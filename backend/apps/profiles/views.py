from django.http import Http404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import StudentProfile
from apps.accounts.permissions import IsStudent
from apps.jobs.models import Skill
from apps.jobs.serializers import SkillSerializer
from apps.resumes.analysis import skill_source_map

from .models import Certification, Education, Project
from .serializers import (
    CertificationSerializer,
    EducationSerializer,
    ProfileDetailSerializer,
    ProjectSerializer,
    SkillInputSerializer,
    get_or_create_skill,
    serialize_student_skills,
)


def _get_or_create_profile(user):
    return StudentProfile.objects.get_or_create(user=user)[0]


class ProfileView(APIView):
    """GET the caller's full student profile; PUT updates profile fields."""

    permission_classes = [IsStudent]

    def get(self, request):
        profile = _get_or_create_profile(request.user)
        serializer = ProfileDetailSerializer(profile, context={"request": request})
        return Response(serializer.data)

    def put(self, request):
        profile = _get_or_create_profile(request.user)
        data = {k: v for k, v in request.data.items()
                if k in {"full_name", "college", "degree", "branch", "graduation_year",
                         "cgpa", "phone", "location", "bio", "preferred_roles",
                         "preferred_technologies"}}
        for key, value in data.items():
            setattr(profile, key, value)
        profile.save()
        serializer = ProfileDetailSerializer(profile, context={"request": request})
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------
class EducationListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsStudent]
    serializer_class = EducationSerializer
    pagination_class = None

    def get_queryset(self):
        return Education.objects.filter(profile__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(profile=_get_or_create_profile(self.request.user))


class EducationDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsStudent]
    serializer_class = EducationSerializer

    def get_queryset(self):
        return Education.objects.filter(profile__user=self.request.user)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------
class ProjectListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsStudent]
    serializer_class = ProjectSerializer
    pagination_class = None

    def get_queryset(self):
        return Project.objects.filter(profile__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(profile=_get_or_create_profile(self.request.user))


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsStudent]
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return Project.objects.filter(profile__user=self.request.user)


# ---------------------------------------------------------------------------
# Certifications
# ---------------------------------------------------------------------------
class CertificationListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsStudent]
    serializer_class = CertificationSerializer
    pagination_class = None

    def get_queryset(self):
        return Certification.objects.filter(profile__user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(profile=_get_or_create_profile(self.request.user))


class CertificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsStudent]
    serializer_class = CertificationSerializer

    def get_queryset(self):
        return Certification.objects.filter(profile__user=self.request.user)


# ---------------------------------------------------------------------------
# Skills (reuse the global Skill catalog, per-student membership)
# ---------------------------------------------------------------------------
class MySkillsView(APIView):
    """List the student's skills or add one by name."""

    permission_classes = [IsStudent]

    def get(self, request):
        profile = _get_or_create_profile(request.user)
        return Response(serialize_student_skills(profile))

    def post(self, request):
        serializer = SkillInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = _get_or_create_profile(request.user)
        skill = get_or_create_skill(serializer.validated_data["name"])
        if skill not in profile.skills.all():
            profile.skills.add(skill)
        row = dict(SkillSerializer(skill).data)
        # Manual entry never rewrites the analysis; only the badge may differ.
        row["source"] = "ai" if skill.name.strip().lower() in skill_source_map(request.user) else "manual"
        return Response(row, status=status.HTTP_201_CREATED)


class RemoveSkillView(APIView):
    """Remove a skill from the student's profile by Skill id."""

    permission_classes = [IsStudent]

    def delete(self, request, pk):
        profile = _get_or_create_profile(request.user)
        try:
            skill = profile.skills.get(pk=pk)
        except Skill.DoesNotExist:
            raise Http404
        profile.skills.remove(skill)
        return Response(status=status.HTTP_204_NO_CONTENT)