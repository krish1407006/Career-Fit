from django.db.models import Avg, Count
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import StudentProfile, User
from apps.accounts.permissions import IsAdminRole, IsRecruiter, IsStudent
from apps.assessments.models import Quiz, QuizAttempt
from apps.dashboard.analytics import student_analytics
from apps.interviews.models import InterviewSession
from apps.jobs.models import Job, JobApplication
from apps.profiles.utils import profile_completion
from apps.resumes.models import Resume, ResumeAnalysis


class DashboardView(APIView):
    """Role-aware dashboard: returns the tree matching the caller's role."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_admin_role:
            return Response(admin_dashboard())
        if request.user.is_student:
            return Response(student_dashboard(request.user))
        if request.user.is_recruiter:
            return Response(recruiter_dashboard(request.user))
        return Response({})


class StudentDashboardView(APIView):
    """Student-only dashboard endpoint. 403 for any other role."""

    permission_classes = [IsStudent]

    def get(self, request):
        return Response(student_dashboard(request.user))


class RecruiterDashboardView(APIView):
    """Recruiter-only dashboard endpoint. 403 for any other role."""

    permission_classes = [IsRecruiter]

    def get(self, request):
        return Response(recruiter_dashboard(request.user))


class AdminDashboardView(APIView):
    """Admin-only platform overview."""

    permission_classes = [IsAdminRole]

    def get(self, request):
        return Response(admin_dashboard())


# ------------------------------------------------------------------
def student_dashboard(student):
    """The student's own performance dashboard (Phase 8).

    All of the aggregation lives in ``apps.dashboard.analytics``; this function
    only shapes the response. The ``jobs``/``quizzes``/``interviews`` blocks are
    thin aliases over the Phase 8 sections, kept so the pre-Phase-8 response
    contract keeps working for existing consumers. They reuse the numbers
    already computed above rather than re-querying, so adding the analytics did
    not add queries.
    """
    data = student_analytics(student)
    applications = data["applications"]
    quizzes = data["quiz_performance"]
    interviews = data["interview_performance"]

    return {
        **data,
        "jobs": {
            "openings": data["overview"]["jobs_available"],
            "available_jobs": data["overview"]["jobs_available"],
            "total_applications": applications["total"],
            "applications": applications["total"],
            "best_match": applications["best_match"],
            "by_status": applications["by_status"],
            "recent": applications["recent"],
        },
        "quizzes": {
            "attempts": quizzes["attempts_completed"],
            # None (not 0) when nothing has been submitted, so the UI can say
            # "no attempts" instead of claiming a 0% average.
            "avg_score": quizzes["average_score"],
            "passed": quizzes["passed"],
        },
        "interviews": {
            "total": interviews["total"],
            "completed": interviews["completed"],
        },
    }


def recruiter_dashboard(recruiter):
    jobs = Job.objects.filter(recruiter=recruiter)
    app_qs = JobApplication.objects.filter(job__recruiter=recruiter)
    return {
        "jobs": {
            "total": jobs.count(),
            "active": jobs.filter(is_active=True).count(),
            "applications": app_qs.count(),
            "by_status": {
                "applied": app_qs.filter(status=JobApplication.Status.APPLIED).count(),
                "shortlisted": app_qs.filter(status=JobApplication.Status.SHORTLISTED).count(),
                "interview": app_qs.filter(status=JobApplication.Status.INTERVIEW).count(),
                "selected": app_qs.filter(status=JobApplication.Status.SELECTED).count(),
                "rejected": app_qs.filter(status=JobApplication.Status.REJECTED).count(),
            },
            "avg_match": int(app_qs.aggregate(a=Avg("match_score"))["a"] or 0),
        },
    }


def admin_dashboard():
    roles = {
        r: User.objects.filter(role=r).count()
        for r in dict(User.Role.choices)
    }
    return {
        "users": {
            **roles,
            "total": User.objects.count(),
        },
        "jobs": {
            "total": Job.objects.count(),
            "active": Job.objects.filter(is_active=True).count(),
            "applications": JobApplication.objects.count(),
        },
        "quizzes": {
            "quizzes": Quiz.objects.count(),
            "attempts": QuizAttempt.objects.count(),
            "avg_score": int(QuizAttempt.objects.filter(submitted_at__isnull=False).aggregate(a=Avg("score_percent"))["a"] or 0),
        },
        "interviews": {
            "sessions": InterviewSession.objects.count(),
            "completed": InterviewSession.objects.filter(status=InterviewSession.Status.COMPLETED).count(),
        },
        "colleges": StudentProfile.objects.exclude(college="").values("college").annotate(n=Count("id")).order_by("-n")[:5],
    }