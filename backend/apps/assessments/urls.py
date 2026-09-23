from django.urls import path

from .views import MyAttemptsView, QuizAdminView, QuizDetailView, QuizListView, QuizStartView, QuizSubmitView

app_name = "assessments"

urlpatterns = [
    path("quizzes/", QuizListView.as_view(), name="quiz-list"),
    path("quizzes/admin/", QuizAdminView.as_view(), name="quiz-admin"),
    path("quizzes/<int:pk>/", QuizDetailView.as_view(), name="quiz-detail"),
    path("quizzes/<int:pk>/start/", QuizStartView.as_view(), name="quiz-start"),
    path("quizzes/attempts/<int:attempt_id>/submit/", QuizSubmitView.as_view(), name="quiz-submit"),
    path("quizzes/attempts/mine/", MyAttemptsView.as_view(), name="quiz-attempts"),
]