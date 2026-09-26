from urllib.parse import quote

from django.conf import settings
from django.http import FileResponse
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStudent
from apps.jobs.models import JobApplication

from .analysis import AnalysisError, run_resume_analysis
from .models import Resume, ResumeAnalysis
from .serializers import ResumeAnalysisSerializer, ResumeSerializer, ResumeUploadSerializer


class ResumeListCreateView(APIView):
    """Upload a resume (multipart, PDF) or list the caller's resumes.

    A student holds at most one resume: uploading a new file replaces any
    previous one (file and row are removed, and with it its analysis). AI
    analysis is a separate, on-demand step - see ``ResumeAnalyzeView``.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        resumes = Resume.objects.filter(user=request.user).prefetch_related("analysis")
        return Response(ResumeSerializer(resumes, many=True, context={"request": request}).data)

    def post(self, request):
        serializer = ResumeUploadSerializer(data=request.data,
                                            context={"request": request})
        serializer.is_valid(raise_exception=True)

        for old in Resume.objects.filter(user=request.user):
            old.delete()

        resume = serializer.save(user=request.user)
        return Response(
            ResumeSerializer(resume, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class ResumeDetailView(APIView):
    """Retrieve or delete one of the caller's resumes."""

    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return Resume.objects.select_related("analysis").get(pk=pk, user=user)
        except Resume.DoesNotExist:
            return None

    def get(self, request, pk):
        resume = self.get_object(pk, request.user)
        if not resume:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ResumeSerializer(resume, context={"request": request}).data)

    def delete(self, request, pk):
        resume = self.get_object(pk, request.user)
        if not resume:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        resume.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResumeDownloadView(APIView):
    """Stream a resume file.

    The resume owner may always download their own resume. A recruiter may
    download a candidate's resume only when that candidate has applied to one
    of the recruiter's jobs and the application used this resume, keeping
    private student documents out of reach of unrelated recruiters.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        resume = Resume.objects.filter(pk=pk).first()
        if not resume:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if not self._can_access(resume, request.user):
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if not resume.file:
            return Response({"detail": "No file on this resume."}, status=status.HTTP_404_NOT_FOUND)
        response = FileResponse(resume.file.open("rb"), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{quote(resume.original_name)}"'
        return response

    @staticmethod
    def _can_access(resume, user):
        if resume.user_id == user.id:
            return True
        if user.is_recruiter:
            return JobApplication.objects.filter(
                student=resume.user_id, job__recruiter=user, resume=resume
            ).exists()
        return False


# ---------------------------------------------------------------------------
# Phase 6 - AI-powered resume analysis
# ---------------------------------------------------------------------------
class ResumeAnalyzeView(APIView):
    """POST /api/resumes/<pk>/analyze/ -> run (or re-run) AI analysis.

    Ownership comes from the authenticated user only: another student's resume
    is reported as 404, never as 403, and no student id is ever accepted from
    the request body. An optional ``job_id`` is used only to add job-role
    relevance, computed with the existing skill-matching logic.
    """

    permission_classes = [IsStudent]

    def get_resume(self, pk, user):
        return Resume.objects.filter(pk=pk, user=user).first()

    def post(self, request, pk):
        resume = self.get_resume(pk, request.user)
        if resume is None:
            return Response({"detail": "Resume not found."}, status=status.HTTP_404_NOT_FOUND)

        job = None
        job_id = (request.data or {}).get("job_id")
        if job_id not in (None, "", "null"):
            try:
                job = Job.objects.filter(pk=int(job_id), is_active=True).first()
            except (TypeError, ValueError):
                job = None
            if job is None:
                return Response({"detail": "Job not found or closed."},
                                status=status.HTTP_404_NOT_FOUND)

        try:
            analysis = run_resume_analysis(
                resume, user=request.user, job=job, require_ai=settings.AI_REQUIRED,
            )
        except AnalysisError as exc:
            return Response(
                {"detail": exc.message, "code": exc.code,
                 "resume_status": resume.status},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(ResumeAnalysisSerializer(analysis).data, status=status.HTTP_200_OK)


class ResumeAnalysisView(APIView):
    """GET /api/resumes/<pk>/analysis/ -> the caller's analysis for one resume."""

    permission_classes = [IsStudent]

    def get(self, request, pk):
        resume = Resume.objects.filter(pk=pk, user=request.user).first()
        if resume is None:
            return Response({"detail": "Resume not found."}, status=status.HTTP_404_NOT_FOUND)
        analysis = getattr(resume, "analysis", None)
        if analysis is None:
            return Response({"detail": "No analysis yet. Run Analyze Resume first."},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(ResumeAnalysisSerializer(analysis).data)


class ResumeAnalysisDetailView(APIView):
    """GET /api/resume-analyses/<pk>/ -> one analysis, owner only."""

    permission_classes = [IsStudent]

    def get(self, request, pk):
        analysis = (
            ResumeAnalysis.objects
            .select_related("resume")
            .filter(pk=pk, resume__user=request.user)
            .first()
        )
        if analysis is None:
            return Response({"detail": "Analysis not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ResumeAnalysisSerializer(analysis).data)
