from django.urls import path

from .views import (
    ApplicationStatusView,
    ApplyToJobView,
    JobApplicantsView,
    JobDetailView,
    JobListView,
    JobMatchView,
    MyApplicationsView,
    MyJobsView,
    RecruiterApplicationsView,
    SkillGapView,
    SkillListView,
)

app_name = "jobs"

urlpatterns = [
    path("skills/", SkillListView.as_view(), name="skills"),
    path("jobs/", JobListView.as_view(), name="job-list"),
    path("jobs/<int:pk>/", JobDetailView.as_view(), name="job-detail"),
    path("jobs/<int:pk>/apply/", ApplyToJobView.as_view(), name="job-apply"),
    path("jobs/<int:pk>/applicants/", JobApplicantsView.as_view(), name="job-applicants"),
    path("jobs/<int:pk>/match/", JobMatchView.as_view(), name="job-match"),
    path("jobs/mine/", MyJobsView.as_view(), name="my-jobs"),
    path("applications/", MyApplicationsView.as_view(), name="my-applications-canonical"),
    path("applications/mine/", MyApplicationsView.as_view(), name="my-applications"),
    path("applications/<int:pk>/status/", ApplicationStatusView.as_view(), name="application-status"),
    path("recruiter/jobs/", MyJobsView.as_view(), name="recruiter-jobs"),
    path("recruiter/applications/", RecruiterApplicationsView.as_view(), name="recruiter-applications"),
    path("skill-gap/", SkillGapView.as_view(), name="skill-gap"),
]