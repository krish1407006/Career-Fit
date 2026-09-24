from django.urls import path

from .views import (
    CertificationDetailView,
    CertificationListCreateView,
    EducationDetailView,
    EducationListCreateView,
    MySkillsView,
    ProfileView,
    ProjectDetailView,
    ProjectListCreateView,
    RemoveSkillView,
)

app_name = "profiles"

urlpatterns = [
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/skills/", MySkillsView.as_view(), name="my-skills"),
    path("profile/skills/<int:pk>/", RemoveSkillView.as_view(), name="remove-skill"),
    path("education/", EducationListCreateView.as_view(), name="education-list"),
    path("education/<int:pk>/", EducationDetailView.as_view(), name="education-detail"),
    path("projects/", ProjectListCreateView.as_view(), name="project-list"),
    path("projects/<int:pk>/", ProjectDetailView.as_view(), name="project-detail"),
    path("certifications/", CertificationListCreateView.as_view(), name="certification-list"),
    path("certifications/<int:pk>/", CertificationDetailView.as_view(), name="certification-detail"),
]