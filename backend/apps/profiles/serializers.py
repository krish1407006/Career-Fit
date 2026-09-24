from rest_framework import serializers

from apps.accounts.models import StudentProfile
from apps.accounts.serializers import StudentProfileSerializer
from apps.jobs.models import Skill
from apps.jobs.serializers import SkillSerializer
from apps.resumes.serializers import ResumeSerializer

from .models import Certification, Education, Project
from .utils import profile_completion


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = ["id", "institution", "degree", "field_of_study", "start_year",
                  "end_year", "cgpa", "is_current"]


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "title", "description", "technologies", "link"]


class CertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certification
        fields = ["id", "name", "issuer", "issue_date", "credential_url"]


class ProfileDetailSerializer(serializers.Serializer):
    """Rich student-profile payload used by GET/PUT /api/profile/ and the dashboard."""

    profile = StudentProfileSerializer()
    skills = SkillSerializer(many=True)
    education = EducationSerializer(many=True)
    projects = ProjectSerializer(many=True)
    certifications = CertificationSerializer(many=True)
    resume = ResumeSerializer(read_only=True)
    completion = serializers.SerializerMethodField()

    def get_completion(self, obj):
        return profile_completion(obj.profile)

    def to_representation(self, instance):
        profile = instance
        resume = None
        if hasattr(profile.user, "resumes") and profile.user.resumes.exists():
            resume = profile.user.resumes.first()
        return {
            "profile": StudentProfileSerializer(profile).data,
            "skills": SkillSerializer(profile.skills.all(), many=True).data,
            "education": EducationSerializer(profile.education.all(), many=True).data,
            "projects": ProjectSerializer(profile.projects.all(), many=True).data,
            "certifications": CertificationSerializer(profile.certifications.all(), many=True).data,
            "resume": ResumeSerializer(resume, context=self.context).data if resume else None,
            "completion": profile_completion(profile),
        }


class SkillInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Skill name is required.")
        return value


def get_or_create_skill(name, category=""):
    existing = Skill.objects.filter(name__iexact=name).first()
    if existing:
        return existing
    return Skill.objects.create(name=name, category=category)