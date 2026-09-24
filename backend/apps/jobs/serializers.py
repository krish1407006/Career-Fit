from rest_framework import serializers

from .models import Job, JobApplication, Skill
from .matching import match_job_to_student


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name", "category"]


class JobSerializer(serializers.ModelSerializer):
    recruiter_name = serializers.CharField(source="recruiter.username", read_only=True)
    company_name = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField()
    status = serializers.CharField(read_only=True)
    skills_required = serializers.SerializerMethodField()
    required_skills = SkillSerializer(many=True, read_only=True)
    preferred_skills = SkillSerializer(many=True, read_only=True)
    application_count = serializers.SerializerMethodField()
    match = serializers.SerializerMethodField()
    applied = serializers.SerializerMethodField()
    application_id = serializers.SerializerMethodField()
    application_status = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id", "recruiter", "recruiter_name", "company_name", "title",
            "description", "responsibilities", "required_skills",
            "preferred_skills", "skills_required", "job_type", "location",
            "salary_range", "education_required", "min_cgpa",
            "experience_required", "openings", "is_active", "status",
            "application_deadline", "created_at", "updated_at",
            "application_count", "match", "applied", "application_id",
            "application_status",
        ]

    def get_skills_required(self, obj):
        return [s.name for s in obj.required_skills.all()]

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


def resolve_skills(names):
    """Turn a list of skill names into Skill records (reusing the catalog).

    Matching is case-insensitive so "python" reuses an existing "Python"
    skill instead of creating a duplicate row, and duplicates within one
    payload are collapsed to a single skill.
    """
    skills = []
    seen = set()
    for name in names or []:
        name = str(name).strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        skill = Skill.objects.filter(name__iexact=name).first()
        if skill is None:
            skill = Skill.objects.create(name=name)
        skills.append(skill)
    return skills


class JobCreateUpdateSerializer(serializers.ModelSerializer):
    """Write serializer for jobs.

    ``skills_required`` (names) and ``required_skills``/``preferred_skills``
    (names or ids) map onto the Job <-> Skill relationships.
    """

    skills_required = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True, write_only=True,
    )
    preferred_skills = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True, write_only=True,
    )

    class Meta:
        model = Job
        fields = [
            "id", "company_name", "title", "description", "responsibilities",
            "skills_required", "preferred_skills", "job_type", "location",
            "salary_range", "education_required", "min_cgpa",
            "experience_required", "openings", "is_active", "application_deadline",
        ]

    def validate_min_cgpa(self, value):
        if value is not None and not (0 <= float(value) <= 10):
            raise serializers.ValidationError("Minimum CGPA must be between 0 and 10.")
        return value

    def create(self, validated_data):
        required_names = validated_data.pop("skills_required", [])
        preferred_names = validated_data.pop("preferred_skills", [])
        job = Job.objects.create(**validated_data)
        job.required_skills.set(resolve_skills(required_names))
        job.preferred_skills.set(resolve_skills(preferred_names))
        return job

    def update(self, instance, validated_data):
        required_names = validated_data.pop("skills_required", None)
        preferred_names = validated_data.pop("preferred_skills", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if required_names is not None:
            instance.required_skills.set(resolve_skills(required_names))
        if preferred_names is not None:
            instance.preferred_skills.set(resolve_skills(preferred_names))
        return instance


class JobApplicationSerializer(serializers.ModelSerializer):
    job_id = serializers.IntegerField(source="job.id", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    company = serializers.CharField(source="job.company_name", read_only=True)
    job_type = serializers.CharField(source="job.job_type", read_only=True)
    location = serializers.CharField(source="job.location", read_only=True)
    resume = serializers.SerializerMethodField()

    class Meta:
        model = JobApplication
        fields = [
            "id", "job_id", "job_title", "company", "job_type", "location", "status",
            "match_score", "cover_note", "remarks", "resume", "applied_at", "updated_at",
        ]

    def get_resume(self, obj):
        if not obj.resume_id:
            return None
        return {
            "id": obj.resume_id,
            "original_name": obj.resume.original_name,
        }


class ApplicantSummary(serializers.Serializer):
    application_id = serializers.IntegerField(source="id")
    status = serializers.CharField()
    cover_note = serializers.CharField()
    remarks = serializers.CharField()
    applied_at = serializers.DateTimeField()
    match_score = serializers.IntegerField()
    student_id = serializers.IntegerField()
    username = serializers.CharField(source="student.username")
    email = serializers.CharField(source="student.email")
    profile = serializers.SerializerMethodField()
    resume = serializers.SerializerMethodField()

    def get_profile(self, obj):
        profile = getattr(obj.student, "student_profile", None)
        if not profile:
            return None
        return {
            "full_name": profile.full_name,
            "college": profile.college,
            "degree": profile.degree,
            "branch": profile.branch,
            "graduation_year": profile.graduation_year,
            "cgpa": str(profile.cgpa) if profile.cgpa else None,
            "location": profile.location,
            "skills": [s.name for s in profile.skills.all()],
        }

    def get_resume(self, obj):
        analysis = getattr(obj, "_latest_analysis", None)
        resume = obj.resume
        return {
            "id": resume.id if resume else None,
            "name": resume.original_name if resume else None,
            "score": analysis.score if analysis else None,
            "skills": analysis.skills if analysis else None,
            "source": analysis.source if analysis else None,
        }


class RecruiterApplicationSerializer(ApplicantSummary):
    """Recruiter-facing application row: application + job + candidate summary."""

    job_id = serializers.IntegerField(source="job.id", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)
    company = serializers.CharField(source="job.company_name", read_only=True)
    job_type = serializers.CharField(source="job.job_type", read_only=True)