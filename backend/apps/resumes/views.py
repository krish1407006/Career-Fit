import logging

from django.conf import settings
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.errors import AiError
from apps.ai.services import analyze_resume

from .models import Resume, ResumeAnalysis
from .serializers import ResumeSerializer, ResumeUploadSerializer
from .text_extraction import extract_text_from_resume

logger = logging.getLogger(__name__)

RESUME_PROCESSING_EXISTS = "There is already a resume being processed. Wait for it to finish."


class ResumeListCreateView(APIView):
    """Upload a resume (multipart) or list the caller's resumes."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        resumes = Resume.objects.filter(user=request.user).prefetch_related("analysis")
        return Response(ResumeSerializer(resumes, many=True, context={"request": request}).data)

    def post(self, request):
        serializer = ResumeUploadSerializer(data=request.data,
                                            context={"request": request})
        serializer.is_valid(raise_exception=True)
        if Resume.objects.filter(user=request.user, status=Resume.Status.PROCESSING).exists():
            return Response({"detail": RESUME_PROCESSING_EXISTS}, status=status.HTTP_409_CONFLICT)

        resume = serializer.save(user=request.user)
        try:
            text = extract_text_from_resume(resume.file)
            analysis_data = analyze_resume(text)
            ResumeAnalysis.objects.update_or_create(
                resume=resume,
                defaults={
                    "skills": analysis_data.get("skills") or [],
                    "summary": analysis_data.get("summary") or "",
                    "education": analysis_data.get("education") or [],
                    "experience": analysis_data.get("experience") or [],
                    "score": int(analysis_data.get("score") or 0),
                    "suggestions": analysis_data.get("suggestions") or [],
                    "source": analysis_data.get("source", "offline"),
                    "raw": analysis_data,
                },
            )
            resume.status = Resume.Status.ANALYZED
            resume.save()
        except AiError as exc:
            resume.status = Resume.Status.FAILED
            resume.error_message = str(exc)
            resume.save()
            logger.exception("Resume analysis failed for resume %s", resume.id)
            return Response(
                {"detail": "AI provider unavailable and required.", "error": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            resume.status = Resume.Status.FAILED
            resume.error_message = str(exc)
            resume.save()
            logger.exception("Resume processing failed for resume %s", resume.id)
            return Response(
                {"detail": "Could not process this resume. Try a clear PDF/DOCX."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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