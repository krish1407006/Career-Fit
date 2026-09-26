"""URLs for direct resume-analysis access (``/api/resume-analyses/<id>/``)."""

from django.urls import path

from .views import ResumeAnalysisDetailView

urlpatterns = [
    path("<int:pk>/", ResumeAnalysisDetailView.as_view(), name="resume-analysis-detail"),
]
