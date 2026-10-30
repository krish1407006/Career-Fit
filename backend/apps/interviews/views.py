"""Interview API views (Phase 7).

Every view resolves the student from ``request.user`` only. A student-supplied
id is never trusted for authorisation, and an AI failure is converted into a
fixed, student-safe message by :mod:`apps.interviews.services`.
"""

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole, IsStudent
from apps.ai.errors import AiError
from apps.ai.interview_service import transcribe_answer
from config.throttling import AiThrottle

from . import services
from .models import InterviewSession, InterviewTurn
from .serializers import (
    AdminInterviewSessionSerializer,
    AnswerSerializer,
    CompleteInterviewSerializer,
    InterviewReportSerializer,
    InterviewSessionDetailSerializer,
    InterviewSessionListSerializer,
    StartInterviewSerializer,
)


def _error(message, code, status):
    return Response({"detail": message, "code": code}, status=status)


def _owned_session(request, pk):
    """Fetch a session the caller owns, or None.

    A session belonging to another student is reported as not found, never as
    forbidden, so ids cannot be probed.
    """
    return InterviewSession.objects.filter(pk=pk, student=request.user).first()


class InterviewStartView(APIView):
    """POST /api/interviews/start/ - start, or resume, a voice/text interview."""

    permission_classes = [IsStudent]
    throttle_classes = [AiThrottle]

    def post(self, request):
        serializer = StartInterviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            session, created = services.start_session(
                request.user,
                position=data["position"],
                total_questions=data["total_questions"],
                job_id=data.get("job"),
                mode=data.get("mode"),
                resume=data.get("resume", False),
            )
        except services.InterviewError as exc:
            return _error(exc.message, exc.code, exc.status)

        payload = InterviewSessionDetailSerializer(session).data
        payload["resumed"] = not created
        return Response(
            payload,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MyInterviewsView(APIView):
    """GET /api/interviews/mine/ - the student's own sessions, newest first."""

    permission_classes = [IsStudent]

    def get(self, request):
        sessions = InterviewSession.objects.filter(student=request.user)
        return Response(InterviewSessionListSerializer(sessions, many=True).data)


class ActiveInterviewView(APIView):
    """GET /api/interviews/active/ - resumable session, or 404 when idle.

    Lets the frontend show "Resume Interview" after a browser refresh without
    the student having to remember which interview was running.
    """

    permission_classes = [IsStudent]

    def get(self, request):
        session = services.active_session(request.user)
        if session is None:
            return Response({"detail": "No interview in progress."}, status=status.HTTP_404_NOT_FOUND)
        try:
            session = services.resume_session(session)
        except services.InterviewError as exc:
            return _error(exc.message, exc.code, exc.status)
        payload = InterviewSessionDetailSerializer(session).data
        payload["resumed"] = True
        return Response(payload)


class InterviewDetailView(APIView):
    """GET /api/interviews/<id>/ - full transcript for a session the caller owns."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        session = _owned_session(request, pk)
        if session is None and not request.user.is_admin_role:
            return _error("Interview not found.", "not_found", status.HTTP_404_NOT_FOUND)
        if session is None:
            session = InterviewSession.objects.filter(pk=pk).first()
        if session is None:
            return _error("Interview not found.", "not_found", status.HTTP_404_NOT_FOUND)
        return Response(InterviewSessionDetailSerializer(session).data)


class InterviewAnswerView(APIView):
    """POST /api/interviews/<id>/answer/ - submit a recognised transcript.

    Body: {"answer": "<transcript>", "client_token": "<idempotency key>"}
    """

    permission_classes = [IsStudent]
    throttle_classes = [AiThrottle]

    def post(self, request, pk):
        session = _owned_session(request, pk)
        if session is None:
            return _error("Interview not found.", "not_found", status.HTTP_404_NOT_FOUND)

        serializer = AnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answer = serializer.validated_data["answer"]
        client_token = serializer.validated_data.get("client_token", "")

        try:
            result = services.submit_answer(
                session, answer, client_token=client_token
            )
        except services.InterviewError as exc:
            return _error(exc.message, exc.code, exc.status)

        session = result["session"]
        body = {
            "duplicate": result["duplicate"],
            "evaluation": result["evaluation"],
            "next_question": result["next_question"],
            "question_index": result["question_index"],
            "total_questions": result["total_questions"],
            "state": session.state,
            "status": session.status,
            "session": InterviewSessionDetailSerializer(session).data,
        }
        if result["completed"]:
            body["completed"] = True
            body["report"] = session.report_data or {}
        else:
            body["completed"] = False
        return Response(body, status=status.HTTP_200_OK)


class InterviewTranscribeView(APIView):
    """POST /api/interviews/transcribe/ - speech-to-text for one recorded answer.

    Multipart body: ``audio`` file. Only the transcript is returned; the audio
    is passed to the provider in memory and never stored.
    """

    permission_classes = [IsStudent]
    throttle_classes = [AiThrottle]

    MAX_AUDIO_BYTES = 10 * 1024 * 1024
    ALLOWED_TYPES = {
        "audio/webm",
        "audio/ogg",
        "audio/wav",
        "audio/x-wav",
        "audio/mp4",
        "audio/m4a",
        "audio/x-m4a",
        "audio/mpeg",
        "audio/mp3",
        "audio/opus",
        "audio/aac",
        "audio/flac",
    }

    def post(self, request):
        audio = request.FILES.get("audio")
        if audio is None:
            return _error(
                "Record an answer before requesting a transcript.",
                "audio_required",
                status.HTTP_400_BAD_REQUEST,
            )
        if audio.size == 0:
            return _error(
                "The recording was empty. Try recording again.",
                "audio_empty",
                status.HTTP_400_BAD_REQUEST,
            )
        if audio.size > self.MAX_AUDIO_BYTES:
            return _error(
                "That recording is too long. Keep answers under about two minutes.",
                "audio_too_large",
                status.HTTP_400_BAD_REQUEST,
            )
        mime_type = (audio.content_type or "").split(";", 1)[0].strip().lower()
        if mime_type not in self.ALLOWED_TYPES:
            return _error(
                "That audio format is not supported. Try a different browser or type your answer.",
                "audio_type_unsupported",
                status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = transcribe_answer(audio.read(), mime_type)
        except AiError:
            return _error(
                "Speech-to-text is temporarily unavailable. Type your answer instead.",
                "transcription_unavailable",
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {"text": result["text"], "source": result["source"]},
            status=status.HTTP_200_OK,
        )


class InterviewCompleteView(APIView):
    """POST /api/interviews/<id>/complete/ - finish early and build the report."""

    permission_classes = [IsStudent]

    def post(self, request, pk):
        session = _owned_session(request, pk)
        if session is None:
            return _error("Interview not found.", "not_found", status.HTTP_404_NOT_FOUND)

        serializer = CompleteInterviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if session.status == InterviewSession.Status.IN_PROGRESS:
            try:
                services.complete_session(session)
            except services.InterviewError as exc:
                return _error(exc.message, exc.code, exc.status)
        elif not session.report_data:
            # Cancelled/aborted sessions can still be given a report on demand.
            try:
                services.complete_session(session)
            except services.InterviewError as exc:
                return _error(exc.message, exc.code, exc.status)

        return Response(
            {
                "completed": True,
                "report": session.report_data or {},
                "session": InterviewSessionDetailSerializer(session).data,
            }
        )


class InterviewCancelView(APIView):
    """POST /api/interviews/<id>/cancel/ - abandon an interview."""

    permission_classes = [IsStudent]

    def post(self, request, pk):
        session = _owned_session(request, pk)
        if session is None:
            return _error("Interview not found.", "not_found", status.HTTP_404_NOT_FOUND)
        if session.status == InterviewSession.Status.IN_PROGRESS:
            services.cancel_session(session)
        return Response({"session": InterviewSessionDetailSerializer(session).data})


class InterviewReportView(APIView):
    """GET /api/interviews/<id>/report/ - the structured practice report."""

    permission_classes = [IsStudent]

    def get(self, request, pk):
        session = _owned_session(request, pk)
        if session is None:
            return _error("Interview not found.", "not_found", status.HTTP_404_NOT_FOUND)

        if not session.report_data and session.status == InterviewSession.Status.IN_PROGRESS:
            return _error(
                "This interview is still in progress. Finish it to generate the report.",
                "report_pending",
                status=status.HTTP_409_CONFLICT,
            )
        if not session.report_data:
            try:
                services.complete_session(session)
            except services.InterviewError as exc:
                return _error(exc.message, exc.code, exc.status)

        report = dict(session.report_data or {})
        report.setdefault("score_note", "")
        payload = {
            "id": session.id,
            "position": session.position,
            "status": session.status,
            "mode": session.mode,
            "completed_at": session.completed_at,
            **report,
        }
        return Response(InterviewReportSerializer(payload).data)


# ---------------------------------------------------------------------------
# Admin inspection
# ---------------------------------------------------------------------------
class AdminInterviewListView(APIView):
    """GET /api/interviews/admin/ -> every mock interview session.

    Read only. ``/api/interviews/<id>/`` already lets an admin read any
    transcript, so this list only has to say who ran what and how it went.
    Optional filters: ``?student=<id>``, ``?status=<value>``.
    """

    permission_classes = [IsAdminRole]

    def get(self, request):
        sessions = InterviewSession.objects.select_related("student", "job").annotate(
            answer_count=Count("turns", filter=Q(turns__kind=InterviewTurn.Kind.ANSWER))
        )
        student_id = request.query_params.get("student")
        if student_id:
            try:
                sessions = sessions.filter(student_id=int(student_id))
            except (TypeError, ValueError):
                return Response({"detail": "student must be an account id."},
                                status=status.HTTP_400_BAD_REQUEST)
        status_filter = request.query_params.get("status")
        if status_filter:
            sessions = sessions.filter(status=status_filter)
        return Response(AdminInterviewSessionSerializer(sessions, many=True).data)
