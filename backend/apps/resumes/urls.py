from django.urls import path

from .views import ResumeDetailView, ResumeDownloadView, ResumeListCreateView

app_name = "resumes"

urlpatterns = [
    path("", ResumeListCreateView.as_view(), name="resume-list"),
    path("<int:pk>/", ResumeDetailView.as_view(), name="resume-detail"),
    path("<int:pk>/download/", ResumeDownloadView.as_view(), name="resume-download"),
]