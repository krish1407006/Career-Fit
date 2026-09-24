from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import RecruiterProfile, StudentProfile

from .models import Difficulty, Question, Quiz, QuizAttempt, QuizQuestionAnswer

User = get_user_model()


class QuizAPITestCase(APITestCase):
    """Shared setup: role users, auth helper, and quiz/attempt factories."""

    @staticmethod
    def make_student(username, password="Str0ngPass!23"):
        user = User.objects.create_user(
            username=username,
            password=password,
            email=f"{username}@example.com",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=user, full_name=username.title())
        return user

    @staticmethod
    def make_recruiter(username, password="Str0ngPass!23"):
        user = User.objects.create_user(
            username=username,
            password=password,
            email=f"{username}@example.com",
            role=User.Role.RECRUITER,
        )
        RecruiterProfile.objects.create(user=user, company_name=username.title())
        return user

    @staticmethod
    def make_admin(username, password="Str0ngPass!23"):
        user = User.objects.create_user(
            username=username,
            password=password,
            email=f"{username}@example.com",
            role=User.Role.ADMIN,
        )
        user.is_staff = True
        user.save()
        return user

    def login(self, username, password="Str0ngPass!23"):
        response = self.client.post(
            "/api/auth/login/", {"username": username, "password": password}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response.data

    @staticmethod
    def make_quiz(title="Python Test", questions=5, **kwargs):
        quiz = Quiz.objects.create(
            title=title,
            description="A test quiz.",
            category=kwargs.pop("category", Quiz.Category.PYTHON),
            difficulty=kwargs.pop("difficulty", Difficulty.MEDIUM),
            duration_minutes=kwargs.pop("duration_minutes", 10),
            **kwargs,
        )
        for i in range(questions):
            Question.objects.create(
                quiz=quiz,
                text=f"Question {i + 1}",
                options=["A", "B", "C", "D"],
                correct_index=i % 4,
                explanation=f"Explanation {i + 1}",
                topic=f"Topic {i + 1}",
                difficulty="easy" if i % 2 == 0 else "medium",
            )
        return quiz

    def start_quiz(self, quiz_id):
        return self.client.post(f"/api/quizzes/{quiz_id}/start/", format="json")

    def submit(self, quiz_id, answers):
        return self.client.post(
            f"/api/quizzes/{quiz_id}/submit/", {"answers": answers}, format="json"
        )


class QuizStudentFlowTests(QuizAPITestCase):
    """Scenarios 1-5, 11-12: list/start/no-leak/submit/scoring/attempts."""

    def setUp(self):
        self.student = self.make_student("stu1")
        self.quiz = self.make_quiz(title="Python Basics", questions=4)
        self.quiz_answers = {str(q.id): q.correct_index for q in self.quiz.questions.all()}
        self.login("stu1")

    def test_can_list_active_quizzes_with_attempt_summary(self):
        response = self.client.get("/api/quizzes/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [quiz["title"] for quiz in response.data]
        self.assertIn("Python Basics", titles)
        row = next(q for q in response.data if q["title"] == "Python Basics")
        self.assertEqual(row["category"], "python")
        self.assertEqual(row["difficulty"], "medium")
        self.assertEqual(row["total_questions"], 4)
        self.assertFalse(row["attempted"])

    def test_student_can_start_quiz_without_answer_leak(self):
        response = self.start_quiz(self.quiz.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["quiz"]["title"], "Python Basics")
        self.assertEqual(response.data["countdown_seconds"], 600)
        for q in response.data["questions"]:
            self.assertNotIn("correct_index", q)
            self.assertNotIn("explanation", q)
        self.assertTrue(QuizAttempt.objects.filter(student=self.student, quiz=self.quiz).exists())

    def test_repeat_start_is_idempotent_and_single_attempt(self):
        self.start_quiz(self.quiz.id)
        response = self.start_quiz(self.quiz.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(
            QuizAttempt.objects.filter(student=self.student, quiz=self.quiz).count(), 1)

    def test_submit_scores_server_side_and_blocks_resubmission(self):
        self.start_quiz(self.quiz.id)

        response = self.submit(self.quiz.id, self.quiz_answers)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        attempt = QuizAttempt.objects.get(student=self.student, quiz=self.quiz)
        self.assertEqual(response.data["correct_count"], 4)
        self.assertEqual(response.data["incorrect_count"], 0)
        self.assertEqual(response.data["total"], 4)
        self.assertEqual(response.data["score_percent"], 100)
        self.assertTrue(response.data["passed"])
        self.assertEqual(attempt.status, QuizAttempt.Status.COMPLETED)
        self.assertIsNotNone(attempt.submitted_at)

        second = self.submit(self.quiz.id, self.quiz_answers)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_attempt_details_and_question_answers_persisted(self):
        self.start_quiz(self.quiz.id)
        answers = {
            str(q.id): (q.correct_index if i % 2 == 0 else (q.correct_index + 1) % 4)
            for i, q in enumerate(self.quiz.questions.all())
        }
        self.submit(self.quiz.id, answers)

        attempt = QuizAttempt.objects.get(student=self.student, quiz=self.quiz)
        self.assertEqual(attempt.incorrect_count, 2)
        self.assertEqual(attempt.correct_count, 2)
        self.assertEqual(QuizQuestionAnswer.objects.filter(attempt=attempt).count(), 4)
        self.assertEqual(attempt.answers, {str(q.id): answers[str(q.id)]
                                           for q in self.quiz.questions.all()})

        detail = self.client.get(f"/api/quiz-attempts/{attempt.id}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK, detail.data)
        self.assertEqual(len(detail.data["per_question"]), 4)
        review = detail.data["per_question"][0]
        for key in ("correct_index", "explanation", "chosen_index", "is_correct"):
            self.assertIn(key, review)
        self.assertIn("passed", detail.data)

    def test_legacy_submit_alias_and_mine_history(self):
        self.start_quiz(self.quiz.id)
        attempt = QuizAttempt.objects.get(student=self.student, quiz=self.quiz)
        legacy = self.client.post(
            f"/api/quizzes/attempts/{attempt.id}/submit/",
            {"answers": self.quiz_answers}, format="json")
        self.assertEqual(legacy.status_code, status.HTTP_200_OK, legacy.data)
        mine = self.client.get("/api/quizzes/attempts/mine/")
        self.assertEqual(mine.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mine.data), 1)
        canonical = self.client.get("/api/quiz-attempts/")
        self.assertEqual(canonical.status_code, status.HTTP_200_OK)
        self.assertEqual(len(canonical.data), 1)

    def test_cannot_start_or_submit_inactive_quiz(self):
        inactive = self.make_quiz(title="Dormant", is_active=False)
        resp = self.start_quiz(inactive.id)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        resp2 = self.submit(inactive.id, {})
        self.assertEqual(resp2.status_code, status.HTTP_404_NOT_FOUND)
        inactive_detail = self.client.get(f"/api/quizzes/{inactive.id}/")
        self.assertEqual(inactive_detail.status_code, status.HTTP_404_NOT_FOUND)

    def test_submit_without_attempt_is_404(self):
        response = self.submit(self.quiz.id, {})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_submit_after_inactive_and_legacy_resubmit_already_submitted(self):
        self.start_quiz(self.quiz.id)
        attempt = QuizAttempt.objects.get(student=self.student, quiz=self.quiz)
        resp = self.client.post(
            f"/api/quizzes/attempts/{attempt.id}/submit/", {"answers": {}}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        again = self.client.post(
            f"/api/quizzes/attempts/{attempt.id}/submit/", {"answers": {}}, format="json")
        self.assertEqual(again.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_answer_indices_are_ignored(self):
        self.start_quiz(self.quiz.id)
        first_qid = str(self.quiz.questions.first().id)
        response = self.submit(self.quiz.id, {first_qid: 99, "banana": "x"})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["correct_count"], 0)
        self.assertEqual(response.data["incorrect_count"], 4)


class QuizTimeoutTests(QuizAPITestCase):
    """Scenario: server-side time-limit enforcement auto-completes the attempt."""

    def test_expired_timer_auto_submits_and_returns_400(self):
        student = self.make_student("stu2")
        quiz = self.make_quiz(title="Timed", questions=3, duration_minutes=1)
        correct = {str(q.id): q.correct_index for q in quiz.questions.all()}
        self.login("stu2")

        self.start_quiz(quiz.id)
        attempt = QuizAttempt.objects.get(student=student, quiz=quiz)
        attempt.answers = correct
        attempt.save()
        QuizAttempt.objects.filter(pk=attempt.id).update(
            started_at=timezone.now() - timedelta(minutes=3))

        response = self.submit(quiz.id, correct)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, QuizAttempt.Status.COMPLETED)
        self.assertIsNotNone(attempt.submitted_at)
        self.assertEqual(attempt.correct_count, 3)


class QuizAccessControlTests(QuizAPITestCase):
    """Scenarios: ownership isolation, role locks, answer secrecy after submit"""

    def setUp(self):
        self.stu_a = self.make_student("stu_a")
        self.stu_b = self.make_student("stu_b")
        self.quiz = self.make_quiz(title="Shared Quiz", questions=3)
        self.answers = {str(q.id): q.correct_index for q in self.quiz.questions.all()}

    def test_student_cannot_view_another_students_attempt(self):
        self.login("stu_a")
        self.start_quiz(self.quiz.id)
        self.submit(self.quiz.id, self.answers)
        attempt = QuizAttempt.objects.get(student=self.stu_a, quiz=self.quiz)

        self.login("stu_b")
        response = self.client.get(f"/api/quiz-attempts/{attempt.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_in_progress_attempt_has_no_review_until_submitted(self):
        self.login("stu_a")
        self.start_quiz(self.quiz.id)
        attempt = QuizAttempt.objects.get(student=self.stu_a, quiz=self.quiz)
        detail = self.client.get(f"/api/quiz-attempts/{attempt.id}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data["per_question"], [])
        self.assertIsNone(detail.data["score_percent"])

    def test_recruiter_cannot_start_or_submit_quizzes(self):
        self.make_recruiter("recz")
        self.login("recz")
        self.assertEqual(self.start_quiz(self.quiz.id).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.submit(self.quiz.id, {}).status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_access_admin_endpoints(self):
        self.login("stu_a")
        for url, method in (
            ("/api/quizzes/admin/", self.client.post),
            (f"/api/quizzes/admin/{self.quiz.id}/", self.client.put),
            (f"/api/quizzes/admin/{self.quiz.id}/", self.client.delete),
            ("/api/quizzes/admin/questions/", self.client.post),
        ):
            response = method(url, {}, format="json")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, url)

    def test_recruiter_cannot_access_admin_endpoints(self):
        self.make_recruiter("recy")
        self.login("recy")
        response = self.client.get("/api/quizzes/admin/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class QuizAdminCRUDTests(QuizAPITestCase):
    """Scenarios 8-9: admin quiz + question management."""

    def setUp(self):
        self.admin = self.make_admin("root_admin")
        self.login("root_admin")
        self.quiz = self.make_quiz(title="CRUD Quiz", questions=3)

    def test_admin_can_list_and_delete_quiz(self):
        response = self.client.get("/api/quizzes/admin/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.quiz.id, [q["id"] for q in response.data])

        resp = self.client.delete(f"/api/quizzes/admin/{self.quiz.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Quiz.objects.filter(id=self.quiz.id).exists())

    def test_admin_can_create_quiz_with_nested_questions(self):
        response = self.client.post(
            "/api/quizzes/admin/",
            {
                "title": "New Admin Quiz",
                "description": "Created over API.",
                "category": "aptitude",
                "difficulty": "easy",
                "duration_minutes": 5,
                "questions": [
                    {"text": "Q1", "options": ["A", "B"], "correct_index": 0,
                     "explanation": "E", "topic": "T", "difficulty": "easy"},
                    {"text": "Q2", "options": ["C", "D", "E"], "correct_index": 2,
                     "explanation": "E2", "topic": "T2", "difficulty": "hard"},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        quiz = Quiz.objects.get(title="New Admin Quiz")
        self.assertEqual(quiz.category, "aptitude")
        self.assertEqual(quiz.questions.count(), 2)
        self.assertEqual(response.data["questions"][0]["correct_index"], 0)

    def test_admin_create_rejects_invalid_nested_question_and_rolls_back(self):
        before = Quiz.objects.count()
        response = self.client.post(
            "/api/quizzes/admin/",
            {
                "title": "Bad Quiz",
                "questions": [
                    {"text": "Good", "options": ["A", "B"], "correct_index": 0,
                     "explanation": "", "topic": "", "difficulty": "easy"},
                    {"text": "Bad", "options": ["A"], "correct_index": 5,
                     "explanation": "", "topic": "", "difficulty": "easy"},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Quiz.objects.filter(title="Bad Quiz").exists())
        self.assertEqual(Quiz.objects.count(), before)

    def test_admin_can_update_quiz_and_replace_nested_questions(self):
        questions = list(self.quiz.questions.all())
        keep, drop = questions[0], questions[1]
        response = self.client.put(
            f"/api/quizzes/admin/{self.quiz.id}/",
            {
                "title": "CRUD Quiz Updated",
                "description": "Changed.",
                "category": "django",
                "difficulty": "hard",
                "duration_minutes": None,
                "is_active": False,
                "questions": [
                    {"id": keep.id, "text": "Updated Q",
                     "options": ["X", "Y"], "correct_index": 1,
                     "explanation": "New", "topic": "New", "difficulty": "easy"},
                    {"text": "Fresh Q", "options": ["P", "Q", "R"], "correct_index": 0,
                     "explanation": "F", "topic": "F", "difficulty": "easy"},
                ],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        quiz = Quiz.objects.get(pk=self.quiz.id)
        self.assertEqual(quiz.title, "CRUD Quiz Updated")
        self.assertEqual(quiz.category, "django")
        self.assertEqual(quiz.difficulty, "hard")
        self.assertIsNone(quiz.duration_minutes)
        self.assertFalse(quiz.is_active)
        self.assertFalse(Quiz.objects.filter(pk=drop.id).exists())
        self.assertEqual(quiz.questions.count(), 2)
        keep.refresh_from_db()
        self.assertEqual(keep.text, "Updated Q")

    def test_admin_question_endpoints_create_update_delete(self):
        payload = {
            "quiz": self.quiz.id,
            "text": "Standalone Q", "options": ["A2", "B2"],
            "correct_index": 1, "explanation": "S", "topic": "S", "difficulty": "medium",
        }
        resp = self.client.post("/api/quizzes/admin/questions/", payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        qid = resp.data["id"]

        resp = self.client.patch(
            f"/api/quizzes/admin/questions/{qid}/", {"text": "A rewritten Q"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["text"], "A rewritten Q")

        resp = self.client.delete(f"/api/quizzes/admin/questions/{qid}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Question.objects.filter(pk=qid).exists())

    def test_admin_question_rejects_bad_options(self):
        resp = self.client.post(
            "/api/quizzes/admin/questions/",
            {"quiz": self.quiz.id, "text": "Broken", "options": ["Only one"], "correct_index": 1},
            format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_access_student_endpoints(self):
        list_resp = self.client.get("/api/quizzes/")
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        detail = self.client.get(f"/api/quizzes/{self.quiz.id}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertNotIn("questions", detail.data)