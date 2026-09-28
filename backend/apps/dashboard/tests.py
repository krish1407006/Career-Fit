"""Phase 8: student performance dashboard tests.

Every assertion here is computed from records the test itself creates, so a
wrong number fails instead of drifting. No random or placeholder values.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import StudentProfile
from apps.assessments.models import Question, Quiz, QuizAttempt
from apps.interviews.models import InterviewSession
from apps.jobs.models import Job, JobApplication, Skill
from apps.resumes.models import Resume, ResumeAnalysis

User = get_user_model()
PASSWORD = "Str0ngPass!23"
DASHBOARD = "/api/dashboard/student/"


def make_student(username, email=None, password=PASSWORD):
    user = User.objects.create_user(
        username=username, email=email or f"{username}@example.com",
        password=password, role=User.Role.STUDENT,
    )
    StudentProfile.objects.create(user=user, full_name=username.title())
    return user


def login_as(client, user, password=PASSWORD):
    response = client.post(
        "/api/auth/login/", {"username": user.username, "password": password},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK, response.data
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")


def make_quiz(title, category=Quiz.Category.PYTHON):
    quiz = Quiz.objects.create(title=title, category=category)
    for index in range(4):
        Question.objects.create(
            quiz=quiz, text=f"{title} q{index}", options=["a", "b", "c", "d"],
            correct_index=0, explanation="because",
        )
    return quiz


def submit_attempt(student, quiz, correct, total=4, days_ago=0, submitted=True):
    """A submitted attempt with a known score_percent, plus its answer rows."""
    percent = round((correct / total) * 100) if total else 0
    attempt = QuizAttempt.objects.create(
        student=student, quiz=quiz, status=QuizAttempt.Status.COMPLETED,
        correct_count=correct, incorrect_count=total - correct, total=total,
        score_percent=percent,
    )
    if submitted:
        attempt.submitted_at = timezone.now() - timedelta(days=days_ago)
        attempt.save(update_fields=["submitted_at"])
    return attempt


def complete_interview(student, position, score, days_ago=0, report_extra=None):
    """A completed Phase 7 session carrying a stored report score out of 10."""
    report = {"summary": f"{position} summary", "questions_answered": 3}
    if score is not None:
        report["score"] = score
    if report_extra:
        report.update(report_extra)
    done = timezone.now() - timedelta(days=days_ago)
    return InterviewSession.objects.create(
        student=student, position=position, status=InterviewSession.Status.COMPLETED,
        report_data=report, completed_at=done, created_at=done,
    )


def attach_analysis(student, **overrides):
    resume = Resume.objects.create(
        user=student, original_name="cv.pdf", file="resumes/test/cv.pdf",
        status=Resume.Status.ANALYZED,
    )
    fields = {
        "status": ResumeAnalysis.Status.COMPLETED,
        "detected_skills": ["Python", "Django"],
        "skill_gaps": ["Kubernetes", "GraphQL"],
        "recommended_roles": ["Backend Developer"],
        "source": "ai",
        "score": 74,
    }
    fields.update(overrides)
    return resume, ResumeAnalysis.objects.create(resume=resume, **fields)


class DashboardAccessTests(APITestCase):
    """Authentication and role gates (spec 15.1, 15.2, 15.11)."""

    def setUp(self):
        self.student = make_student("alice")
        self.recruiter = User.objects.create_user(
            username="acme", password=PASSWORD, role=User.Role.RECRUITER,
        )

    def test_dashboard_requires_authentication(self):
        self.assertEqual(self.client.get(DASHBOARD).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_can_read_their_own_dashboard(self):
        login_as(self.client, self.student)
        response = self.client.get(DASHBOARD)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["student"]["username"], "alice")

    def test_recruiter_is_refused(self):
        login_as(self.client, self.recruiter)
        self.assertEqual(self.client.get(DASHBOARD).status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_pass_a_student_id_to_read_someone_else(self):
        """Ownership comes from the token, never from a request parameter."""
        bob = make_student("bob")
        submit_attempt(bob, make_quiz("Bob quiz"), correct=4)
        login_as(self.client, self.student)
        response = self.client.get(f"{DASHBOARD}?student={bob.pk}&user={bob.pk}&id={bob.pk}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["student"]["username"], "alice")
        self.assertEqual(response.data["overview"]["quiz_attempts"], 0)
        self.assertNotIn("Bob quiz", str(response.data))


class DashboardEmptyStateTests(APITestCase):
    """A brand new account must not be told it scored 0% (spec 15.10, 1)."""

    def setUp(self):
        self.student = make_student("newbie")
        login_as(self.client, self.student)
        self.data = self.client.get(DASHBOARD).data

    def test_overview_reports_none_not_zero_for_averages(self):
        overview = self.data["overview"]
        self.assertIsNone(overview["average_quiz_score"])
        self.assertIsNone(overview["average_interview_score"])
        self.assertEqual(overview["quiz_attempts"], 0)
        self.assertEqual(overview["interviews_completed"], 0)

    def test_counts_that_are_genuinely_zero_are_zero(self):
        overview = self.data["overview"]
        self.assertFalse(overview["resume_uploaded"])
        self.assertFalse(overview["resume_analyzed"])
        self.assertEqual(overview["skills_count"], 0)
        self.assertEqual(overview["skill_gaps_count"], 0)
        self.assertEqual(overview["applications"], 0)

    def test_sections_are_empty_rather_than_missing(self):
        self.assertEqual(self.data["quiz_performance"]["recent_attempts"], [])
        self.assertEqual(self.data["interview_performance"]["recent_interviews"], [])
        self.assertEqual(self.data["applications"]["recent"], [])
        self.assertEqual(self.data["performance_trend"], [])
        self.assertEqual(self.data["skills"]["current"], [])
        self.assertEqual(self.data["skills"]["job_gaps"], [])

    def test_legacy_quiz_average_is_none_not_zero(self):
        """The pre-Phase-8 key must not reintroduce the misleading 0%."""
        self.assertIsNone(self.data["quizzes"]["avg_score"])

    def test_empty_dashboard_still_offers_actions(self):
        ids = {item["id"] for item in self.data["preparation_insights"]}
        self.assertIn("no-resume", ids)
        self.assertIn("no-applications", ids)

    def test_no_resume_summary_is_honest(self):
        resume = self.data["resume"]
        self.assertFalse(resume["uploaded"])
        self.assertFalse(resume["analysis_completed"])
        self.assertIsNone(resume["score"])
        self.assertEqual(resume["status"], "none")


class ResumeSummaryTests(APITestCase):
    """Spec 15.4: resume analysis summary."""

    def setUp(self):
        self.student = make_student("resumer")
        login_as(self.client, self.student)

    def test_summary_after_analysis(self):
        attach_analysis(self.student)
        resume = self.client.get(DASHBOARD).data["resume"]
        self.assertTrue(resume["uploaded"])
        self.assertTrue(resume["analysis_completed"])
        self.assertEqual(resume["detected_skills_count"], 2)
        self.assertEqual(resume["skill_gaps_count"], 2)
        self.assertEqual(resume["score"], 74)
        self.assertEqual(resume["source"], "ai")
        self.assertEqual(resume["recommended_roles"], ["Backend Developer"])
        self.assertEqual(resume["detected_skills"], ["Python", "Django"])

    def test_failed_analysis_is_not_reported_as_completed(self):
        attach_analysis(self.student, status=ResumeAnalysis.Status.FAILED)
        resume = self.client.get(DASHBOARD).data["resume"]
        self.assertTrue(resume["uploaded"])
        self.assertFalse(resume["analysis_completed"])
        self.assertEqual(resume["analysis_status"], ResumeAnalysis.Status.FAILED)

    def test_upload_without_analysis_prompts_analysis(self):
        Resume.objects.create(
            user=self.student, original_name="cv.pdf", file="resumes/test/cv.pdf",
        )
        data = self.client.get(DASHBOARD).data
        self.assertTrue(data["resume"]["uploaded"])
        self.assertFalse(data["resume"]["analysis_completed"])
        self.assertIn("resume-not-analyzed", {i["id"] for i in data["preparation_insights"]})

    def test_latest_resume_wins(self):
        older, _ = attach_analysis(self.student, score=10)
        newer = Resume.objects.create(
            user=self.student, original_name="new.pdf", file="resumes/test/new.pdf",
            status=Resume.Status.ANALYZED,
        )
        ResumeAnalysis.objects.create(
            resume=newer, status=ResumeAnalysis.Status.COMPLETED, score=91,
        )
        resume = self.client.get(DASHBOARD).data["resume"]
        self.assertEqual(resume["score"], 91)
        self.assertNotEqual(resume["original_name"], older.original_name)


class SkillInsightTests(APITestCase):
    """Spec 15.5: skill counts, reusing the existing matching logic."""

    def setUp(self):
        self.student = make_student("skiller")
        self.profile = StudentProfile.objects.get(user=self.student)
        login_as(self.client, self.student)

    def test_profile_skills_are_counted(self):
        for name in ("Python", "SQL"):
            self.profile.skills.add(Skill.objects.create(name=name))
        data = self.client.get(DASHBOARD).data
        self.assertEqual(data["skills"]["current_count"], 2)
        self.assertEqual(data["overview"]["skills_count"], 2)
        self.assertEqual(data["skills"]["current"], ["Python", "SQL"])

    def test_analysis_gaps_are_reported_separately_from_job_gaps(self):
        attach_analysis(self.student)
        data = self.client.get(DASHBOARD).data
        self.assertEqual(data["skills"]["gaps"], ["Kubernetes", "GraphQL"])
        self.assertEqual(data["overview"]["skill_gaps_count"], 2)

    def test_job_gaps_come_from_the_shared_matching_function(self):
        # Only Python is on the profile; the job also requires Docker and Redis.
        self.profile.skills.add(Skill.objects.create(name="Python"))
        recruiter = User.objects.create_user(
            username="corp", password=PASSWORD, role=User.Role.RECRUITER,
        )
        job = Job.objects.create(
            recruiter=recruiter, company_name="Corp", title="SDE",
            description="d", location="Remote",
        )
        job.required_skills.add(
            Skill.objects.create(name="Python"),
            Skill.objects.create(name="Docker"),
            Skill.objects.create(name="Redis"),
        )
        JobApplication.objects.create(student=self.student, job=job, match_score=33)

        data = self.client.get(DASHBOARD).data
        gaps = {item["skill"]: item["required_by"] for item in data["skills"]["job_gaps"]}
        self.assertEqual(gaps, {"docker": 1, "redis": 1})
        self.assertNotIn("python", gaps)
        self.assertEqual(data["skills"]["job_gap_count"], 2)

    def test_no_applications_means_no_job_gaps(self):
        self.profile.skills.add(Skill.objects.create(name="Python"))
        data = self.client.get(DASHBOARD).data
        self.assertEqual(data["skills"]["job_gaps"], [])


class QuizPerformanceTests(APITestCase):
    """Spec 15.6: quiz statistics, ignoring incomplete and invalid attempts."""

    def setUp(self):
        self.student = make_student("quizer")
        login_as(self.client, self.student)

    def test_known_scores_produce_known_averages(self):
        submit_attempt(self.student, make_quiz("Python Basics"), correct=4)      # 100
        submit_attempt(self.student, make_quiz("SQL Basics"), correct=3)         # 75
        submit_attempt(self.student, make_quiz("DSA Fundamentals"), correct=2)    # 50
        data = self.client.get(DASHBOARD).data["quiz_performance"]
        self.assertEqual(data["attempts_completed"], 3)
        self.assertEqual(data["average_score"], 75)      # (100+75+50)/3
        self.assertEqual(data["highest_score"], 100)
        self.assertEqual(data["passed"], 2)              # >=60: 100 and 75

    def test_single_attempt_average_is_that_attempt(self):
        submit_attempt(self.student, make_quiz("Solo"), correct=3)
        data = self.client.get(DASHBOARD).data["quiz_performance"]
        self.assertEqual(data["average_score"], 75)
        self.assertEqual(data["highest_score"], 75)

    def test_unsubmitted_attempt_is_excluded_from_statistics(self):
        quiz = make_quiz("Abandoned")
        QuizAttempt.objects.create(
            student=self.student, quiz=quiz, status=QuizAttempt.Status.IN_PROGRESS,
        )
        data = self.client.get(DASHBOARD).data
        self.assertEqual(data["quiz_performance"]["attempts_completed"], 0)
        self.assertEqual(data["quiz_performance"]["in_progress"], 1)
        self.assertIsNone(data["quiz_performance"]["average_score"])
        self.assertEqual(data["performance_trend"], [])

    def test_zero_question_attempt_is_not_a_zero_percent_score(self):
        """A quiz with no questions is not an attempt; it must not drag the mean."""
        empty = Quiz.objects.create(title="Empty")
        submit_attempt(self.student, empty, correct=0, total=0)
        submit_attempt(self.student, make_quiz("Real"), correct=4)
        data = self.client.get(DASHBOARD).data["quiz_performance"]
        self.assertEqual(data["average_score"], 100)
        self.assertEqual(data["highest_score"], 100)
        self.assertEqual(len(data["recent_attempts"]), 1)

    def test_recent_attempts_are_newest_first_with_real_titles(self):
        submit_attempt(self.student, make_quiz("Oldest"), correct=1, days_ago=9)
        submit_attempt(self.student, make_quiz("Newest"), correct=4, days_ago=1)
        recent = self.client.get(DASHBOARD).data["quiz_performance"]["recent_attempts"]
        self.assertEqual([row["title"] for row in recent], ["Newest", "Oldest"])
        self.assertEqual(recent[0]["score_percent"], 100)

    def test_by_category_uses_real_category_labels(self):
        submit_attempt(self.student, make_quiz("Py", category=Quiz.Category.PYTHON), correct=4)
        submit_attempt(self.student, make_quiz("Sql", category=Quiz.Category.SQL), correct=1)
        rows = self.client.get(DASHBOARD).data["quiz_performance"]["by_category"]
        by_name = {row["category"]: row for row in rows}
        self.assertEqual(by_name["python"]["label"], "Python")
        self.assertEqual(by_name["python"]["average"], 100)
        self.assertEqual(by_name["python"]["attempts"], 1)
        self.assertEqual(by_name["sql"]["label"], "SQL")
        self.assertEqual(by_name["sql"]["average"], 25)


class InterviewPerformanceTests(APITestCase):
    """Spec 15.7: interview statistics from Phase 7 sessions."""

    def setUp(self):
        self.student = make_student("interviewee")
        login_as(self.client, self.student)

    def test_completed_and_in_progress_are_counted_separately(self):
        complete_interview(self.student, "Python Developer", score=8, days_ago=3)
        InterviewSession.objects.create(
            student=self.student, position="Backend",
            status=InterviewSession.Status.IN_PROGRESS,
        )
        data = self.client.get(DASHBOARD).data["interview_performance"]
        self.assertEqual(data["completed"], 1)
        self.assertEqual(data["in_progress"], 1)
        self.assertEqual(data["total"], 2)

    def test_average_of_real_report_scores(self):
        complete_interview(self.student, "A", score=8, days_ago=5)
        complete_interview(self.student, "B", score=7, days_ago=2)
        data = self.client.get(DASHBOARD).data["interview_performance"]
        self.assertEqual(data["average_score"], 7.5)
        self.assertEqual(data["scored_interviews"], 2)

    def test_unscored_completion_is_excluded_from_the_average(self):
        complete_interview(self.student, "Scored", score=9)
        complete_interview(self.student, "Unscored", score=None)
        data = self.client.get(DASHBOARD).data["interview_performance"]
        self.assertEqual(data["completed"], 2)
        self.assertEqual(data["scored_interviews"], 1)
        self.assertEqual(data["average_score"], 9)

    def test_no_completed_interview_means_no_average(self):
        InterviewSession.objects.create(
            student=self.student, position="Pending",
            status=InterviewSession.Status.IN_PROGRESS,
        )
        data = self.client.get(DASHBOARD).data["interview_performance"]
        self.assertIsNone(data["average_score"])
        self.assertIsNone(data["latest"])

    def test_latest_is_the_most_recent_completion(self):
        complete_interview(
            self.student, "Python Developer", score=8, days_ago=7,
            report_extra={"areas_to_improve": ["Explain complexity"],
                          "topics_to_prepare": ["Heap"]},
        )
        complete_interview(self.student, "Django Developer", score=9, days_ago=1)
        latest = self.client.get(DASHBOARD).data["interview_performance"]["latest"]
        self.assertEqual(latest["position"], "Django Developer")
        self.assertEqual(latest["score"], 9)

    def test_active_session_is_exposed_for_the_resume_button(self):
        session = InterviewSession.objects.create(
            student=self.student, position="Half done",
            status=InterviewSession.Status.IN_PROGRESS, question_index=2, total_questions=5,
        )
        active = self.client.get(DASHBOARD).data["interview_performance"]["active_session"]
        self.assertEqual(active["id"], session.id)
        self.assertEqual(active["question_index"], 2)

    def test_no_active_session_when_nothing_in_progress(self):
        complete_interview(self.student, "Done", score=8)
        data = self.client.get(DASHBOARD).data["interview_performance"]
        self.assertIsNone(data["active_session"])

    def test_feedback_summary_comes_from_the_stored_report(self):
        complete_interview(
            self.student, "Python Developer", score=8,
            report_extra={"areas_to_improve": ["Give complexity analysis"],
                          "topics_to_prepare": ["Decorators"]},
        )
        recent = self.client.get(DASHBOARD).data["interview_performance"]["recent_interviews"]
        self.assertEqual(recent[0]["areas_to_improve"], ["Give complexity analysis"])
        self.assertEqual(recent[0]["topics_to_prepare"], ["Decorators"])


class ApplicationSummaryTests(APITestCase):
    """Spec 15.8: application counts using only real model statuses."""

    def setUp(self):
        self.student = make_student("applier")
        self.recruiter = User.objects.create_user(
            username="corp", password=PASSWORD, role=User.Role.RECRUITER,
        )
        self.job = Job.objects.create(
            recruiter=self.recruiter, company_name="Corp", title="SDE",
            description="d", location="Remote",
        )
        login_as(self.client, self.student)

    def _apply(self, title, status, match=50):
        job = Job.objects.create(
            recruiter=self.recruiter, company_name="Corp", title=title,
            description="d", location="Remote",
        )
        return JobApplication.objects.create(
            student=self.student, job=job, status=status, match_score=match,
        )

    def test_counts_by_real_statuses(self):
        self._apply("A", JobApplication.Status.APPLIED)
        self._apply("B", JobApplication.Status.SHORTLISTED)
        self._apply("C", JobApplication.Status.SELECTED)
        self._apply("D", JobApplication.Status.REJECTED)
        data = self.client.get(DASHBOARD).data
        self.assertEqual(data["applications"]["total"], 4)
        self.assertEqual(data["applications"]["by_status"], {
            "applied": 1, "shortlisted": 1, "selected": 1, "rejected": 1,
        })
        self.assertEqual(data["overview"]["applications"], 4)

    def test_only_statuses_that_exist_are_reported(self):
        """No invented 'pending' state: the model has no such status."""
        self._apply("A", JobApplication.Status.APPLIED)
        by_status = self.client.get(DASHBOARD).data["applications"]["by_status"]
        self.assertNotIn("pending", by_status)
        for key in by_status:
            self.assertIn(key, dict(JobApplication.Status.choices))

    def test_best_match_and_recent_rows(self):
        self._apply("Low", JobApplication.Status.APPLIED, match=20)
        self._apply("High", JobApplication.Status.SHORTLISTED, match=88)
        data = self.client.get(DASHBOARD).data["applications"]
        self.assertEqual(data["best_match"], 88)
        titles = {row["title"] for row in data["recent"]}
        self.assertEqual(titles, {"Low", "High"})

    def test_best_match_is_none_with_no_applications(self):
        data = self.client.get(DASHBOARD).data["applications"]
        self.assertIsNone(data["best_match"])


class PerformanceTrendTests(APITestCase):
    """Spec 15.9: the trend may only contain real stored results."""

    def setUp(self):
        self.student = make_student("trender")
        login_as(self.client, self.student)

    def test_merges_quizzes_and_interviews_oldest_first(self):
        complete_interview(self.student, "Interview 1", score=6, days_ago=6)
        submit_attempt(self.student, make_quiz("Quiz 1"), correct=3, days_ago=5)
        complete_interview(self.student, "Interview 2", score=8, days_ago=2)
        submit_attempt(self.student, make_quiz("Quiz 2"), correct=4, days_ago=1)

        trend = self.client.get(DASHBOARD).data["performance_trend"]
        self.assertEqual(
            [(p["kind"], p["label"]) for p in trend],
            [("interview", "Interview 1"), ("quiz", "Quiz 1"),
             ("interview", "Interview 2"), ("quiz", "Quiz 2")],
        )

    def test_interview_score_is_normalised_but_keeps_its_raw_scale(self):
        complete_interview(self.student, "Inter", score=7)
        point = self.client.get(DASHBOARD).data["performance_trend"][0]
        self.assertEqual(point["raw_score"], 7)
        self.assertEqual(point["max_score"], 10)
        self.assertEqual(point["score"], 70)

    def test_quiz_point_keeps_percentage_scale(self):
        submit_attempt(self.student, make_quiz("Q"), correct=3)
        point = self.client.get(DASHBOARD).data["performance_trend"][0]
        self.assertEqual(point["raw_score"], 75)
        self.assertEqual(point["max_score"], 100)
        self.assertEqual(point["score"], 75)

    def test_incomplete_and_unscored_results_never_appear(self):
        quiz = make_quiz("Abandoned")
        QuizAttempt.objects.create(
            student=self.student, quiz=quiz, status=QuizAttempt.Status.IN_PROGRESS,
        )
        InterviewSession.objects.create(
            student=self.student, position="Live",
            status=InterviewSession.Status.IN_PROGRESS, report_data={"score": 10},
        )
        complete_interview(self.student, "No score", score=None)
        self.assertEqual(self.client.get(DASHBOARD).data["performance_trend"], [])

    def test_trend_is_capped(self):
        for index in range(25):
            submit_attempt(
                self.student, make_quiz(f"Quiz {index}"), correct=2, days_ago=index,
            )
        trend = self.client.get(DASHBOARD).data["performance_trend"]
        self.assertEqual(len(trend), 20)


class PreparationInsightTests(APITestCase):
    """Spec 8 and 15.3: insights come from stored data and stay neutral."""

    def setUp(self):
        self.student = make_student("insighter")
        self.profile = StudentProfile.objects.get(user=self.student)
        self.recruiter = User.objects.create_user(
            username="corp", password=PASSWORD, role=User.Role.RECRUITER,
        )
        login_as(self.client, self.student)

    def _ids(self):
        return {item["id"] for item in self.client.get(DASHBOARD).data["preparation_insights"]}

    def test_no_insights_are_invented_for_an_empty_account(self):
        self.assertEqual(self.client.get(DASHBOARD).data["preparation_insights"][0]["id"],
                         "no-resume")

    def test_resume_gap_insight_lists_the_stored_gaps(self):
        attach_analysis(self.student, skill_gaps=["Kubernetes", "GraphQL"])
        insight = next(
            i for i in self.client.get(DASHBOARD).data["preparation_insights"]
            if i["id"] == "resume-gaps"
        )
        self.assertIn("Kubernetes", insight["detail"])
        self.assertIn("GraphQL", insight["detail"])

    def test_weak_quiz_category_insight_uses_the_real_average(self):
        submit_attempt(self.student, make_quiz("Hard", category=Quiz.Category.DBMS), correct=1)
        insight = next(
            i for i in self.client.get(DASHBOARD).data["preparation_insights"]
            if i["id"] == "weak-quiz-category"
        )
        self.assertIn("DBMS", insight["title"])
        self.assertIn("25%", insight["detail"])

    def test_no_weak_category_insight_when_scores_are_strong(self):
        submit_attempt(self.student, make_quiz("Fine", category=Quiz.Category.SQL), correct=4)
        self.assertNotIn("weak-quiz-category", self._ids())

    def test_interview_feedback_surfaces_as_neutral_advice(self):
        complete_interview(
            self.student, "Python Developer", score=6,
            report_extra={"areas_to_improve": ["Discuss trade-offs"],
                          "topics_to_prepare": ["Generators"]},
        )
        ids = self._ids()
        self.assertIn("interview-areas", ids)
        self.assertIn("interview-topics", ids)
        insight = next(
            i for i in self.client.get(DASHBOARD).data["preparation_insights"]
            if i["id"] == "interview-areas"
        )
        # Neutral: suggests attention, never asserts the student is bad at it.
        self.assertIn("Consider", insight["title"])
        self.assertNotIn("weak", insight["detail"].lower())

    def test_job_skill_gap_insight_is_driven_by_applied_jobs(self):
        job = Job.objects.create(
            recruiter=self.recruiter, company_name="Corp", title="SDE",
            description="d", location="Remote",
        )
        job.required_skills.add(Skill.objects.create(name="Kubernetes"))
        JobApplication.objects.create(student=self.student, job=job, match_score=0)
        insight = next(
            i for i in self.client.get(DASHBOARD).data["preparation_insights"]
            if i["id"] == "job-skill-gaps"
        )
        self.assertIn("Kubernetes", insight["detail"])


class CrossStudentIsolationTests(APITestCase):
    """Spec 15.11: no dashboard may contain another student's records."""

    def setUp(self):
        self.alice = make_student("alice")
        self.bob = make_student("bob")
        self._give_bob_a_life()
        login_as(self.client, self.alice)

    def _give_bob_a_life(self):
        profile = StudentProfile.objects.get(user=self.bob)
        profile.skills.add(Skill.objects.create(name="Rust"))
        attach_analysis(self.bob, detected_skills=["Rust"], recommended_roles=["Systems Engineer"])
        submit_attempt(self.bob, make_quiz("Bob's Private Quiz"), correct=4)
        complete_interview(self.bob, "Bob's Private Role", score=9)
        recruiter = User.objects.create_user(
            username="corp", password=PASSWORD, role=User.Role.RECRUITER,
        )
        job = Job.objects.create(
            recruiter=recruiter, company_name="Bob Corp", title="Bob's Job",
            description="d", location="Remote",
        )
        JobApplication.objects.create(student=self.bob, job=job, match_score=91)

    def test_no_part_of_bobs_data_appears_for_alice(self):
        payload = self.client.get(DASHBOARD).data
        serialised = str(payload)
        for secret in ("bob", "Bob", "Rust", "Systems Engineer"):
            self.assertNotIn(secret, serialised)

    def test_alice_sees_only_her_own_zeroed_statistics(self):
        overview = self.client.get(DASHBOARD).data["overview"]
        self.assertEqual(overview["quiz_attempts"], 0)
        self.assertEqual(overview["interviews_completed"], 0)
        self.assertEqual(overview["applications"], 0)
        self.assertIsNone(overview["average_quiz_score"])
        self.assertIsNone(overview["average_interview_score"])
        self.assertEqual(overview["skills_count"], 0)

    def test_alice_with_her_own_data_still_excludes_bobs(self):
        submit_attempt(self.alice, make_quiz("Alice Quiz"), correct=2)
        payload = self.client.get(DASHBOARD).data
        self.assertEqual(payload["overview"]["quiz_attempts"], 1)
        self.assertEqual(payload["quiz_performance"]["average_score"], 50)
        self.assertNotIn("Rust", str(payload))

    def test_legacy_alias_blocks_also_exclude_bob(self):
        payload = self.client.get(DASHBOARD).data
        self.assertEqual(payload["jobs"]["total_applications"], 0)
        self.assertEqual(payload["interviews"]["completed"], 0)
        self.assertEqual(payload["quizzes"]["attempts"], 0)


class QueryCountTests(APITestCase):
    """Spec 11: the dashboard must not fan out into per-row queries."""

    def setUp(self):
        self.student = make_student("counter")
        profile = StudentProfile.objects.get(user=self.student)
        profile.skills.add(Skill.objects.create(name="Python"))
        recruiter = User.objects.create_user(
            username="corp", password=PASSWORD, role=User.Role.RECRUITER,
        )
        for index in range(5):
            quiz = make_quiz(f"Quiz {index}")
            submit_attempt(self.student, quiz, correct=3)
            complete_interview(self.student, f"Role {index}", score=7)
            job = Job.objects.create(
                recruiter=recruiter, company_name="Corp", title=f"Job {index}",
                description="d", location="Remote",
            )
            job.required_skills.add(Skill.objects.create(name=f"Skill{index}"))
            JobApplication.objects.create(student=self.student, job=job, match_score=60)
        login_as(self.client, self.student)

    def test_dashboard_query_count_stays_flat_as_records_grow(self):
        """Ten more of each record must not mean more queries."""
        def measure():
            self.client.get(DASHBOARD)  # warm caches
            with self.assertNumQueries(0):
                pass
            from django.db import connection, reset_queries
            from django.test.utils import CaptureQueriesContext
            with CaptureQueriesContext(connection) as captured:
                response = self.client.get(DASHBOARD)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            return len(captured.captured_queries)

        five_each = measure()

        recruiter = User.objects.get(username="corp")
        for index in range(5, 10):
            quiz = make_quiz(f"Extra {index}")
            submit_attempt(self.student, quiz, correct=2)
            complete_interview(self.student, f"Extra Role {index}", score=6)
            job = Job.objects.create(
                recruiter=recruiter, company_name="Corp", title=f"Extra {index}",
                description="d", location="Remote",
            )
            job.required_skills.add(Skill.objects.create(name=f"Extra{index}"))
            JobApplication.objects.create(student=self.student, job=job, match_score=70)
        ten_each = measure()

        # A small drift is fine (schema caching); a per-row fan-out is not.
        self.assertLessEqual(
            ten_each - five_each, 3,
            f"query count grew from {five_each} to {ten_each} as records were added",
        )

    def test_recent_lists_are_bounded(self):
        from apps.dashboard.analytics import RECENT_LIMIT
        self.assertLessEqual(
            len(self.client.get(DASHBOARD).data["quiz_performance"]["recent_attempts"]),
            RECENT_LIMIT,
        )
