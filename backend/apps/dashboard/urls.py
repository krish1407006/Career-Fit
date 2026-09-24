from django.urls import path

from .views import (
    AdminDashboardView,
    DashboardView,
    RecruiterDashboardView,
    StudentDashboardView,
)

app_name = "dashboard"

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("dashboard/student/", StudentDashboardView.as_view(), name="dashboard-student"),
    path("dashboard/recruiter/", RecruiterDashboardView.as_view(), name="dashboard-recruiter"),
    path("dashboard/admin/", AdminDashboardView.as_view(), name="dashboard-admin"),
]