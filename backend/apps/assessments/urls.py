from django.urls import path

from .views import (
    MyAttemptsView,
    QuestionAdminDetailView,
    QuestionAdminView,
    QuizAdminDetailView,
    QuizAdminListView,
    QuizAttemptDetailView,
    QuizDetailView,
    QuizListView,
    QuizStartView,
    QuizSubmitByAttemptView,
    QuizSubmitView,
)

app_name = "assessments"

urlpatterns = [
    # Student-facing
    path("quizzes/", QuizListView.as_view(), name="quiz-list"),
    path("quizzes/<int:pk>/", QuizDetailView.as_view(), name="quiz-detail"),
    path("quizzes/<int:pk>/start/", QuizStartView.as_view(), name="quiz-start"),
    path("quizzes/<int:pk>/submit/", QuizSubmitView.as_view(), name="quiz-submit"),
    path("quizzes/attempts/mine/", MyAttemptsView.as_view(), name="quiz-attempts-mine"),
    path("quizzes/attempts/<int:attempt_id>/submit/", QuizSubmitByAttemptView.as_view(),
         name="quiz-submit-attempt"),
    path("quiz-attempts/", MyAttemptsView.as_view(), name="quiz-attempts"),
    path("quiz-attempts/<int:pk>/", QuizAttemptDetailView.as_view(), name="quiz-attempt-detail"),
    # Admin-only management
    path("quizzes/admin/", QuizAdminListView.as_view(), name="quiz-admin-list"),
    path("quizzes/admin/<int:pk>/", QuizAdminDetailView.as_view(), name="quiz-admin-detail"),
    path("quizzes/admin/questions/", QuestionAdminView.as_view(), name="question-admin-create"),
    path("quizzes/admin/questions/<int:pk>/", QuestionAdminDetailView.as_view(),
         name="question-admin-detail"),
]