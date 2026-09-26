from django.urls import path

from .views import (
    ActiveInterviewView,
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
