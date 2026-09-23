from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from .models import Job, JobApplication, Skill
from .matching import match_job_to_student


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name", "category"]


class JobSerializer(serializers.ModelSerializer):
    recruiter_name = serializers.CharField(source="recruiter.username", read_only=True)
    application_count = serializers.SerializerMethodField()
    match = serializers.SerializerMethodField()
    applied = serializers.SerializerMethodField()
    application_id = serializers.SerializerMethodField()
    application_status = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id", "recruiter", "recruiter_name", "company_name", "title",
            "description", "responsibilities", "skills_required", "job_type",
            "location", "salary_range", "openings", "is_active", "expires_at",
            "created_at", "updated_at", "application_count", "match", "applied",
            "application_id", "application_status",
        ]

    def get_application_count(self, obj):
        return obj.application_count if hasattr(obj, "application_count") else None

    def get_match(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated or not user.is_student:
            return None
        skills = getattr(obj, "_candidate_skills", None)
        if skills is None:
            return None
        preferred_roles = []
        profile = getattr(user, "student_profile", None)
        if profile:
            preferred_roles = profile.preferred_roles
        return match_job_to_student(obj, skills, preferred_roles)

    def get_applied(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        apps = getattr(obj, "_user_application", None)
        return apps is not None

    def get_application_id(self, obj):
        apps = getattr(obj, "_user_application", None)
        return apps.id if apps else None

    def get_application_status(self, obj):
        apps = getattr(obj, "_user_application", None)
        return apps.status if apps else None


class JobCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            "id", "company_name", "title", "description", "responsibilities",
            "skills_required", "job_type", "location", "salary_range",
            "openings", "is_active", "expires_at",
        ]


class JobApplicationSerializer(serializers.ModelSerializer):
    job_id = serializers.IntegerField(source="job.id", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    company = serializers.CharField(source="job.company_name", read_only=True)
    job_type = serializers.CharField(source="job.job_type", read_only=True)
    location = serializers.CharField(source="job.location", read_only=True)

    class Meta:
        model = JobApplication
        fields = [
            "id", "job_id", "job_title", "company", "job_type", "location", "status",
            "match_score", "cover_note", "applied_at", "updated_at",
        ]


class ApplicantSummary(serializers.Serializer):
    application_id = serializers.IntegerField(source="id")
    status = serializers.CharField()
    cover_note = serializers.CharField()
    applied_at = serializers.DateTimeField()
    match_score = serializers.IntegerField()
    student_id = serializers.IntegerField()
    username = serializers.CharField(source="student.username")
    email = serializers.CharField(source="student.email")
    profile = serializers.SerializerMethodField()
    resume = serializers.SerializerMethodField()

    def get_profile(self, obj):
        profile = obj.student.student_profile
        return {
            "full_name": profile.full_name,
            "college": profile.college,
            "branch": profile.branch,
            "graduation_year": profile.graduation_year,
            "cgpa": str(profile.cgpa) if profile.cgpa else None,
            "location": profile.location,
        }

    def get_resume(self, obj):
        analysis = obj._latest_analysis
        return {
            "score": analysis.score,
            "skills": analysis.skills,
            "source": analysis.source,
        } if analysis else None