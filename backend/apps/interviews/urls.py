from django.urls import path

from .views import InterviewAnswerView, InterviewDetailView, InterviewStartView, MyInterviewsView

app_name = "interviews"

urlpatterns = [
    path("interviews/start/", InterviewStartView.as_view(), name="interview-start"),
    path("interviews/mine/", MyInterviewsView.as_view(), name="my-interviews"),
    path("interviews/<int:pk>/", InterviewDetailView.as_view(), name="interview-detail"),
    path("interviews/<int:pk>/answer/", InterviewAnswerView.as_view(), name="interview-answer"),
]