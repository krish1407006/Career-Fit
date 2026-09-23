from django.contrib.auth import get_user_model
from django.db.models import Count, OuterRef, Subquery
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole, IsRecruiter, IsStudent
from apps.resumes.models import Resume, ResumeAnalysis

from .models import Job, JobApplication, Skill
from .matching import match_job_to_student, skill_gap
from .serializers import (
    ApplicantSummary,
    JobApplicationSerializer,
    JobCreateUpdateSerializer,
    JobSerializer,
    SkillSerializer,
)

User = get_user_model()


def latest_analysis_subquery():
    latest_resume = Resume.objects.filter(user=OuterRef("pk")).order_by("-uploaded_at")
    return ResumeAnalysis.objects.filter(resume=latest_resume[:1])[:1]


def candidate_skills_for(user):
    analysis = ResumeAnalysis.objects.filter(resume__user=user, resume__status=Resume.Status.ANALYZED)\
        .order_by("-resume__uploaded_at").first()
    return analysis.skills if analysis else []


def preferred_roles_for(user):
    profile = getattr(user, "student_profile", None)
    return list(profile.preferred_roles) if profile else []


class SkillListView(generics.ListAPIView):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated]


class JobListView(APIView):
    """List/search jobs (all authenticated); recruiters may create."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Job.objects.filter(is_active=True)
        q = request.query_params.get("q")
        job_type = request.query_params.get("job_type")
        location = request.query_params.get("location")

        if q:
            qs = (qs.filter(title__icontains=q)
                  | qs.filter(company_name__icontains=q)
                  | qs.filter(location__icontains=q)).distinct()
        if job_type:
            qs = qs.filter(job_type=job_type)
        if location:
            qs = qs.filter(location__icontains=location)

        qs = qs.annotate(application_count=Count("applications"))

        if request.user.is_student:
            skills = candidate_skills_for(request.user)
            preferred_roles = preferred_roles_for(request.user)
            user_apps = JobApplication.objects.filter(student=request.user)
            app_map = {a.job_id: a for a in user_apps}
            jobs = list(qs)
            for job in jobs:
                job._candidate_skills = skills
                job._user_application = app_map.get(job.id)
                job._match = match_job_to_student(job, skills, preferred_roles)
            jobs.sort(key=lambda j: (getattr(j, "_match", {}) or {}).get("score", 0), reverse=True)
        else:
            jobs = list(qs)

        return Response(JobSerializer(jobs, many=True, context={"request": request}).data)

    def post(self, request):
        if not request.user.is_recruiter and not request.user.is_admin_role:
            return Response({"detail": "Only recruiters can post jobs."},
                            status=status.HTTP_403_FORBIDDEN)
        data = {**request.data}
        if request.user.is_recruiter and not data.get("company_name"):
            profile = getattr(request.user, "recruiter_profile", None)
            if profile and profile.company_name:
                data["company_name"] = profile.company_name
        serializer = JobCreateUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save(recruiter=request.user)
        return Response(JobSerializer(job, context={"request": request}).data,
                        status=status.HTTP_201_CREATED)


class JobDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, request):
        try:
            job = Job.objects.annotate(application_count=Count("applications")).get(pk=pk)
        except Job.DoesNotExist:
            return None
        if request.user.is_student:
            job._candidate_skills = candidate_skills_for(request.user)
            job._user_application = JobApplication.objects.filter(
                student=request.user, job=job).first()
        return job

    def _user_can_modify(self, job, request):
        return job.recruiter == request.user or request.user.is_admin_role

    def get(self, request, pk):
        job = self.get_object(pk, request)
        if not job:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        self._visible_ok = True
        return Response(JobSerializer(job, context={"request": request}).data)

    def put(self, request, pk):
        job = self.get_object(pk, request)
        if not job:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        if not self._user_can_modify(job, request):
            return Response({"detail": "Not your job."}, status=status.HTTP_403_FORBIDDEN)
        serializer = JobCreateUpdateSerializer(job, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        job = serializer.save()
        return Response(JobSerializer(job, context={"request": request}).data)

    def delete(self, request, pk):
        job = self.get_object(pk, request)
        if not job:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        if not self._user_can_modify(job, request):
            return Response({"detail": "Not your job."}, status=status.HTTP_403_FORBIDDEN)
        job.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyJobsView(generics.ListAPIView):
    serializer_class = JobSerializer
    permission_classes = [IsRecruiter]

    def get_queryset(self):
        return (Job.objects.filter(recruiter=self.request.user)
                .annotate(application_count=Count("applications")).order_by("-created_at"))


class JobApplicantsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            job = Job.objects.get(pk=pk)
        except Job.DoesNotExist:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        if job.recruiter != request.user and not request.user.is_admin_role:
            return Response({"detail": "Not your job."}, status=status.HTTP_403_FORBIDDEN)
        apps = JobApplication.objects.filter(job=job).order_by("-match_score", "-applied_at")
        student_ids = [a.student_id for a in apps]
        analysis_qs = (
            ResumeAnalysis.objects.filter(resume__user__in=student_ids)
            .select_related("resume__user")
            .order_by("-resume__uploaded_at")
        )
        analysis_map = {}
        for a in analysis_qs:
            analysis_map.setdefault(a.resume.user_id, a)
        result = []
        for a in apps:
            a._latest_analysis = analysis_map.get(a.student_id)
            result.append(a)
        return Response(ApplicantSummary(result, many=True).data)


class ApplyToJobView(APIView):
    permission_classes = [IsStudent]

    def post(self, request, pk):
        try:
            job = Job.objects.get(pk=pk, is_active=True)
        except Job.DoesNotExist:
            return Response({"detail": "Job not found or closed."}, status=status.HTTP_404_NOT_FOUND)
        if JobApplication.objects.filter(student=request.user, job=job).exists():
            return Response({"detail": "You already applied for this job."},
                            status=status.HTTP_409_CONFLICT)
        skills = candidate_skills_for(request.user)
        match = match_job_to_student(job, skills, preferred_roles_for(request.user))
        application = JobApplication.objects.create(
            student=request.user,
            job=job,
            match_score=match["score"],
            cover_note=request.data.get("cover_note", ""),
        )
        return Response(JobApplicationSerializer(application).data, status=status.HTTP_201_CREATED)


class MyApplicationsView(generics.ListAPIView):
    serializer_class = JobApplicationSerializer
    permission_classes = [IsStudent]

    def get_queryset(self):
        return JobApplication.objects.filter(student=self.request.user)


class ApplicationStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            app = JobApplication.objects.select_related("job").get(pk=pk)
        except JobApplication.DoesNotExist:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)
        if app.job.recruiter != request.user and not request.user.is_admin_role:
            return Response({"detail": "Not your job."}, status=status.HTTP_403_FORBIDDEN)
        new_status = request.data.get("status")
        if new_status not in JobApplication.Status.values:
            return Response({"detail": f"Invalid status. Choose from {JobApplication.Status.values}"},
                            status=status.HTTP_400_BAD_REQUEST)
        app.status = new_status
        app.save()
        return Response({"detail": "Application updated.", "status": app.status})


class SkillGapView(APIView):
    """POST {job_id} -> compares the student's extracted skills to the job."""

    permission_classes = [IsStudent]

    def post(self, request):
        job_id = request.data.get("job_id")
        try:
            job = Job.objects.get(pk=job_id)
        except (Job.DoesNotExist, TypeError, ValueError):
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        skills = candidate_skills_for(request.user)
        gap = skill_gap(skills, job.skills_required)
        return Response({
            "job": {"id": job.id, "title": job.title, "company": job.company_name},
            "skills_required": gap["needed"],
            "your_skills": gap["have"],
            "matched": gap["matched"],
            "missing": gap["missing"],
            "coverage": gap["coverage"],
            "score": gap["score"],
            "recommendation": self._recommendation(gap["coverage"]),
        })

    def _recommendation(self, coverage):
        if coverage >= 70:
            return "Strong fit. Consider applying now."
        if coverage >= 40:
            return "Decent fit. Fill the gaps below before interviewing."
        return "Gap is significant. Learn the missing skills and upload an updated resume."