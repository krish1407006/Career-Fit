from django.urls import path

from .views import ResumeDetailView, ResumeListCreateView

app_name = "resumes"

urlpatterns = [
    path("", ResumeListCreateView.as_view(), name="resume-list"),
    path("<int:pk>/", ResumeDetailView.as_view(), name="resume-detail"),
]