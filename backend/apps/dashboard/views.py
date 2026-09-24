from django.db.models import Avg, Count
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import StudentProfile, User
from apps.accounts.permissions import IsAdminRole, IsRecruiter, IsStudent
from apps.assessments.models import Quiz, QuizAttempt
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
    resume = Resume.objects.filter(user=student).first()
    analysis = (
        resume.analysis if resume and hasattr(resume, "analysis") else None
    )
    apps = JobApplication.objects.filter(student=student)
    attempts = QuizAttempt.objects.filter(student=student)
    interviews = InterviewSession.objects.filter(student=student)
    profile, _ = StudentProfile.objects.get_or_create(user=student)

    return {
        "resume": {
            "status": resume.status if resume else "none",
            "score": analysis.score if analysis else None,
            "skills_count": len(analysis.skills) if analysis else 0,
            "suggestions_count": len(analysis.suggestions) if analysis else 0,
            "source": analysis.source if analysis else None,
        },
        "profile": {
            "completion": profile_completion(profile),
            "skills_count": profile.skills.count(),
            "projects_count": profile.projects.count(),
            "resume_uploaded": resume is not None,
        },
        "jobs": {
            "openings": Job.objects.filter(is_active=True).count(),
            "applications": apps.count(),
            "shortlisted": apps.filter(status=JobApplication.Status.SHORTLISTED).count(),
            "selected": apps.filter(status=JobApplication.Status.SELECTED).count(),
            "best_match": apps.order_by("-match_score").first().match_score if apps.exists() else None,
        },
        "quizzes": {
            "attempts": attempts.count(),
            "avg_score": int(attempts.filter(submitted_at__isnull=False).aggregate(a=Avg("score_percent"))["a"] or 0),
            "passed": attempts.filter(submitted_at__isnull=False, score_percent__gte=60).count(),
        },
        "interviews": {
            "total": interviews.count(),
            "completed": interviews.filter(status=InterviewSession.Status.COMPLETED).count(),
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