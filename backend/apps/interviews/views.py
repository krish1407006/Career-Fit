from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStudent

from apps.ai import services as ai_services

from .models import InterviewSession, InterviewTurn
from .serializers import (
    AnswerSerializer,
    InterviewSessionDetailSerializer,
    InterviewSessionListSerializer,
    StartInterviewSerializer,
)


class InterviewStartView(APIView):
    """Start a mock interview: creates a session + first AI question."""

    permission_classes = [IsStudent]

    def post(self, request):
        serializer = StartInterviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        session = InterviewSession.objects.create(
            student=request.user,
            position=data["position"],
            total_questions=data["total_questions"],
            question_index=0,
        )
        question = ai_services.next_interview_question(
            position=session.position,
            transcript=[],
            index=0,
            total=session.total_questions,
        )
        InterviewTurn.objects.create(
            session=session, role=InterviewTurn.Role.ASSISTANT, kind="question", content=question,
        )
        return Response(InterviewSessionDetailSerializer(session).data, status=status.HTTP_201_CREATED)


class InterviewAnswerView(APIView):
    """Submit an answer; evaluates it and either continues or completes the interview."""

    permission_classes = [IsStudent]

    def post(self, request, pk):
        try:
            session = InterviewSession.objects.get(pk=pk, student=request.user)
        except InterviewSession.DoesNotExist:
            return Response({"detail": "Interview not found."}, status=status.HTTP_404_NOT_FOUND)

        if session.status != InterviewSession.Status.IN_PROGRESS:
            return Response({"detail": "Interview already completed."},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = AnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answer = serializer.validated_data["answer"]

        last_question_turn = (
            session.turns.filter(role=InterviewTurn.Role.ASSISTANT, kind="question").order_by("id").last()
        )
        question = last_question_turn.content if last_question_turn else "Tell us about yourself."

        InterviewTurn.objects.create(
            session=session, role=InterviewTurn.Role.USER, kind="answer", content=answer,
        )

        evaluation = ai_services.evaluate_interview_answer(
            position=session.position, question=question, answer=answer,
        )
        InterviewTurn.objects.create(
            session=session,
            role=InterviewTurn.Role.ASSISTANT,
            kind="evaluation",
            content=evaluation.get("feedback", ""),
            score=evaluation.get("score"),
            suggestions=evaluation.get("suggestions", ""),
        )

        session.question_index += 1

        if session.question_index >= session.total_questions:
            transcript = list(session.turns.all().values("role", "kind", "content", "score"))
            report = ai_services.summarize_interview(session.position, transcript)
            session.status = InterviewSession.Status.COMPLETED
            session.report = report
            session.save(update_fields=["question_index", "status", "report", "updated_at"])
            return Response({
                "completed": True,
                "evaluation": evaluation,
                "report": report,
                "session": InterviewSessionListSerializer(session).data,
            })

        next_question = ai_services.next_interview_question(
            position=session.position,
            transcript=list(session.turns.all().values("role", "kind", "content")),
            index=session.question_index,
            total=session.total_questions,
        )
        InterviewTurn.objects.create(
            session=session, role=InterviewTurn.Role.ASSISTANT, kind="question", content=next_question,
        )
        session.save(update_fields=["question_index", "updated_at"])
        return Response({
            "completed": False,
            "evaluation": evaluation,
            "next_question": next_question,
            "question_index": session.question_index,
            "total_questions": session.total_questions,
        })


class MyInterviewsView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        sessions = InterviewSession.objects.filter(student=request.user)
        return Response(InterviewSessionListSerializer(sessions, many=True).data)


class InterviewDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            session = InterviewSession.objects.get(pk=pk)
        except InterviewSession.DoesNotExist:
            return Response({"detail": "Interview not found."}, status=status.HTTP_404_NOT_FOUND)
        if session.student_id != request.user.id and not request.user.is_admin_role:
            return Response({"detail": "Interview not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(InterviewSessionDetailSerializer(session).data)