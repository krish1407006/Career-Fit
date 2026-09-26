"""Phase 7 voice-interview tests.

Every external AI call is mocked: no test performs a network request.
"""

from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.ai import interview_service
from apps.ai.errors import AiParseError, ProviderUnavailable
from apps.jobs.models import Job, Skill
from apps.accounts.models import StudentProfile

from .models import InterviewSession, InterviewTurn

User = get_user_model()

QUESTION_PAYLOAD = {
    "question": "Can you explain how you implemented authentication in that Django project?",
    "category": "project",
}

EVALUATION_PAYLOAD = {
    "score": 7,
    "technical_correctness": "Token handling and permission classes were described correctly.",
    "relevance": "Directly answers the authentication question.",
    "clarity": "Well structured answer.",
    "completeness": "Covers the happy path but not token refresh.",
    "strengths": ["Named a real project", "Explained the trade-off"],
    "improvements": ["Mention token refresh and expiry"],
    "feedback": "Good grounding in a real project; add token refresh for depth.",
}

REPORT_PAYLOAD = {
    "summary": "You showed solid project grounding and clear communication.",
    "technical_strengths": ["Explains real project trade-offs"],
    "areas_to_improve": ["Token lifecycle details"],
    "topics_to_prepare": ["JWT refresh rotation"],
}


def make_student(username, password="Str0ngPass!23", **kwargs):
    user = User.objects.create_user(
        username=username, password=password, role=User.Role.STUDENT, **kwargs
    )
    StudentProfile.objects.create(user=user, full_name=username.title())
    return user


class InterviewTestBase(TestCase):
    def setUp(self):
        self.student = make_student("student_a")
        self.other = make_student("student_b")
        self.client = APIClient()
        self.client.force_authenticate(self.student)
        self.url = "/api/interviews/start/"

    def start(self, **overrides):
        payload = {"position": "Python Developer", "total_questions": 3, **overrides}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def session(self, **kwargs):
        return InterviewSession.objects.create(
            student=self.student,
            position="Python Developer",
            total_questions=kwargs.pop("total_questions", 2),
            **kwargs,
        )

    def add_question(self, session, content="Explain list vs tuple."):
        return InterviewTurn.objects.create(
            session=session,
            role=InterviewTurn.Role.ASSISTANT,
            kind=InterviewTurn.Kind.QUESTION,
            content=content,
            category="technical",
        )


class StartInterviewTests(InterviewTestBase):
    def test_student_can_start_interview(self):
        """1. Student can start an interview."""
        data = self.start()
        self.assertEqual(data["status"], InterviewSession.Status.IN_PROGRESS)
        self.assertEqual(data["mode"], "text")
        self.assertEqual(data["state"], InterviewSession.State.AWAITING_ANSWER)
        self.assertEqual(data["question_index"], 0)
        self.assertIsNotNone(data["started_at"])
        # A first question exists and is offered as the current question.
        self.assertEqual(len(data["turns"]), 1)
        self.assertEqual(data["turns"][0]["kind"], "question")
        self.assertEqual(data["current_question"]["content"], data["turns"][0]["content"])
        self.assertEqual(data["resumed"], False)

    def test_start_voice_mode_is_accepted(self):
        data = self.start(mode="voice")
        self.assertEqual(data["mode"], "voice")

    def test_start_requires_a_role(self):
        response = self.client.post(self.url, {"position": "   "}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_start_validates_question_count(self):
        response = self.client.post(
            self.url, {"position": "QA", "total_questions": 99}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_second_simultaneous_session_is_rejected(self):
        """16. Multiple simultaneous interview sessions are handled safely."""
        self.start()
        response = self.client.post(
            self.url, {"position": "Other Role"}, format="json"
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "interview_in_progress")
        self.assertEqual(InterviewSession.objects.filter(student=self.student).count(), 1)

    def test_start_can_target_a_job_posting(self):
        recruiter = User.objects.create_user(
            username="rec", password="Str0ngPass!23", role=User.Role.RECRUITER
        )
        job = Job.objects.create(
            recruiter=recruiter, company_name="Acme", title="Django Developer",
            description="Build APIs", location="Remote",
        )
        job.required_skills.add(Skill.objects.create(name="Django"))
        data = self.start(job=job.id)
        self.assertEqual(data["job"], job.id)
        context = interview_service.build_context(self.student, job=job, position=data["position"])
        self.assertIn("Django Developer", context)
        self.assertIn("Django", context)

    def test_start_ignores_an_unknown_job_id(self):
        data = self.start(job=999999)
        self.assertIsNone(data["job"])

    def test_start_requires_authentication(self):
        client = APIClient()
        self.assertEqual(
            client.post(self.url, {"position": "QA"}, format="json").status_code, 401
        )

    def test_recruiter_cannot_start_an_interview(self):
        recruiter = User.objects.create_user(
            username="rec2", password="Str0ngPass!23", role=User.Role.RECRUITER
        )
        client = APIClient()
        client.force_authenticate(recruiter)
        self.assertEqual(
            client.post(self.url, {"position": "QA"}, format="json").status_code, 403
        )


class OwnershipTests(InterviewTestBase):
    """2, 3, 16. A student only ever sees their own interviews."""

    def setUp(self):
        super().setUp()
        self.mine = self.session()
        self.theirs = InterviewSession.objects.create(
            student=self.other, position="Their Role", total_questions=2
        )

    def test_student_can_read_own_interview(self):
        response = self.client.get(f"/api/interviews/{self.mine.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["position"], "Python Developer")

    def test_student_cannot_read_another_students_interview(self):
        response = self.client.get(f"/api/interviews/{self.theirs.id}/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["code"], "not_found")

    def test_student_cannot_answer_another_students_interview(self):
        self.add_question(self.theirs)
        response = self.client.post(
            f"/api/interviews/{self.theirs.id}/answer/", {"answer": "hello"}, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_student_cannot_read_another_students_report(self):
        self.theirs.status = InterviewSession.Status.COMPLETED
        self.theirs.save()
        response = self.client.get(f"/api/interviews/{self.theirs.id}/report/")
        self.assertEqual(response.status_code, 404)

    def test_mine_list_only_returns_own_sessions(self):
        response = self.client.get("/api/interviews/mine/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([s["id"] for s in response.data], [self.mine.id])

    def test_student_id_in_the_body_is_ignored(self):
        response = self.client.post(
            self.url,
            {"position": "QA", "student": self.other.id, "student_id": self.other.id},
            format="json",
        )
        self.assertEqual(response.status_code, 409)  # stops at the "in progress" guard
        self.assertEqual(InterviewSession.objects.filter(student=self.student).count(), 1)


class AnswerTests(InterviewTestBase):
    def setUp(self):
        super().setUp()
        self.session_obj = self.session(total_questions=2)
        self.question = self.add_question(self.session_obj)
        self.answer_url = f"/api/interviews/{self.session_obj.id}/answer/"

    def test_student_can_submit_a_transcript_answer(self):
        """4. Student can submit a transcript answer."""
        with mock.patch.object(interview_service, "generate_question",
                               return_value={"question": "Follow up?", "category": "technical",
                                             "source": "offline", "provider": "offline",
                                             "notice": "", "raw": {}}), \
             mock.patch.object(interview_service, "evaluate_answer",
                               return_value=dict(EVALUATION_PAYLOAD, source="ai",
                                                 provider="openai", notice="", raw={})):
            response = self.client.post(
                self.answer_url, {"answer": "I used JWT tokens in Django."}, format="json"
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["duplicate"])
        self.assertEqual(response.data["evaluation"]["score"], 7)
        self.assertEqual(response.data["evaluation"]["technical_correctness"],
                         EVALUATION_PAYLOAD["technical_correctness"])
        self.assertEqual(response.data["next_question"], "Follow up?")
        self.assertEqual(response.data["question_index"], 1)
        self.assertFalse(response.data["completed"])
        # No provider payload is exposed to the client.
        self.assertNotIn("raw", response.data["evaluation"])
        # The transcript itself is persisted.
        self.assertTrue(
            InterviewTurn.objects.filter(
                session=self.session_obj, kind=InterviewTurn.Kind.ANSWER,
                content="I used JWT tokens in Django.",
            ).exists()
        )

    def test_empty_answer_is_rejected(self):
        response = self.client.post(self.answer_url, {"answer": "   "}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_duplicate_submission_is_prevented(self):
        """5. Duplicate answer submission is prevented (idempotency token)."""
        token = "abc-1234-5678"
        payload = {"answer": "My answer about caching.", "client_token": token}
        with mock.patch.object(interview_service, "generate_question",
                               return_value={"question": "Next?", "category": "technical",
                                             "source": "offline", "provider": "offline",
                                             "notice": "", "raw": {}}), \
             mock.patch.object(interview_service, "evaluate_answer",
                               return_value=dict(EVALUATION_PAYLOAD, source="ai",
                                                 provider="openai", notice="", raw={})):
            first = self.client.post(self.answer_url, payload, format="json")
            self.assertEqual(first.status_code, 200)
            second = self.client.post(self.answer_url, payload, format="json")
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.data["duplicate"])
        # Only one answer turn and one evaluation were ever stored.
        self.assertEqual(
            InterviewTurn.objects.filter(
                session=self.session_obj, kind=InterviewTurn.Kind.ANSWER
            ).count(),
            1,
        )
        self.assertEqual(
            InterviewTurn.objects.filter(
                session=self.session_obj, kind=InterviewTurn.Kind.EVALUATION
            ).count(),
            1,
        )

    def test_duplicate_with_different_answer_does_not_create_a_turn(self):
        token = "same-token-0001"
        with mock.patch.object(interview_service, "generate_question",
                               return_value={"question": "Next?", "category": "technical",
                                             "source": "offline", "provider": "offline",
                                             "notice": "", "raw": {}}), \
             mock.patch.object(interview_service, "evaluate_answer",
                               return_value=dict(EVALUATION_PAYLOAD, source="ai",
                                                 provider="openai", notice="", raw={})):
            self.client.post(self.answer_url, {"answer": "A", "client_token": token},
                             format="json")
            again = self.client.post(
                self.answer_url, {"answer": "B", "client_token": token}, format="json"
            )
        self.assertTrue(again.data["duplicate"])
        self.assertEqual(
            InterviewTurn.objects.filter(
                session=self.session_obj, kind=InterviewTurn.Kind.ANSWER
            ).count(),
            1,
        )

    def test_malformed_client_token_is_rejected(self):
        response = self.client.post(
            self.answer_url, {"answer": "hi", "client_token": "bad token!!"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_completed_interview_cannot_accept_new_answers(self):
        """12. Completed interviews cannot accept new answers."""
        self.session_obj.status = InterviewSession.Status.COMPLETED
        self.session_obj.save()
        response = self.client.post(self.answer_url, {"answer": "late answer"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "interview_closed")

    def test_cancelled_interview_cannot_accept_new_answers(self):
        self.session_obj.status = InterviewSession.Status.CANCELLED
        self.session_obj.save()
        response = self.client.post(self.answer_url, {"answer": "nope"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_ai_failure_preserves_the_answer_and_allows_retry(self):
        """9. AI service failure does not crash the interview."""
        with mock.patch.object(
            interview_service, "evaluate_answer", side_effect=ProviderUnavailable("key rejected")
        ):
            response = self.client.post(
                self.answer_url, {"answer": "A careful answer"}, format="json"
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "evaluation_unavailable")
        # Student-safe message: no key, no URL, no exception class name.
        self.assertNotIn("key rejected", response.data["detail"])
        self.assertNotIn("ProviderUnavailable", response.data["detail"])
        # The transcript is kept so the student can retry.
        self.assertTrue(
            InterviewTurn.objects.filter(
                session=self.session_obj, kind=InterviewTurn.Kind.ANSWER,
                content="A careful answer",
            ).exists()
        )
        self.session_obj.refresh_from_db()
        self.assertEqual(self.session_obj.status, InterviewSession.Status.IN_PROGRESS)
        self.assertTrue(self.session_obj.last_error)

    def test_question_failure_keeps_the_evaluation(self):
        with mock.patch.object(interview_service, "evaluate_answer",
                               return_value=dict(EVALUATION_PAYLOAD, source="ai",
                                                 provider="openai", notice="", raw={})), \
             mock.patch.object(interview_service, "generate_question",
                               side_effect=ProviderUnavailable("down")):
            response = self.client.post(
                self.answer_url, {"answer": "Good answer"}, format="json"
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "question_unavailable")
        self.assertEqual(
            InterviewTurn.objects.filter(
                session=self.session_obj, kind=InterviewTurn.Kind.EVALUATION
            ).count(),
            1,
        )

    def test_answering_the_last_question_completes_the_interview(self):
        self.session_obj.total_questions = 1
        self.session_obj.save()
        with mock.patch.object(interview_service, "evaluate_answer",
                               return_value=dict(EVALUATION_PAYLOAD, source="ai",
                                                 provider="openai", notice="", raw={})), \
             mock.patch.object(interview_service, "build_report",
                               return_value=dict(REPORT_PAYLOAD, questions_answered=1,
                                                 score=7, per_question=[], source="ai",
                                                 provider="openai", notice="", raw={})):
            response = self.client.post(self.answer_url, {"answer": "Final answer"},
                                        format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["completed"])
        self.assertIn("report", response.data)
        self.session_obj.refresh_from_db()
        self.assertEqual(self.session_obj.status, InterviewSession.Status.COMPLETED)
        self.assertIsNotNone(self.session_obj.completed_at)


class AiServiceTests(TestCase):
    """6, 7, 8, 10. AI generation, evaluation, malformed output, no config."""

    def setUp(self):
        self.user = make_student("ai_student")

    def test_question_generation_is_mocked_and_structured(self):
        with mock.patch("apps.ai.providers.is_configured", return_value=True), \
             mock.patch("apps.ai.providers.chat_json", return_value=QUESTION_PAYLOAD) as chat:
            result = interview_service.generate_question(
                context="ctx", position="Python Developer", transcript=[], index=0, total=5
            )
        self.assertEqual(result["question"], QUESTION_PAYLOAD["question"])
        self.assertEqual(result["category"], "project")
        self.assertEqual(result["source"], "ai")
        self.assertEqual(result["raw"], QUESTION_PAYLOAD)
        # The prompt really asked the provider and carried the role.
        sent = chat.call_args[0][0]
        self.assertIn("Python Developer", sent[1]["content"])
        self.assertEqual(sent[1]["content"].count("Question 1 of 5"), 1)

    def test_question_generation_uses_the_previous_answer(self):
        """8. Adaptive generation reads the conversation so far."""
        transcript = [
            {"role": "assistant", "kind": "question", "content": "Tell me about a project."},
            {"role": "user", "kind": "answer",
             "content": "I built a Django app with JWT authentication."},
        ]
        with mock.patch("apps.ai.providers.is_configured", return_value=True), \
             mock.patch("apps.ai.providers.chat_json", return_value=QUESTION_PAYLOAD) as chat:
            interview_service.generate_question(
                context="ctx", position="Django Developer",
                transcript=transcript, index=1, total=5,
            )
        history = chat.call_args[0][0][1]["content"]
        self.assertIn("JWT authentication", history)
        self.assertIn("Question 2 of 5", history)

    def test_question_falls_back_when_ai_breaks(self):
        with mock.patch("apps.ai.providers.is_configured", return_value=True), \
             mock.patch("apps.ai.providers.chat_json", side_effect=AiParseError("bad json")):
            result = interview_service.generate_question(
                context="ctx", position="Python Developer", transcript=[], index=0, total=5
            )
        self.assertEqual(result["source"], "offline")
        self.assertTrue(result["question"])
        self.assertTrue(result["notice"])

    def test_question_falls_back_on_malformed_payload(self):
        for bad in ({"question": ""}, {"question": None}, "not a dict", {"category": "x"}):
            with mock.patch("apps.ai.providers.is_configured", return_value=True), \
                 mock.patch("apps.ai.providers.chat_json", return_value=bad):
                result = interview_service.generate_question(
                    context="ctx", position="Python Developer", transcript=[], index=0, total=5
                )
            self.assertEqual(result["source"], "offline", bad)

    def test_question_raises_when_ai_is_required(self):
        with mock.patch("apps.ai.providers.is_configured", return_value=True), \
             mock.patch("apps.ai.providers.chat_json", side_effect=ProviderUnavailable("no")), \
             mock.patch("apps.ai.interview_service.settings.AI_REQUIRED", True):
            with self.assertRaises(ProviderUnavailable):
                interview_service.generate_question(
                    context="", position="QA", transcript=[], index=0, total=3
                )

    def test_missing_ai_configuration_uses_offline(self):
        """10. Missing AI configuration is handled gracefully."""
        with mock.patch("apps.ai.providers.is_configured", return_value=False):
            question = interview_service.generate_question(
                context="", position="Python Developer", transcript=[], index=0, total=5
            )
            evaluation = interview_service.evaluate_answer(
                context="", position="Python Developer",
                question="Explain the GIL.", answer="It serialises bytecode execution in CPython.",
            )
            report = interview_service.build_report(
                context="", position="Python Developer",
                per_question=[{"question": "Explain the GIL.",
                               "answer": "It serialises bytecode.", "score": 6,
                               "feedback": "ok", "strengths": ["s"], "improvements": ["i"]}],
            )
        self.assertEqual(question["source"], "offline")
        self.assertEqual(
            question["question"], interview_service.offline_question("Python Developer", 0)
        )
        self.assertTrue(question["notice"])
        self.assertEqual(evaluation["source"], "offline")
        self.assertGreaterEqual(evaluation["score"], 1)
        self.assertLessEqual(evaluation["score"], 10)
        self.assertEqual(report["source"], "offline")
        self.assertIn("practice indicator", report["score_note"].lower())

    def test_evaluation_is_mocked_and_normalised(self):
        with mock.patch("apps.ai.providers.is_configured", return_value=True), \
             mock.patch("apps.ai.providers.chat_json", return_value=EVALUATION_PAYLOAD):
            result = interview_service.evaluate_answer(
                context="ctx", position="Django Developer",
                question="How do you handle auth?", answer="With JWT in Django.",
            )
        self.assertEqual(result["score"], 7)
        self.assertEqual(result["source"], "ai")
        self.assertEqual(result["strengths"], EVALUATION_PAYLOAD["strengths"])
        self.assertTrue(result["feedback"])
        self.assertEqual(result["raw"], EVALUATION_PAYLOAD)

    def test_evaluation_normalises_hostile_payloads(self):
        hostile = {
            "score": 999,                       # clamped
            "strengths": "one, two, two, one",  # string -> list, deduped
            "improvements": {"a": 1},           # object -> dropped safely
            "feedback": {"x": 1},               # object -> ""
        }
        with mock.patch("apps.ai.providers.is_configured", return_value=True), \
             mock.patch("apps.ai.providers.chat_json", return_value=hostile):
            result = interview_service.evaluate_answer(
                context="", position="QA", question="q", answer="a"
            )
        self.assertEqual(result["score"], 10)
        self.assertEqual(result["strengths"], ["one", "two"])
        self.assertEqual(result["improvements"], [])
        self.assertEqual(result["feedback"], "Answer reviewed.")

    def test_evaluation_falls_back_on_malformed_payload(self):
        with mock.patch("apps.ai.providers.is_configured", return_value=True), \
             mock.patch("apps.ai.providers.chat_json", return_value={"score": 5}):
            result = interview_service.evaluate_answer(
                context="", position="QA", question="q", answer="a real answer"
            )
        self.assertEqual(result["source"], "offline")

    def test_report_is_mocked_and_structured(self):
        pairs = [{"question": "Q1", "answer": "A1", "score": 8, "feedback": "good",
                  "strengths": ["s1"], "improvements": ["i1"], "category": "technical"}]
        with mock.patch("apps.ai.providers.is_configured", return_value=True), \
             mock.patch("apps.ai.providers.chat_json", return_value=REPORT_PAYLOAD):
            report = interview_service.build_report(
                context="ctx", position="Django Developer", per_question=pairs
            )
        self.assertEqual(report["source"], "ai")
        self.assertEqual(report["questions_answered"], 1)
        self.assertEqual(report["score"], 8)
        self.assertEqual(report["technical_strengths"], REPORT_PAYLOAD["technical_strengths"])
        self.assertEqual(report["per_question"][0]["question"], "Q1")
        self.assertIn("not an objective measure", report["score_note"])

    def test_report_rejects_a_hiring_probability_claim(self):
        """The prompt itself forbids it; the offline path must not produce it."""
        with mock.patch("apps.ai.providers.is_configured", return_value=False):
            report = interview_service.build_report(
                context="", position="QA",
                per_question=[{"question": "Q", "answer": "A", "score": 7,
                              "feedback": "f", "strengths": [], "improvements": []}],
            )
        blob = str(report).lower()
        self.assertNotIn("hiring probability", blob.replace("not a hiring decision", ""))
        self.assertNotIn("chance of getting", blob)
        self.assertIn("practice", report["score_note"].lower())

    def test_context_uses_profile_job_and_resume(self):
        from apps.resumes.models import Resume, ResumeAnalysis

        recruiter = User.objects.create_user(
            username="rec3", password="Str0ngPass!23", role=User.Role.RECRUITER
        )
        job = Job.objects.create(
            recruiter=recruiter, company_name="Acme", title="Backend Engineer",
            description="APIs", location="Remote",
        )
        job.required_skills.add(Skill.objects.create(name="PostgreSQL"))
        profile = StudentProfile.objects.get(user=self.user)
        profile.skills.add(Skill.objects.create(name="Python"))
        resume = Resume.objects.create(user=self.user)
        ResumeAnalysis.objects.create(
            resume=resume, status=ResumeAnalysis.Status.COMPLETED,
            skill_gaps=["Kubernetes"], strengths=["Clear project write-ups"],
        )
        context = interview_service.build_context(self.user, job=job, position="Backend Engineer")
        self.assertIn("Python", context)
        self.assertIn("PostgreSQL", context)
        self.assertIn("Kubernetes", context)
        self.assertIn("Backend Engineer", context)


class ResumeAndReportTests(InterviewTestBase):
    def setUp(self):
        super().setUp()
        self.session_obj = self.session(total_questions=2)
        self.question = self.add_question(self.session_obj)

    def test_in_progress_interview_can_be_resumed(self):
        """11. IN_PROGRESS interviews can be resumed after a reload."""
        response = self.client.get("/api/interviews/active/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.session_obj.id)
        self.assertTrue(response.data["resumed"])
        self.assertTrue(response.data["is_resumable"])
        # The current question and previous answers come back for the UI.
        self.assertEqual(response.data["current_question"]["content"], self.question.content)
        self.assertEqual(response.data["turns"][0]["content"], self.question.content)

    def test_active_returns_404_when_idle(self):
        self.session_obj.status = InterviewSession.Status.COMPLETED
        self.session_obj.save()
        self.assertEqual(self.client.get("/api/interviews/active/").status_code, 404)

    def test_resume_after_an_answer_continues_from_the_right_point(self):
        with mock.patch.object(interview_service, "evaluate_answer",
                               return_value=dict(EVALUATION_PAYLOAD, source="ai",
                                                 provider="openai", notice="", raw={})), \
             mock.patch.object(interview_service, "generate_question",
                               return_value={"question": "Second question?",
                                             "category": "behavioral", "source": "offline",
                                             "provider": "offline", "notice": "", "raw": {}}):
            self.client.post(
                f"/api/interviews/{self.session_obj.id}/answer/",
                {"answer": "My first answer"}, format="json",
            )
        response = self.client.get("/api/interviews/active/")
        self.assertEqual(response.data["question_index"], 1)
        self.assertEqual(response.data["current_question"]["content"], "Second question?")
        # One question + one answer + one evaluation + the new question.
        self.assertEqual(len(response.data["turns"]), 4)

    def test_resume_regenerates_a_missing_question(self):
        self.session_obj.turns.all().delete()
        with mock.patch.object(interview_service, "generate_question",
                               return_value={"question": "Recovered question?",
                                             "category": "general", "source": "offline",
                                             "provider": "offline", "notice": "", "raw": {}}):
            response = self.client.get("/api/interviews/active/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_question"]["content"], "Recovered question?")

    def test_start_with_resume_returns_the_open_session(self):
        response = self.client.post(
            self.url, {"position": "Different Role", "resume": True}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.session_obj.id)
        self.assertTrue(response.data["resumed"])
        self.assertEqual(response.data["position"], "Python Developer")

    def test_report_is_generated_and_shaped_correctly(self):
        """13. Interview report is generated correctly."""
        self.session_obj.total_questions = 1
        self.session_obj.save()
        with mock.patch.object(interview_service, "evaluate_answer",
                               return_value=dict(EVALUATION_PAYLOAD, source="ai",
                                                 provider="openai", notice="", raw={})):
            self.client.post(
                f"/api/interviews/{self.session_obj.id}/answer/",
                {"answer": "A thorough answer"}, format="json",
            )
        with mock.patch("apps.ai.providers.is_configured", return_value=True), \
             mock.patch("apps.ai.providers.chat_json", return_value=REPORT_PAYLOAD):
            report = self.client.get(f"/api/interviews/{self.session_obj.id}/report/")
        self.assertEqual(report.status_code, 200, report.data)
        for key in ("summary", "questions_answered", "technical_strengths",
                    "areas_to_improve", "topics_to_prepare", "per_question", "score_note"):
            self.assertIn(key, report.data)
        entry = report.data["per_question"][0]
        for key in ("question", "answer", "score", "feedback", "strengths", "improvements"):
            self.assertIn(key, entry)
        self.assertEqual(entry["answer"], "A thorough answer")
        self.assertEqual(entry["score"], 7)
        self.assertIn("practice", report.data["score_note"].lower())

    def test_report_is_pending_while_the_interview_runs(self):
        response = self.client.get(f"/api/interviews/{self.session_obj.id}/report/")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "report_pending")

    def test_complete_endpoint_ends_the_interview_early(self):
        with mock.patch.object(interview_service, "build_report",
                               return_value=dict(REPORT_PAYLOAD, questions_answered=0,
                                                 score=None, per_question=[],
                                                 source="offline", provider="offline",
                                                 notice="", raw={})):
            response = self.client.post(
                f"/api/interviews/{self.session_obj.id}/complete/", {}, format="json"
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["completed"])
        self.session_obj.refresh_from_db()
        self.assertEqual(self.session_obj.status, InterviewSession.Status.COMPLETED)
        self.assertEqual(self.session_obj.state, InterviewSession.State.COMPLETED)
        self.assertIsNotNone(self.session_obj.completed_at)

    def test_report_failure_returns_a_safe_message(self):
        with mock.patch.object(interview_service, "build_report",
                               side_effect=ProviderUnavailable("sk-secret-leak")):
            response = self.client.post(
                f"/api/interviews/{self.session_obj.id}/complete/", {}, format="json"
            )
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("sk-secret-leak", response.data["detail"])

    def test_cancel_frees_the_slot_for_a_new_interview(self):
        response = self.client.post(
            f"/api/interviews/{self.session_obj.id}/cancel/", {}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.session_obj.refresh_from_db()
        self.assertEqual(self.session_obj.status, InterviewSession.Status.CANCELLED)
        # A new interview can now start.
        self.assertEqual(self.start()["status"], InterviewSession.Status.IN_PROGRESS)

    def test_no_response_ever_contains_a_configured_api_key(self):
        """16. API keys are never sent to the frontend."""
        secret = "sk-test-do-not-leak-1234567890"
        # this class already has an in-progress session, so start returns it
        start = self.client.post(
            self.url, {"position": "QA", "resume": True}, format="json"
        )
        self.assertEqual(start.status_code, 200, start.data)
        with mock.patch("apps.ai.providers.is_configured", return_value=True), \
             mock.patch("apps.ai.providers.provider_name", return_value="openai"), \
             mock.patch("apps.ai.providers.chat_json", return_value=QUESTION_PAYLOAD):
            detail = self.client.get(f"/api/interviews/{self.session_obj.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn(secret, str(start.data))
        self.assertNotIn(secret, str(detail.data))
        # The provider is reported as a safe label, never a key or endpoint URL.
        self.assertNotIn("http", str(detail.data).lower())

    def test_timestamps_are_recorded(self):
        self.assertIsNotNone(self.session_obj.created_at)
        self.assertIsNotNone(self.session_obj.updated_at)
        self.assertIsNone(self.session_obj.completed_at)
        self.assertLess(self.session_obj.created_at, timezone.now())



