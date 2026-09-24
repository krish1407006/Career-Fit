from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdminRole, IsStudent

from .models import Difficulty, Question, Quiz, QuizAttempt, QuizQuestionAnswer
from .serializers import (
    PASS_THRESHOLD,
    QuestionAdminSerializer,
    QuestionReadSerializer,
    QuestionSerializer,
    QuizAdminDetailSerializer,
    QuizAttemptDetailSerializer,
    QuizAttemptSerializer,
    QuizDetailSerializer,
    QuizListSerializer,
    build_review,
)

# Grace applied to server-side time-limit checks (seconds).
# The client auto-submits at 0:00; this absorbs network/clock drift.
TIMEOUT_GRACE_SECONDS = 60


class QuizAdminListView(APIView):
    """Admin: list all quizzes or create one (with nested questions)."""

    permission_classes = [IsAdminRole]

    def get(self, request):
        quizzes = Quiz.objects.annotate(total_questions=Count("questions"))
        return Response(QuizListSerializer(quizzes, many=True).data)

    def post(self, request):
        quiz = self._create(request)
        if isinstance(quiz, Response):
            return quiz
        return Response(QuizAdminDetailSerializer(quiz).data, status=status.HTTP_201_CREATED)

    def _create(self, request):
        data = request.data
        title = (data.get("title") or "").strip()
        if not title:
            return Response({"detail": "Title is required."}, status=status.HTTP_400_BAD_REQUEST)
        quiz = Quiz.objects.create(
            title=title,
            description=data.get("description", ""),
            category=data.get("category", Quiz.Category.PYTHON),
            difficulty=data.get("difficulty", Difficulty.MEDIUM),
            duration_minutes=data.get("duration_minutes"),
            is_active=bool(data.get("is_active", True)),
            created_by=request.user,
        )
        errors = self._save_questions(quiz, data.get("questions", []))
        if errors:
            quiz.delete()
            return Response({"detail": errors[0]}, status=status.HTTP_400_BAD_REQUEST)
        return quiz

    def _save_questions(self, quiz, questions):
        errors = []
        for q in questions:
            s = QuestionAdminSerializer(data={**q, "quiz": quiz.id})
            if s.is_valid():
                s.save()
            else:
                errors.append(self._first_error(s.errors, q.get("text", "")))
        return errors

    @staticmethod
    def _first_error(errors, question_text):
        detail = list(errors.values())
        msg = (detail[0][0] if detail else "Invalid question.")
        return f"Question \"{str(question_text)[:40]}\": {msg}"


class QuizAdminDetailView(APIView):
    """Admin: view, edit (incl. nested questions) or delete a quiz."""

    permission_classes = [IsAdminRole]

    def _get(self, pk):
        try:
            return (Quiz.objects.prefetch_related("questions")
                    .annotate(total_questions=Count("questions")).get(pk=pk))
        except Quiz.DoesNotExist:
            return None

    def get(self, request, pk):
        quiz = self._get(pk)
        return self._respond(quiz, status.HTTP_200_OK)

    def put(self, request, pk):
        quiz = self._get(pk)
        if not quiz:
            return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)
        data = request.data
        for field in ("title", "description", "category", "difficulty"):
            if field in data:
                setattr(quiz, field, data[field])
        if "duration_minutes" in data:
            value = data.get("duration_minutes")
            quiz.duration_minutes = int(value) if value not in (None, "", 0) else None
        if "is_active" in data:
            quiz.is_active = bool(data.get("is_active"))
        quiz.save()

        if "questions" in data:
            result = self._replace_questions(quiz, data.get("questions") or [])
            if isinstance(result, Response):
                return result

        quiz = self._get(pk)
        return Response(QuizAdminDetailSerializer(quiz).data)

    def patch(self, request, pk):
        return self.put(request, pk)

    def delete(self, request, pk):
        quiz = self._get(pk)
        if not quiz:
            return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)
        quiz.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _replace_questions(self, quiz, questions):
        """Full-question-set replace: create/update by id, delete missing."""

        incoming_ids = []
        for q in questions:
            qid = q.get("id")
            if qid:
                incoming_ids.append(int(qid))
        quiz.questions.exclude(id__in=incoming_ids).delete()

        for q in questions:
            payload = {**q, "quiz": quiz.id}
            qid = q.get("id")
            if qid:
                s = QuestionAdminSerializer(
                    quiz.questions.filter(pk=qid).first(), data=payload, partial=True)
            else:
                s = QuestionAdminSerializer(data=payload)
            if s.is_valid():
                s.save()
            else:
                return Response(
                    {"detail": self._first_error(s.errors, q.get("text", ""))},
                    status=status.HTTP_400_BAD_REQUEST)
        return None

    @staticmethod
    def _first_error(errors, question_text):
        detail = list(errors.values())
        msg = (detail[0][0] if detail else "Invalid question.")
        return f"Question \"{str(question_text)[:40]}\": {msg}"

    def _respond(self, quiz, ok_status):
        if not quiz:
            return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(QuizAdminDetailSerializer(quiz).data, status=ok_status)


class QuestionAdminView(APIView):
    """Admin: add a question to a quiz."""

    permission_classes = [IsAdminRole]

    def post(self, request):
        try:
            quiz = Quiz.objects.get(pk=request.data.get("quiz"))
        except (Quiz.DoesNotExist, TypeError, ValueError):
            return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)
        s = QuestionAdminSerializer(data={**request.data, "quiz": quiz.id})
        if not s.is_valid():
            return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)
        s.save()
        return Response(QuestionSerializer(s.instance).data, status=status.HTTP_201_CREATED)


class QuestionAdminDetailView(APIView):
    """Admin: edit or delete a question."""

    permission_classes = [IsAdminRole]

    def _get(self, pk):
        try:
            return Question.objects.get(pk=pk)
        except Question.DoesNotExist:
            return None

    def put(self, request, pk):
        question = self._get(pk)
        if not question:
            return Response({"detail": "Question not found."}, status=status.HTTP_404_NOT_FOUND)
        s = QuestionAdminSerializer(question, data=request.data, partial=True)
        if not s.is_valid():
            return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)
        s.save()
        return Response(QuestionSerializer(s.instance).data)

    def patch(self, request, pk):
        return self.put(request, pk)

    def delete(self, request, pk):
        question = self._get(pk)
        if not question:
            return Response({"detail": "Question not found."}, status=status.HTTP_404_NOT_FOUND)
        question.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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


class QuizStartView(APIView):
    """Start a quiz: create the attempt (idempotent) and return questions sans answers."""

    permission_classes = [IsStudent]

    def post(self, request, pk):
        try:
            quiz = Quiz.objects.annotate(total_questions=Count("questions")).get(pk=pk, is_active=True)
        except Quiz.DoesNotExist:
            return Response({"detail": "Quiz not found."}, status=status.HTTP_404_NOT_FOUND)
        attempt, created = QuizAttempt.objects.get_or_create(student=request.user, quiz=quiz)
        if not created and attempt.status == QuizAttempt.Status.COMPLETED:
            return Response({"detail": "You have already completed this quiz."},
                            status=status.HTTP_400_BAD_REQUEST)
        questions = quiz.questions.all()
        countdown = quiz.duration_minutes * 60 if quiz.duration_minutes else None
        return Response({
            "attempt_id": attempt.id,
            "quiz": QuizDetailSerializer(quiz).data,
            "questions": QuestionReadSerializer(questions, many=True).data,
            "countdown_seconds": countdown,
        })


# ------------------------------------------------------------------ submit
def _evaluate(attempt, raw_answers):
    """Backend scoring. Never trusts client-provided scores."""
    quiz = attempt.quiz
    questions = list(quiz.questions.all())
    answers = {}
    correct = 0
    for q in questions:
        chosen = raw_answers.get(str(q.id)) if isinstance(raw_answers, dict) else None
        try:
            chosen = int(chosen) if chosen is not None else None
        except (TypeError, ValueError):
            chosen = None
        if chosen is not None and not (0 <= chosen < len(q.options)):
            chosen = None
        answers[str(q.id)] = chosen
        if chosen is not None and chosen == q.correct_index:
            correct += 1
    total = len(questions)
    incorrect = total - correct
    percent = round((correct / total) * 100) if total else 0

    attempt.answers = answers
    attempt.correct_count = correct
    attempt.incorrect_count = incorrect
    attempt.total = total
    attempt.score_percent = percent
    # Store per-question rows (kept separate from the answer key).
    QuizQuestionAnswer.objects.filter(attempt=attempt).delete()
    QuizQuestionAnswer.objects.bulk_create([
        QuizQuestionAnswer(attempt=attempt, question=q, chosen_index=answers[str(q.id)],
                           is_correct=answers[str(q.id)] is not None and answers[str(q.id)] == q.correct_index)
        for q in questions
    ])
    attempt.save(update_fields=["answers", "correct_count", "incorrect_count", "total",
                                "score_percent"])
    return correct, incorrect, total, percent


def _finalize_submission(attempt):
    attempt.status = QuizAttempt.Status.COMPLETED
    attempt.submitted_at = timezone.now()
    attempt.save(update_fields=["status", "submitted_at"])
    return attempt


def _expire_attempt(attempt):
    """Server-side time-limit enforcement: close the attempt with stored answers."""
    if attempt.status == QuizAttempt.Status.COMPLETED:
        return
    raw = attempt.answers or {}
    _evaluate(attempt, raw)
    attempt.status = QuizAttempt.Status.COMPLETED
    attempt.submitted_at = timezone.now()
    attempt.save(update_fields=["status", "submitted_at"])


def _submit_payload(attempt):
    return {
        "attempt_id": attempt.id,
        "correct_count": attempt.correct_count,
        "incorrect_count": attempt.incorrect_count,
        "total": attempt.total,
        "score_percent": attempt.score_percent,
        "passed": attempt.score_percent >= PASS_THRESHOLD,
        "status": attempt.status,
        "per_question": build_review(attempt),
    }


class QuizSubmitView(APIView):
    """POST /api/quizzes/<id>/submit/ — submit by QUIZ id (canonical)."""

    permission_classes = [IsStudent]

    def post(self, request, pk):
        return self._handle(request, quiz_id=pk)

    def _handle(self, request, quiz_id=None, attempt_id=None):
        if attempt_id is not None:
            attempt = QuizAttempt.objects.select_related("quiz").filter(
                pk=attempt_id, student=request.user).first()
        else:
            attempt = QuizAttempt.objects.select_related("quiz").filter(
                quiz_id=quiz_id, student=request.user).first()
        if not attempt:
            return Response({"detail": "Attempt not found. Start the quiz first."},
                            status=status.HTTP_404_NOT_FOUND)
        if attempt.status == QuizAttempt.Status.COMPLETED:
            return Response({"detail": "Already submitted."}, status=status.HTTP_400_BAD_REQUEST)

        if attempt.quiz.duration_minutes:
            allowed = attempt.quiz.duration_minutes * 60
            elapsed = (timezone.now() - attempt.started_at).total_seconds()
            if elapsed > allowed + TIMEOUT_GRACE_SECONDS:
                _expire_attempt(attempt)
                attempt = QuizAttempt.objects.select_related("quiz").get(pk=attempt.pk)
                return Response(
                    {"detail": "Time limit exceeded. Your attempt was submitted "
                               "automatically with your saved answers.",
                     "attempt_id": attempt.id},
                    status=status.HTTP_400_BAD_REQUEST)

        _evaluate(attempt, request.data.get("answers", {}))
        _finalize_submission(attempt)
        attempt = QuizAttempt.objects.select_related("quiz").get(pk=attempt.pk)
        return Response(_submit_payload(attempt))


class QuizSubmitByAttemptView(QuizSubmitView):
    """Legacy alias: POST /quizzes/attempts/<attempt_id>/submit/."""

    def post(self, request, attempt_id):
        return self._handle(request, attempt_id=attempt_id)


class MyAttemptsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_admin_role:
            attempts = QuizAttempt.objects.all()
        else:
            attempts = QuizAttempt.objects.filter(student=request.user)
        return Response(QuizAttemptSerializer(attempts, many=True).data)


class QuizAttemptDetailView(APIView):
    """GET /api/quiz-attempts/<id>/ — a student's own attempt with review."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if request.user.is_admin_role:
            attempt = QuizAttempt.objects.select_related("quiz").filter(pk=pk).first()
        else:
            attempt = QuizAttempt.objects.select_related("quiz").filter(
                pk=pk, student=request.user).first()
        if not attempt:
            # Do not reveal existence of other students' attempts.
            return Response({"detail": "Attempt not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(QuizAttemptDetailSerializer(attempt).data)