from django.urls import path

from .views import (
    ResumeAnalysisView,
    ResumeAnalyzeView,
    ResumeDetailView,
    ResumeDownloadView,
    ResumeListCreateView,
)

app_name = "resumes"

urlpatterns = [
    path("", ResumeListCreateView.as_view(), name="resume-list"),
    path("<int:pk>/", ResumeDetailView.as_view(), name="resume-detail"),
    path("<int:pk>/download/", ResumeDownloadView.as_view(), name="resume-download"),
    path("<int:pk>/analyze/", ResumeAnalyzeView.as_view(), name="resume-analyze"),
    path("<int:pk>/analysis/", ResumeAnalysisView.as_view(), name="resume-analysis"),
]
