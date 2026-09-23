from django.db.models import Count, OuterRef, Subquery
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole, IsStudent
from apps.accounts.models import User

from .models import Question, Quiz, QuizAttempt
from .serializers import (
    QuestionReadSerializer,
    QuestionResultSerializer,
    QuestionSerializer,
    QuizDetailSerializer,
    QuizListSerializer,
    QuizSubmitResultSerializer,
)

PASS_THRESHOLD = 60


class QuizAdminView(APIView):
    """Admin CRUD for quizzes (with nested questions)."""

    permission_classes = [IsAdminRole]

    def get(self, request):
        quizzes = Quiz.objects.annotate(total_questions=Count("questions"))
        return Response(QuizListSerializer(quizzes, many=True).data)

    def post(self, request):
        data = request.data
        title = data.get("title") or ""
        if not title:
            return Response({"detail": "Title is required."}, status=status.HTTP_400_BAD_REQUEST)
        quiz = Quiz.objects.create(
            title=title,
            description=data.get("description", ""),
            category=data.get("category", Quiz.Category.TECHNICAL),
            duration_minutes=int(data.get("duration_minutes", 15) or 15),
            is_active=bool(data.get("is_active", True)),
            created_by=request.user,
        )
        errors = self._create_questions(quiz, data.get("questions", []))
        if errors:
            quiz.delete()
            return Response({"detail": errors[0]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(QuizDetailSerializer(quiz).data, status=status.HTTP_201_CREATED)

    def _create_questions(self, quiz, questions):
        for q in questions:
            options = q.get("options") or []
            correct = q.get("correct_index")
            if len(options) < 2 or correct is None or not (0 <= correct < len(options)):
                return [f"Question \"{q.get('text', '')[:40]}\" needs at least 2 options and a valid correct_index."]
            Question.objects.create(
                quiz=quiz, text=q["text"], options=options,
                correct_index=int(correct), explanation=q.get("explanation", ""),
            )
        return []


class QuizListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_admin_role:
            quizzes = Quiz.objects.annotate(total_questions=Count("questions"))
        else:
            quizzes = Quiz.objects.filter(is_active=True).annotate(total_questions=Count("questions"))
        if request.user.is_student:
            attempts = QuizAttempt.objects.filter(student=request.user)
            att_map = {a.quiz_id: a for a in attempts}
            for q in quizzes:
                q._attempt = att_map.get(q.id)
        return Response(QuizListSerializer(quizzes, many=True).data)


class QuizStartView(APIView):
    """Start a quiz: creates an attempt (idempotent) and returns questions sans answers."""

    permission_classes = [IsStudent]

    def post(self, request, pk):
        try:
            quiz = Quiz.objects.get(pk=pk, is_active=True)
        except Quiz.DoesNotExist:
            return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)
        attempt, created = QuizAttempt.objects.get_or_create(student=request.user, quiz=quiz)
        questions = quiz.questions.all()
        return Response({
            "attempt_id": attempt.id,
            "quiz": QuizDetailSerializer(quiz).data,
            "questions": QuestionReadSerializer(questions, many=True).data,
            "countdown_seconds": quiz.duration_minutes * 60,
        })


class QuizSubmitView(APIView):
    """Submit answers and evaluate immediately."""

    permission_classes = [IsStudent]

    def post(self, request, attempt_id):
        try:
            attempt = QuizAttempt.objects.select_related("quiz").get(
                pk=attempt_id, student=request.user)
        except QuizAttempt.DoesNotExist:
            return Response({"detail": "Attempt not found."}, status=status.HTTP_404_NOT_FOUND)
        if attempt.submitted_at:
            return Response({"detail": "Already submitted."}, status=status.HTTP_400_BAD_REQUEST)

        answers = request.data.get("answers", {})
        questions = list(attempt.quiz.questions.all())
        correct = 0
        per_question = []
        for q in questions:
            chosen = answers.get(str(q.id))
            is_correct = chosen is not None and int(chosen) == q.correct_index
            if is_correct:
                correct += 1
            per_question.append({
                "question_id": q.id,
                "correct_index": q.correct_index,
                "your_index": int(chosen) if chosen is not None else None,
                "is_correct": is_correct,
                "explanation": q.explanation,
            })
        total = len(questions)
        percent = round((correct / total) * 100) if total else 0
        from django.utils import timezone
        attempt.answers = answers
        attempt.correct_count = correct
        attempt.total = total
        attempt.score_percent = percent
        attempt.submitted_at = timezone.now()
        attempt.save(update_fields=["answers", "correct_count", "total", "score_percent", "submitted_at"])
        return Response({
            "attempt_id": attempt.id,
            "correct_count": correct,
            "total": total,
            "score_percent": percent,
            "passed": percent >= PASS_THRESHOLD,
            "per_question": [QuestionResultSerializer(r).data for r in per_question],
        })


class MyAttemptsView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        attempts = QuizAttempt.objects.filter(student=request.user)
        from .serializers import QuizAttemptSerializer
        return Response(QuizAttemptSerializer(attempts, many=True).data)


class QuizDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            quiz = Quiz.objects.annotate(total_questions=Count("questions")).get(pk=pk)
        except Quiz.DoesNotExist:
            return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)
        if not request.user.is_admin_role and not quiz.is_active:
            return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(QuizDetailSerializer(quiz).data)