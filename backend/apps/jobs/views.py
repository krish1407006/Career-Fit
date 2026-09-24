from django.contrib.auth import get_user_model
from django.db.models import Count, OuterRef, Subquery
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
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
    RecruiterApplicationSerializer,
    SkillSerializer,
)

User = get_user_model()


def latest_analysis_subquery():
    latest_resume = Resume.objects.filter(user=OuterRef("pk")).order_by("-uploaded_at")
    return ResumeAnalysis.objects.filter(resume=latest_resume[:1])[:1]


def candidate_skills_for(user):
    """Union of resume-analysis skills and profile skills (case-insensitively deduped).

    This means matching works even before a student uploads/analyses a resume,
    because Phase 3 students maintain a manual skill catalogue in their profile.
    """
    analysis = ResumeAnalysis.objects.filter(resume__user=user, resume__status=Resume.Status.ANALYZED)\
        .order_by("-resume__uploaded_at").first()
    names = list(analysis.skills) if analysis else []
    profile = getattr(user, "student_profile", None)
    if profile:
        names.extend(s.name for s in profile.skills.all())
    seen = set()
    result = []
    for name in names:
        key = str(name).strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(name)
    return result


def preferred_roles_for(user):
    profile = getattr(user, "student_profile", None)
    return list(profile.preferred_roles) if profile else []


class OptionalPageNumberPagination(PageNumberPagination):
    """Pagination helper that only kicks in when ``?page=``/``?page_size=`` is used."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        if not request.query_params.get("page") and not request.query_params.get("page_size"):
            return None
        return super().paginate_queryset(queryset, request, view)


class SkillListView(generics.ListAPIView):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        q = (request.query_params.get("q") or "").strip()
        if q:
            self.queryset = self.queryset.filter(name__icontains=q)
        return super().get(request, *args, **kwargs)


class JobListView(APIView):
    """List/search/filter jobs (all authenticated); recruiters may create."""

    permission_classes = [IsAuthenticated]

    def _filtered_qs(self, request):
        qs = Job.objects.filter(is_active=True).prefetch_related("required_skills", "preferred_skills")
        q = request.query_params.get("q")
        role = request.query_params.get("role")
        job_type = request.query_params.get("job_type")
        location = request.query_params.get("location")

        if q:
            qs = (qs.filter(title__icontains=q)
                  | qs.filter(company_name__icontains=q)
                  | qs.filter(location__icontains=q)).distinct()
        if role:
            qs = qs.filter(title__icontains=role)
        if job_type:
            qs = qs.filter(job_type=job_type)
        if location:
            qs = qs.filter(location__icontains=location)

        return qs.annotate(application_count=Count("applications"))

    def get(self, request):
        qs = self._filtered_qs(request)
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

        paginator = OptionalPageNumberPagination()
        page = paginator.paginate_queryset(jobs, request, view=self)
        items = page if page is not None else jobs
        serializer = JobSerializer(items, many=True, context={"request": request})
        if page is not None:
            return paginator.get_paginated_response(serializer.data)
        return Response(serializer.data)

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
        job = Job.objects.prefetch_related("required_skills", "preferred_skills").get(pk=job.pk)
        return Response(JobSerializer(job, context={"request": request}).data,
                        status=status.HTTP_201_CREATED)


class JobDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, request):
        try:
            job = Job.objects.prefetch_related("required_skills", "preferred_skills")\
                .annotate(application_count=Count("applications")).get(pk=pk)
        except Job.DoesNotExist:
            return None
        if request.user.is_student:
            job._candidate_skills = candidate_skills_for(request.user)
            job._user_application = JobApplication.objects.filter(
                student=request.user, job=job).first()
        return job

    def _user_can_modify(self, job, request):
        return job.recruiter == request.user or request.user.is_admin_role

    def _not_found(self):
        return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

    def _forbidden(self):
        return Response({"detail": "Not your job."}, status=status.HTTP_403_FORBIDDEN)

    def get(self, request, pk):
        job = self.get_object(pk, request)
        if not job:
            return self._not_found()
        return Response(JobSerializer(job, context={"request": request}).data)

    def put(self, request, pk):
        job = self.get_object(pk, request)
        if not job:
            return self._not_found()
        if not self._user_can_modify(job, request):
            return self._forbidden()
        serializer = JobCreateUpdateSerializer(job, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        job = serializer.save()
        job = Job.objects.prefetch_related("required_skills", "preferred_skills")\
            .annotate(application_count=Count("applications")).get(pk=job.pk)
        return Response(JobSerializer(job, context={"request": request}).data)

    def patch(self, request, pk):
        return self.put(request, pk)

    def delete(self, request, pk):
        job = self.get_object(pk, request)
        if not job:
            return self._not_found()
        if not self._user_can_modify(job, request):
            return self._forbidden()
        job.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyJobsView(generics.ListAPIView):
    serializer_class = JobSerializer
    permission_classes = [IsRecruiter]

    def get_queryset(self):
        return (Job.objects.filter(recruiter=self.request.user)
                .prefetch_related("required_skills", "preferred_skills")
                .annotate(application_count=Count("applications")).order_by("-created_at"))


class JobMatchView(APIView):
    """GET /api/jobs/<pk>/match/ -> transparent skill-match for the student."""

    permission_classes = [IsStudent]

    def get(self, request, pk):
        try:
            job = Job.objects.prefetch_related("required_skills").get(pk=pk)
        except Job.DoesNotExist:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        skills = candidate_skills_for(request.user)
        gap = skill_gap(skills, job.required_skills.all())
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
            return "Strong skill match. Consider applying now."
        if coverage >= 40:
            return "Decent skill match. Fill the gaps below before interviewing."
        return "Skill gap is significant. Learn the missing skills and update your profile."


class JobApplicantsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            job = Job.objects.get(pk=pk)
        except Job.DoesNotExist:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        if job.recruiter != request.user and not request.user.is_admin_role:
            return Response({"detail": "Not your job."}, status=status.HTTP_403_FORBIDDEN)
        apps = (
            JobApplication.objects.filter(job=job)
            .select_related("student__student_profile", "resume")
            .order_by("-match_score", "-applied_at")
        )
        student_ids = [a.student_id for a in apps]
        if student_ids:
            analysis_qs = (
                ResumeAnalysis.objects.filter(resume__user__in=student_ids)
                .select_related("resume__user")
                .order_by("-resume__uploaded_at")
            )
            analysis_map = {}
            for a in analysis_qs:
                analysis_map.setdefault(a.resume.user_id, a)
        else:
            analysis_map = {}
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
        resume = Resume.objects.filter(user=request.user).order_by("-uploaded_at").first()
        application = JobApplication.objects.create(
            student=request.user,
            job=job,
            resume=resume,
            match_score=match["score"],
            cover_note=request.data.get("cover_note", ""),
        )
        return Response(JobApplicationSerializer(application).data, status=status.HTTP_201_CREATED)


class MyApplicationsView(generics.ListAPIView):
    serializer_class = JobApplicationSerializer
    permission_classes = [IsStudent]

    def get_queryset(self):
        return (JobApplication.objects.filter(student=self.request.user)
                .select_related("job", "resume"))


class RecruiterApplicationsView(generics.ListAPIView):
    """All applications across a recruiter's jobs, with candidate summaries."""

    serializer_class = RecruiterApplicationSerializer
    permission_classes = [IsRecruiter]

    def get_queryset(self):
        qs = (
            JobApplication.objects.filter(job__recruiter=self.request.user)
            .select_related("student__student_profile", "job", "resume")
            .order_by("-applied_at")
        )
        job_id = self.request.query_params.get("job_id")
        if job_id:
            qs = qs.filter(job_id=job_id)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        apps = list(queryset)
        student_ids = {a.student_id for a in apps}
        analysis_map = {}
        if student_ids:
            for a in (ResumeAnalysis.objects.filter(resume__user__in=student_ids)
                      .select_related("resume__user").order_by("-resume__uploaded_at")):
                analysis_map.setdefault(a.resume.user_id, a)
        for a in apps:
            a._latest_analysis = analysis_map.get(a.student_id)
        page = self.paginate_queryset(apps)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(apps, many=True)
        return Response(serializer.data)


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
        if new_status is not None:
            if new_status not in JobApplication.Status.values:
                return Response({"detail": f"Invalid status. Choose from {JobApplication.Status.values}"},
                                status=status.HTTP_400_BAD_REQUEST)
            app.status = new_status
        remarks = request.data.get("remarks")
        if remarks is not None:
            app.remarks = remarks
        app.save()
        return Response({
            "detail": "Application updated.",
            "status": app.status,
            "remarks": app.remarks,
        })


class SkillGapView(APIView):
    """POST {job_id} -> compares the student's skills to the job (legacy endpoint)."""

    permission_classes = [IsStudent]

    def post(self, request):
        job_id = request.data.get("job_id")
        try:
            job = Job.objects.prefetch_related("required_skills").get(pk=job_id)
        except (Job.DoesNotExist, TypeError, ValueError):
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        skills = candidate_skills_for(request.user)
        gap = skill_gap(skills, job.required_skills.all())
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