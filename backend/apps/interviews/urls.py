from django.urls import path

from .views import (
    ActiveInterviewView,
    AdminInterviewListView,
    InterviewAnswerView,
    InterviewCancelView,
    InterviewCompleteView,
    InterviewDetailView,
    InterviewReportView,
    InterviewStartView,
    MyInterviewsView,
)

app_name = "interviews"

urlpatterns = [
    # The admin-wide list lives under its own path so /api/interviews/ stays
    # scoped to the caller, exactly as the student client expects.
    path("interviews/admin/", AdminInterviewListView.as_view(), name="interview-admin-list"),
    path("interviews/start/", InterviewStartView.as_view(), name="interview-start"),
    # Phase 7: /mine/ is kept for backwards compatibility with Phase 1-6 clients.
    path("interviews/mine/", MyInterviewsView.as_view(), name="my-interviews"),
    path("interviews/", MyInterviewsView.as_view(), name="interview-list"),
    path("interviews/active/", ActiveInterviewView.as_view(), name="interview-active"),
    path("interviews/<int:pk>/", InterviewDetailView.as_view(), name="interview-detail"),
    path("interviews/<int:pk>/answer/", InterviewAnswerView.as_view(), name="interview-answer"),
    path("interviews/<int:pk>/complete/", InterviewCompleteView.as_view(), name="interview-complete"),
    path("interviews/<int:pk>/cancel/", InterviewCancelView.as_view(), name="interview-cancel"),
    path("interviews/<int:pk>/report/", InterviewReportView.as_view(), name="interview-report"),
]
