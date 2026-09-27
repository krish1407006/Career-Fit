from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import RecruiterProfile, StudentProfile, SuperAdminEmail

User = get_user_model()

STUDENT_PAYLOAD = {
    "username": "jane_student",
    "email": "jane@example.com",
    "password": "Str0ngPass!23",
    "first_name": "Jane",
    "last_name": "Doe",
    "role": "student",
}

RECRUITER_PAYLOAD = {
    "username": "acme_hiring",
    "email": "hiring@acme.com",
    "password": "Str0ngPass!23",
    "first_name": "Acme",
    "last_name": "Hiring",
    "role": "recruiter",
}

ADMIN_PAYLOAD = {
    "username": "root_admin",
    "email": "root@example.com",
    "password": "Str0ngPass!23",
    "first_name": "Root",
    "last_name": "Admin",
    "role": "admin",
}


class AuthAPITestCase(APITestCase):
    """Shared helpers: register, login, and token/role accessors."""

    def register(self, payload):
        return self.client.post("/api/auth/register/", payload, format="json")

    def login(self, username, password):
        return self.client.post(
            "/api/auth/login/", {"username": username, "password": password}, format="json"
        )

    def login_tokens(self, username, password):
        response = self.login(username, password)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data

    def authenticate(self, access):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    @staticmethod
    def make_student(payload=None):
        payload = dict(STUDENT_PAYLOAD if payload is None else payload)
        user = User.objects.create_user(**payload)
        StudentProfile.objects.create(
            user=user, full_name=f"{user.first_name} {user.last_name}".strip()
        )
        return user

    @staticmethod
    def make_recruiter(payload=None):
        payload = dict(RECRUITER_PAYLOAD if payload is None else payload)
        user = User.objects.create_user(**payload)
        RecruiterProfile.objects.create(user=user, company_name=user.username)
        return user

    @staticmethod
    def make_admin(payload=None):
        payload = dict(ADMIN_PAYLOAD if payload is None else payload)
        return User.objects.create_user(**payload)


class RegistrationTests(AuthAPITestCase):
    """(1) + (2) Student and recruiter can register."""

    def test_student_can_register(self):
        response = self.register(STUDENT_PAYLOAD)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        user = User.objects.get(username=STUDENT_PAYLOAD["username"])
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertTrue(user.is_student)
        self.assertFalse(user.is_recruiter)
        self.assertFalse(user.is_admin_role)
        self.assertTrue(hasattr(user, "student_profile"))
        self.assertFalse(hasattr(user, "recruiter_profile"))

    def test_recruiter_can_register(self):
        response = self.register(RECRUITER_PAYLOAD)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        user = User.objects.get(username=RECRUITER_PAYLOAD["username"])
        self.assertEqual(user.role, User.Role.RECRUITER)
        self.assertTrue(user.is_recruiter)
        self.assertFalse(user.is_student)
        self.assertTrue(hasattr(user, "recruiter_profile"))
        self.assertFalse(hasattr(user, "student_profile"))

    def test_duplicate_username_rejected(self):
        self.register(STUDENT_PAYLOAD)
        self.client.credentials()
        response = self.register({**STUDENT_PAYLOAD, "email": "other@example.com"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_password_is_hashed_not_stored_in_plaintext(self):
        self.register(STUDENT_PAYLOAD)
        user = User.objects.get(username=STUDENT_PAYLOAD["username"])
        self.assertNotEqual(user.password, STUDENT_PAYLOAD["password"])
        self.assertTrue(user.password.startswith(("pbkdf2_", "argon2", "scrypt$")))
        self.assertTrue(user.check_password(STUDENT_PAYLOAD["password"]))
        self.assertFalse(user.check_password("wrong-password"))

    def test_password_never_exposed_in_api_response(self):
        response = self.register(STUDENT_PAYLOAD)
        self.assertNotIn("password", str(response.data))
        login = self.login(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.assertNotIn("password", str(login.data))


class LoginTests(AuthAPITestCase):
    """(3) Both roles can log in. (4) Invalid credentials are rejected."""

    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(**STUDENT_PAYLOAD)
        User.objects.create_user(**RECRUITER_PAYLOAD)

    def test_student_can_login_and_gets_role(self):
        data = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertEqual(data["user"]["role"], "student")
        self.assertNotIn("password", data["user"])

    def test_recruiter_can_login_and_gets_role(self):
        data = self.login_tokens(RECRUITER_PAYLOAD["username"], RECRUITER_PAYLOAD["password"])
        self.assertEqual(data["user"]["role"], "recruiter")
        self.assertNotIn("password", data["user"])

    def test_legacy_token_endpoint_still_works(self):
        response = self.client.post(
            "/api/auth/token/",
            {"username": STUDENT_PAYLOAD["username"], "password": STUDENT_PAYLOAD["password"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIn("access", response.data)

    def test_invalid_password_rejected(self):
        response = self.login(STUDENT_PAYLOAD["username"], "wrong-password")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unknown_username_rejected(self):
        response = self.login("ghost", "whatever123")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_inactive_user_cannot_login(self):
        user = User.objects.get(username=STUDENT_PAYLOAD["username"])
        user.is_active = False
        user.save()
        response = self.login(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ProtectedEndpointTests(AuthAPITestCase):
    """(5) Protected pages cannot be opened without authentication."""

    def setUp(self):
        self.make_student()
        self.make_recruiter()

    def test_me_requires_authentication(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dashboard_requires_authentication(self):
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_user_list_requires_authentication(self):
        response = self.client.get("/api/auth/admin/users/")
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_me_returns_own_profile_only(self):
        student = User.objects.get(username=STUDENT_PAYLOAD["username"])
        tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.authenticate(tokens["access"])
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["id"], student.id)
        self.assertNotIn("password", str(response.data))

        other = User.objects.get(username=RECRUITER_PAYLOAD["username"])
        self.assertNotEqual(response.data["user"]["id"], other.id)

    def test_me_returns_role_specific_profile(self):
        self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        student_tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.authenticate(student_tokens["access"])
        response = self.client.get("/api/auth/me/")
        self.assertIn("full_name", response.data["profile"])

        recruiter_tokens = self.login_tokens(RECRUITER_PAYLOAD["username"], RECRUITER_PAYLOAD["password"])
        self.authenticate(recruiter_tokens["access"])
        response = self.client.get("/api/auth/me/")
        self.assertIn("company_name", response.data["profile"])


class RoleIsolationTests(AuthAPITestCase):
    """(6) Student cannot access recruiter-only endpoints.
       (7) Recruiter cannot access student-only endpoints."""

    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(**STUDENT_PAYLOAD)
        User.objects.create_user(**RECRUITER_PAYLOAD)

    def student_auth(self):
        tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.authenticate(tokens["access"])

    def recruiter_auth(self):
        tokens = self.login_tokens(RECRUITER_PAYLOAD["username"], RECRUITER_PAYLOAD["password"])
        self.authenticate(tokens["access"])

    def test_student_cannot_access_recruiter_only_dashboard(self):
        self.student_auth()
        response = self.client.get("/api/dashboard/recruiter/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_recruiter_cannot_access_student_only_dashboard(self):
        self.recruiter_auth()
        response = self.client.get("/api/dashboard/student/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_access_recruiter_jobs_endpoint(self):
        self.student_auth()
        response = self.client.get("/api/jobs/mine/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_recruiter_cannot_access_student_applications_endpoint(self):
        self.recruiter_auth()
        response = self.client.get("/api/applications/mine/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_allowed_on_student_dashboard(self):
        self.student_auth()
        response = self.client.get("/api/dashboard/student/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("resume", response.data)
        self.assertIn("quizzes", response.data)
        self.assertNotIn("by_status", response.data)

    def test_recruiter_allowed_on_recruiter_dashboard(self):
        self.recruiter_auth()
        response = self.client.get("/api/dashboard/recruiter/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("jobs", response.data)
        self.assertIn("by_status", response.data["jobs"])

    def test_student_cannot_list_all_users(self):
        self.student_auth()
        response = self.client.get("/api/auth/admin/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminCanUseStudentExperienceTests(AuthAPITestCase):
    """An admin account can run the student flow, but only on its own records.

    Admins need to exercise the real product (profile, resume analysis, job
    matching, applications, quizzes, mock interview) to check it works. The
    invariant that must not bend is ownership: everything an admin writes is
    attributed to the admin, and nothing belonging to a real student is
    reachable through the student endpoints.
    """

    def setUp(self):
        self.student = self.make_student()
        self.admin = self.make_admin()
        self.recruiter = self.make_recruiter()
        self.admin_auth()

    def admin_auth(self):
        tokens = self.login_tokens(ADMIN_PAYLOAD["username"], ADMIN_PAYLOAD["password"])
        self.authenticate(tokens["access"])

    def student_auth(self):
        tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.authenticate(tokens["access"])

    def recruiter_auth(self):
        tokens = self.login_tokens(RECRUITER_PAYLOAD["username"], RECRUITER_PAYLOAD["password"])
        self.authenticate(tokens["access"])

    def test_admin_counts_as_student_but_stays_admin(self):
        self.assertTrue(self.admin.is_student)
        self.assertTrue(self.admin.is_admin_role)
        self.assertEqual(self.admin.role, User.Role.ADMIN)
        # A recruiter is still not a student.
        self.assertFalse(self.recruiter.is_student)

    def test_admin_can_read_student_dashboard(self):
        response = self.client.get("/api/dashboard/student/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        for section in ("resume", "profile", "jobs", "quizzes", "interviews"):
            self.assertIn(section, response.data)

    def test_admin_role_dashboard_still_wins_on_the_role_aware_endpoint(self):
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertIn("colleges", response.data)
        self.assertNotIn("resume", response.data)

    def test_admin_can_use_the_student_profile_endpoints(self):
        response = self.client.get("/api/profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        response = self.client.post(
            "/api/profile/skills/", {"name": "Python"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(self.admin.student_profile.skills.filter(name="Python").exists())
        # The real student's skills are untouched.
        self.assertFalse(self.student.student_profile.skills.exists())

    def test_admin_can_edit_their_own_student_profile(self):
        response = self.client.put(
            "/api/auth/me/",
            {"profile": {"full_name": "Test Admin", "college": "Test College"}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(self.admin.is_admin_role)
        self.assertEqual(self.admin.student_profile.full_name, "Test Admin")

    def test_admin_applications_are_their_own_not_a_students(self):
        from apps.jobs.models import Job

        job = Job.objects.create(
            recruiter=self.recruiter, company_name="Acme", title="SDE",
            description="Build things", location="Remote",
        )
        response = self.client.post(f"/api/jobs/{job.id}/apply/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        mine = self.client.get("/api/applications/mine/")
        self.assertEqual(mine.status_code, status.HTTP_200_OK, mine.data)
        self.assertEqual(len(mine.data["results"]), 1)
        self.assertEqual(mine.data["results"][0]["id"], response.data["id"])

        # And the student still has none of their own.
        self.student_auth()
        theirs = self.client.get("/api/applications/mine/")
        self.assertEqual(theirs.status_code, status.HTTP_200_OK, theirs.data)
        self.assertEqual(theirs.data["results"], [])

    def test_admin_cannot_read_a_students_resume_through_student_endpoints(self):
        from apps.resumes.models import Resume

        resume = Resume.objects.create(
            user=self.student, original_name="jane.pdf", file="resumes/student/jane.pdf"
        )
        response = self.client.get(f"/api/resumes/{resume.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.data)

    def test_recruiter_still_cannot_use_student_endpoints(self):
        self.recruiter_auth()
        for url in ("/api/dashboard/student/", "/api/applications/mine/", "/api/profile/"):
            response = self.client.get(url)
            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN,
                f"{url} should stay closed to recruiters",
            )


class AdminInspectionEndpointTests(AuthAPITestCase):
    """Admins can read every student's records; students and recruiters cannot.

    These endpoints exist so an admin can confirm the platform is recording
    what it should. They are strictly read-only: there is no POST/PATCH/DELETE.
    """

    def setUp(self):
        self.student = self.make_student()
        self.admin = self.make_admin()
        self.recruiter = self.make_recruiter()
        self.other = self.make_student({
            "username": "ryan_student", "email": "ryan@example.com",
            "password": "Str0ngPass!23", "first_name": "Ryan", "last_name": "Reed",
            "role": "student",
        })
        self.authenticate(
            self.login_tokens(ADMIN_PAYLOAD["username"], ADMIN_PAYLOAD["password"])["access"]
        )

    INSPECTION_URLS = [
        "/api/resumes/admin/",
        "/api/admin/applications/",
        "/api/interviews/admin/",
    ]

    def test_inspection_lists_are_read_only(self):
        for url in self.INSPECTION_URLS:
            for method in ("post", "put", "patch", "delete"):
                response = getattr(self.client, method)(url, {}, format="json")
                self.assertEqual(
                    response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED,
                    f"{method.upper()} {url} must not be allowed",
                )

    def test_student_and_recruiter_are_refused(self):
        for payload, who in ((STUDENT_PAYLOAD, "student"), (RECRUITER_PAYLOAD, "recruiter")):
            self.authenticate(self.login_tokens(payload["username"], payload["password"])["access"])
            for url in self.INSPECTION_URLS:
                response = self.client.get(url)
                self.assertEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN,
                    f"{who} must not read {url}",
                )
        self.authenticate(
            self.login_tokens(ADMIN_PAYLOAD["username"], ADMIN_PAYLOAD["password"])["access"]
        )

    def test_resume_list_names_every_owner(self):
        from apps.resumes.models import Resume

        Resume.objects.create(
            user=self.student, original_name="jane.pdf", file="resumes/a/jane.pdf"
        )
        Resume.objects.create(
            user=self.other, original_name="ryan.pdf", file="resumes/b/ryan.pdf"
        )
        response = self.client.get("/api/resumes/admin/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(
            {row["student_username"] for row in response.data},
            {self.student.username, self.other.username},
        )

    def test_a_bad_filter_id_is_a_400_not_a_silent_empty_list(self):
        """A typo in a filter should be reported, not read as "no records"."""
        cases = (
            ("/api/resumes/admin/", "student"),
            ("/api/admin/applications/", "student"),
            ("/api/admin/applications/", "job"),
            ("/api/quiz-attempts/", "student"),
            ("/api/quiz-attempts/", "quiz"),
        )
        for url, param in cases:
            response = self.client.get(f"{url}?{param}=not-an-id")
            self.assertEqual(
                response.status_code, status.HTTP_400_BAD_REQUEST,
                f"{url}?{param}=not-an-id should be a 400, got {response.data}",
            )

    def test_resume_list_filters_by_student(self):
        from apps.resumes.models import Resume

        Resume.objects.create(
            user=self.student, original_name="jane.pdf", file="resumes/a/jane.pdf"
        )
        Resume.objects.create(
            user=self.other, original_name="ryan.pdf", file="resumes/b/ryan.pdf"
        )
        response = self.client.get(f"/api/resumes/admin/?student={self.other.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual([row["student_username"] for row in response.data],
                         [self.other.username])

    def test_admin_can_read_a_students_resume_analysis(self):
        from apps.resumes.models import Resume, ResumeAnalysis

        resume = Resume.objects.create(
            user=self.student, original_name="jane.pdf", file="resumes/a/jane.pdf"
        )
        ResumeAnalysis.objects.create(resume=resume, status=ResumeAnalysis.Status.COMPLETED,
                                      detected_skills=["Python"], score=72)
        response = self.client.get(f"/api/resumes/admin/{resume.id}/analysis/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["score"], 72)
        self.assertEqual(response.data["detected_skills"], ["Python"])

    def test_admin_resume_analysis_404_when_none_stored(self):
        from apps.resumes.models import Resume

        resume = Resume.objects.create(
            user=self.student, original_name="jane.pdf", file="resumes/a/jane.pdf"
        )
        response = self.client.get(f"/api/resumes/admin/{resume.id}/analysis/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.data)

    def test_application_list_names_student_and_job(self):
        from apps.jobs.models import Job, JobApplication

        job = Job.objects.create(
            recruiter=self.recruiter, company_name="Acme", title="SDE",
            description="Build things", location="Remote",
        )
        JobApplication.objects.create(student=self.student, job=job, match_score=64)
        response = self.client.get("/api/admin/applications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data["results"]), 1)
        row = response.data["results"][0]
        self.assertEqual(row["student_username"], self.student.username)
        self.assertEqual(row["job_title"], "SDE")
        self.assertEqual(row["match_score"], 64)

    def test_interview_list_reports_answers_and_report_score(self):
        from apps.interviews.models import InterviewSession, InterviewTurn

        finished = InterviewSession.objects.create(
            student=self.student, position="SDE", status=InterviewSession.Status.COMPLETED,
            report_data={"score": 8},
        )
        for index in range(3):
            InterviewTurn.objects.create(
                session=finished, role=InterviewTurn.Role.USER,
                kind=InterviewTurn.Kind.ANSWER, content=f"answer {index}",
            )
        InterviewSession.objects.create(
            student=self.other, position="Data Analyst",
            status=InterviewSession.Status.IN_PROGRESS,
        )

        response = self.client.get("/api/interviews/admin/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data), 2)
        by_id = {row["id"]: row for row in response.data}
        self.assertEqual(by_id[finished.id]["answers"], 3)
        self.assertEqual(by_id[finished.id]["report_score"], 8)
        self.assertTrue(by_id[finished.id]["has_report"])

    def test_interview_list_filters_by_status(self):
        from apps.interviews.models import InterviewSession

        InterviewSession.objects.create(
            student=self.student, position="SDE", status=InterviewSession.Status.COMPLETED,
        )
        InterviewSession.objects.create(
            student=self.student, position="SDE", status=InterviewSession.Status.IN_PROGRESS,
        )
        response = self.client.get("/api/interviews/admin/?status=completed")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["status"], "completed")

    def test_quiz_attempt_list_names_the_student(self):
        from apps.assessments.models import Question, Quiz, QuizAttempt

        quiz = Quiz.objects.create(title="Python basics")
        Question.objects.create(quiz=quiz, text="2 + 2?", options=["3", "4"], correct_index=1)
        QuizAttempt.objects.create(
            student=self.student, quiz=quiz, status=QuizAttempt.Status.COMPLETED,
            score_percent=80, correct_count=4, total=5, submitted_at="2026-01-01T00:00:00Z",
        )
        response = self.client.get("/api/quiz-attempts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["student_username"], self.student.username)
        self.assertTrue(response.data[0]["passed"])


class LogoutTests(AuthAPITestCase):
    """(8) Logout works."""

    def setUp(self):
        User.objects.create_user(**STUDENT_PAYLOAD)

    def test_refresh_token_usable_before_logout(self):
        tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.authenticate(tokens["access"])
        refreshed = self.client.post(
            "/api/auth/token/refresh/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK, refreshed.data)

    def test_logout_blacklists_refresh_token(self):
        tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.authenticate(tokens["access"])

        response = self.client.post(
            "/api/auth/logout/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT, response.data)

        # The same refresh token is now rejected.
        after = self.client.post(
            "/api/auth/token/refresh/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(after.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_not_allowed_with_expired_or_alien_refresh(self):
        tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.authenticate(tokens["access"])
        response = self.client.post(
            "/api/auth/logout/", {"refresh": "not-a-real-token"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_requires_authentication(self):
        response = self.client.post("/api/auth/logout/", {"refresh": "x"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_rejects_missing_refresh(self):
        tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.authenticate(tokens["access"])
        response = self.client.post("/api/auth/logout/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AdminTests(AuthAPITestCase):
    """(9) Admin login/access works."""

    @classmethod
    def setUpTestData(cls):
        User.objects.create_superuser("root_admin", password="Adm1nPass!23")
        User.objects.create_user(**STUDENT_PAYLOAD)
        User.objects.create_user(**RECRUITER_PAYLOAD)

    def test_admin_can_login_with_role(self):
        data = self.login_tokens("root_admin", "Adm1nPass!23")
        self.assertEqual(data["user"]["role"], "admin")
        self.assertTrue(data["user"]["is_admin_role"])

    def test_admin_can_access_admin_endpoints(self):
        tokens = self.login_tokens("root_admin", "Adm1nPass!23")
        self.authenticate(tokens["access"])
        response = self.client.get("/api/auth/admin/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"] if isinstance(response.data, dict) and "results" in response.data else response.data
        usernames = {u["username"] for u in results}
        self.assertIn(STUDENT_PAYLOAD["username"], usernames)
        self.assertIn(RECRUITER_PAYLOAD["username"], usernames)

        admin_dash = self.client.get("/api/dashboard/admin/")
        self.assertEqual(admin_dash.status_code, status.HTTP_200_OK)
        self.assertIn("users", admin_dash.data)

    def test_non_admin_cannot_access_admin_endpoints(self):
        tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.authenticate(tokens["access"])
        response = self.client.get("/api/auth/admin/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        recruiter_tokens = self.login_tokens(RECRUITER_PAYLOAD["username"], RECRUITER_PAYLOAD["password"])
        self.authenticate(recruiter_tokens["access"])
        response = self.client.get("/api/dashboard/admin/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class Phase1RegressionTests(AuthAPITestCase):
    """(10) Existing Phase 1 functionality still works."""

    @classmethod
    def setUpTestData(cls):
        User.objects.create_user(**STUDENT_PAYLOAD)
        User.objects.create_user(**RECRUITER_PAYLOAD)

    def test_health_endpoint(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "ok")

    def test_role_aware_dashboard_still_works_for_all_roles(self):
        student_tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.authenticate(student_tokens["access"])
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("resume", response.data)

        recruiter_tokens = self.login_tokens(RECRUITER_PAYLOAD["username"], RECRUITER_PAYLOAD["password"])
        self.authenticate(recruiter_tokens["access"])
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("jobs", response.data)

    def test_job_listing_and_skills_still_work(self):
        tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.authenticate(tokens["access"])
        jobs = self.client.get("/api/jobs/")
        self.assertEqual(jobs.status_code, status.HTTP_200_OK, jobs.data)

        recruiter_tokens = self.login_tokens(RECRUITER_PAYLOAD["username"], RECRUITER_PAYLOAD["password"])
        self.authenticate(recruiter_tokens["access"])
        skills = self.client.get("/api/skills/")
        self.assertEqual(skills.status_code, status.HTTP_200_OK)

    def test_recruiter_can_create_job_and_student_can_list_it(self):
        recruiter_tokens = self.login_tokens(RECRUITER_PAYLOAD["username"], RECRUITER_PAYLOAD["password"])
        self.authenticate(recruiter_tokens["access"])
        created = self.client.post(
            "/api/jobs/",
            {
                "company_name": "Acme",
                "title": "Junior Developer",
                "description": "Build things.",
                "location": "Remote",
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)

        student_tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.authenticate(student_tokens["access"])
        listed = self.client.get("/api/jobs/")
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        titles = [j["title"] for j in listed.data]
        self.assertIn("Junior Developer", titles)


class LoginErrorMessageTests(AuthAPITestCase):
    """A wrong password must not be reported as a missing account.

    SimpleJWT's stock message says "No active account found with the given
    credentials" for both cases, which pushes a real user into registering a
    duplicate account instead of retyping their password.
    """

    def test_wrong_password_does_not_claim_the_account_is_missing(self):
        self.make_student()
        response = self.login(STUDENT_PAYLOAD["username"], "definitely-not-the-password")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        detail = str(response.data["detail"]).lower()
        self.assertNotIn("no active account", detail)
        self.assertIn("incorrect", detail)

    def test_unknown_user_and_wrong_password_are_indistinguishable(self):
        self.make_student()
        unknown = self.login("no_such_user_here", "some-password")
        wrong = self.login(STUDENT_PAYLOAD["username"], "some-password")
        self.assertEqual(unknown.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(wrong.status_code, status.HTTP_401_UNAUTHORIZED)
        # Identical wording: the response must not reveal which usernames exist.
        self.assertEqual(unknown.data["detail"], wrong.data["detail"])

    def test_disabled_account_cannot_log_in(self):
        user = self.make_student()
        user.is_active = False
        user.save(update_fields=["is_active"])
        response = self.login(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AdminAccountManagementTests(AuthAPITestCase):
    """The admin accounts screen: list every account, select and remove."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="boss_admin", password="Str0ngPass!23",
            email="boss@example.com", role=User.Role.ADMIN, is_staff=True,
        )
        self.student = self.make_student()
        self.recruiter = self.make_recruiter()
        tokens = self.login_tokens("boss_admin", "Str0ngPass!23")
        self.authenticate(tokens["access"])

    def test_admin_sees_every_account_with_their_records(self):
        response = self.client.get("/api/auth/admin/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data["results"] if isinstance(response.data, dict) else response.data
        usernames = {row["username"] for row in rows}
        self.assertEqual(usernames, {"boss_admin", "jane_student", "acme_hiring"})

        jane = next(row for row in rows if row["username"] == "jane_student")
        self.assertEqual(jane["role"], "student")
        self.assertTrue(jane["is_active"])
        self.assertEqual(jane["full_name"], "Jane Doe")
        self.assertIn("related_counts", jane)

        acme = next(row for row in rows if row["username"] == "acme_hiring")
        self.assertEqual(acme["company_name"], "acme_hiring")

    def test_student_cannot_reach_the_account_list(self):
        tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.authenticate(tokens["access"])
        self.assertEqual(
            self.client.get("/api/auth/admin/users/").status_code, status.HTTP_403_FORBIDDEN
        )

    def test_admin_can_bulk_delete_selected_accounts(self):
        ids = [self.student.id, self.recruiter.id]
        response = self.client.post(
            "/api/auth/admin/users/bulk-delete/", {"ids": ids}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["deleted"], 2)
        self.assertFalse(User.objects.filter(pk__in=ids).exists())

    def test_bulk_delete_never_removes_the_acting_admin(self):
        response = self.client.post(
            "/api/auth/admin/users/bulk-delete/", {"ids": [self.admin.id]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_bulk_delete_keeps_at_least_one_active_admin(self):
        second = User.objects.create_user(
            username="boss_two", password="Str0ngPass!23", role=User.Role.ADMIN,
        )
        # Both admins selected: the request must be refused, not half-applied.
        response = self.client.post(
            "/api/auth/admin/users/bulk-delete/",
            {"ids": [self.admin.id, second.id]}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.filter(role=User.Role.ADMIN).count(), 2)

    def test_bulk_delete_can_remove_all_but_one_admin(self):
        second = User.objects.create_user(
            username="boss_two", password="Str0ngPass!23", role=User.Role.ADMIN,
        )
        response = self.client.post(
            "/api/auth/admin/users/bulk-delete/", {"ids": [second.id]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["deleted"], 1)
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_bulk_delete_rejects_an_empty_selection(self):
        response = self.client.post(
            "/api/auth/admin/users/bulk-delete/", {"ids": []}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_bulk_delete_rejects_an_unknown_id_and_deletes_nothing(self):
        response = self.client.post(
            "/api/auth/admin/users/bulk-delete/",
            {"ids": [self.student.id, 999999]}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # The valid id in the same request must survive.
        self.assertTrue(User.objects.filter(pk=self.student.pk).exists())

    def test_admin_can_disable_and_re_enable_an_account(self):
        response = self.client.patch(
            f"/api/auth/admin/users/{self.student.id}/", {"is_active": False}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)

        # A disabled account must not be able to sign in.
        self.client.credentials()
        self.assertEqual(
            self.login(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"]).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_single_delete_keeps_the_last_admin(self):
        response = self.client.delete(f"/api/auth/admin/users/{self.admin.id}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())

    def test_deleting_an_account_removes_its_related_records(self):
        from apps.interviews.models import InterviewSession
        InterviewSession.objects.create(student=self.student, position="Django Developer")
        self.assertEqual(InterviewSession.objects.filter(student=self.student).count(), 1)
        self.client.delete(f"/api/auth/admin/users/{self.student.id}/")
        self.assertEqual(InterviewSession.objects.filter(student=self.student).count(), 0)


class AdminResetPasswordTests(AuthAPITestCase):
    """A locked-out account has to be recoverable from the accounts screen."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="boss_admin", password="Str0ngPass!23", role=User.Role.ADMIN,
        )
        self.student = self.make_student()
        tokens = self.login_tokens("boss_admin", "Str0ngPass!23")
        self.authenticate(tokens["access"])

    def test_admin_can_set_a_new_password_and_the_user_can_log_in(self):
        response = self.client.post(
            f"/api/auth/admin/users/{self.student.id}/reset-password/",
            {"password": "BrandNewPass!9"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.client.credentials()
        self.assertEqual(
            self.login(STUDENT_PAYLOAD["username"], "BrandNewPass!9").status_code,
            status.HTTP_200_OK,
        )

    def test_reset_reactivates_a_disabled_account(self):
        self.student.is_active = False
        self.student.save(update_fields=["is_active"])
        self.client.post(
            f"/api/auth/admin/users/{self.student.id}/reset-password/",
            {"password": "BrandNewPass!9"}, format="json",
        )
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_active)

    def test_short_password_is_rejected(self):
        response = self.client.post(
            f"/api/auth/admin/users/{self.student.id}/reset-password/",
            {"password": "short"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_cannot_reset_someone_elses_password(self):
        tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.authenticate(tokens["access"])
        response = self.client.post(
            f"/api/auth/admin/users/{self.admin.id}/reset-password/",
            {"password": "HijackedPass!1"}, format="json",
        )
        self.assertIn(
            response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)
        )
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("Str0ngPass!23"))


class SuperAdminEmailTests(AuthAPITestCase):
    """The super email list is full admin access, so it needs real guardrails."""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="root_admin", email="root@example.com",
            password="Str0ngPass!23", role=User.Role.ADMIN,
        )
        self.grantee = self.make_student()
        self.grantee.email = "partner@example.com"
        self.grantee.save(update_fields=["email"])
        # The manager role requires a listed address, not just the admin role.
        SuperAdminEmail.objects.create(
            email="root@example.com", added_by=self.admin, note="owner",
        )
        tokens = self.login_tokens("root_admin", "Str0ngPass!23")
        self.authenticate(tokens["access"])

    def test_manager_can_list_add_and_remove_addresses(self):
        response = self.client.get("/api/auth/admin/super-emails/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

        created = self.client.post(
            "/api/auth/admin/super-emails/",
            {"email": "Partner@Example.com", "note": "second pair of hands"},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        # Must be normalised, or the lowercase match at login would miss it.
        self.assertEqual(created.data["email"], "partner@example.com")
        self.assertEqual(created.data["added_by"], "root_admin")

        removed = self.client.delete(
            f"/api/auth/admin/super-emails/{created.data['id']}/"
        )
        self.assertEqual(removed.status_code, status.HTTP_204_NO_CONTENT)

    def test_listed_email_is_promoted_to_admin_on_login(self):
        SuperAdminEmail.objects.create(email="partner@example.com", added_by=self.admin)
        tokens = self.login(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.assertEqual(tokens.status_code, status.HTTP_200_OK)
        self.assertEqual(tokens.data["user"]["role"], User.Role.ADMIN)
        self.grantee.refresh_from_db()
        self.assertEqual(self.grantee.role, User.Role.ADMIN)
        self.assertTrue(self.grantee.is_staff)

    def test_listed_email_can_reach_admin_endpoints(self):
        SuperAdminEmail.objects.create(email="partner@example.com", added_by=self.admin)
        tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.authenticate(tokens["access"])
        self.assertEqual(
            self.client.get("/api/auth/admin/users/").status_code,
            status.HTTP_200_OK,
        )

    def test_unlisted_email_gains_nothing(self):
        tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.authenticate(tokens["access"])
        self.assertEqual(
            self.client.get("/api/auth/admin/users/").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_deactivated_entry_stops_granting(self):
        entry = SuperAdminEmail.objects.create(
            email="partner@example.com", added_by=self.admin
        )
        # Sign in while active: that is what promotes the account to admin.
        tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.grantee.refresh_from_db()
        self.assertEqual(self.grantee.role, User.Role.ADMIN)

        # Deactivating must revoke the admin role, not just block future logins.
        self.client.patch(
            f"/api/auth/admin/super-emails/{entry.id}/", {"is_active": False},
            format="json",
        )
        self.grantee.refresh_from_db()
        self.assertEqual(self.grantee.role, User.Role.STUDENT)
        self.assertFalse(self.grantee.is_staff)

        self.authenticate(tokens["access"])
        self.assertEqual(
            self.client.get("/api/auth/admin/users/").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_removed_entry_also_revokes_admin_role(self):
        entry = SuperAdminEmail.objects.create(
            email="partner@example.com", added_by=self.admin
        )
        self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.grantee.refresh_from_db()
        self.assertEqual(self.grantee.role, User.Role.ADMIN)

        self.client.delete(f"/api/auth/admin/super-emails/{entry.id}/")
        self.grantee.refresh_from_db()
        self.assertEqual(self.grantee.role, User.Role.STUDENT)

    def test_duplicate_email_is_rejected(self):
        response = self.client.post(
            "/api/auth/admin/super-emails/", {"email": "ROOT@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_last_active_entry_cannot_be_removed(self):
        only = SuperAdminEmail.objects.get(email="root@example.com")
        response = self.client.delete(f"/api/auth/admin/super-emails/{only.id}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(SuperAdminEmail.objects.filter(pk=only.pk).exists())

    def test_plain_admin_cannot_manage_the_list(self):
        User.objects.create_user(
            username="other_admin", email="other@example.com",
            password="Str0ngPass!23", role=User.Role.ADMIN,
        )
        tokens = self.login_tokens("other_admin", "Str0ngPass!23")
        self.authenticate(tokens["access"])
        self.assertEqual(
            self.client.get("/api/auth/admin/super-emails/").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post("/api/auth/admin/super-emails/",
                             {"email": "sneaky@example.com"},
                             format="json").status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertFalse(SuperAdminEmail.objects.filter(email="sneaky@example.com").exists())

    def test_admin_can_change_their_own_email(self):
        response = self.client.patch(
            "/api/auth/me/email/", {"email": "Owner@NewDomain.com"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.email, "owner@newdomain.com")

    def test_changing_to_an_email_already_in_use_is_rejected(self):
        self.grantee.email = "taken@example.com"
        self.grantee.save(update_fields=["email"])
        response = self.client.patch(
            "/api/auth/me/email/", {"email": "taken@example.com"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_new_address_still_needs_a_signed_in_account(self):
        # Granting an email alone must not let an anonymous visitor in.
        self.client.credentials()
        self.assertEqual(
            self.client.get("/api/auth/admin/users/").status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class SuperAdminEmailLockoutTests(AuthAPITestCase):
    """Regression tests: the owner must never be able to lock themselves out."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="owner", email="owner@example.com", password="Str0ngPass!23",
        )
        tokens = self.login_tokens("owner", "Str0ngPass!23")
        self.authenticate(tokens["access"])

    def test_adding_a_partner_also_lists_the_owner(self):
        # The owner is a superuser, so they can reach the list without already
        # being on it. Adding someone must not leave the list owner-less.
        response = self.client.post(
            "/api/auth/admin/super-emails/", {"email": "partner@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        listed = {row["email"] for row in
                  self.client.get("/api/auth/admin/super-emails/").data["results"]}
        self.assertEqual(listed, {"owner@example.com", "partner@example.com"})

    def test_owner_can_now_revoke_the_partner(self):
        added = self.client.post(
            "/api/auth/admin/super-emails/", {"email": "partner@example.com"},
            format="json",
        ).data
        revoked = self.client.patch(
            f"/api/auth/admin/super-emails/{added['id']}/", {"is_active": False},
            format="json",
        )
        self.assertEqual(revoked.status_code, status.HTTP_200_OK, revoked.data)
        self.assertFalse(revoked.data["is_active"])

    def test_non_superuser_manager_is_still_protected_from_lockout(self):
        manager = User.objects.create_user(
            username="plain_mgr", email="mgr@example.com",
            password="Str0ngPass!23", role=User.Role.ADMIN,
        )
        only = SuperAdminEmail.objects.create(
            email="mgr@example.com", added_by=manager, is_active=True
        )
        tokens = self.login_tokens("plain_mgr", "Str0ngPass!23")
        self.authenticate(tokens["access"])
        response = self.client.patch(
            f"/api/auth/admin/super-emails/{only.id}/", {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_changing_owner_email_carries_the_list_entry_along(self):
        response = self.client.patch(
            "/api/auth/me/email/", {"email": "founder@newdomain.com"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(
            SuperAdminEmail.objects.filter(email="founder@newdomain.com").exists(),
            "owner lost the ability to manage the list after an email change",
        )
        self.assertFalse(SuperAdminEmail.objects.filter(email="owner@example.com").exists())

    def test_changing_to_an_existing_super_email_retires_the_old_row(self):
        SuperAdminEmail.objects.create(email="partner@example.com", added_by=self.admin)
        response = self.client.patch(
            "/api/auth/me/email/", {"email": "partner@example.com"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        # Still exactly one grant, not two rows fighting over the same address.
        self.assertEqual(SuperAdminEmail.objects.count(), 1)
        self.assertTrue(SuperAdminEmail.objects.filter(email="partner@example.com").exists())

    def test_student_changing_own_email_cannot_grant_themselves_admin(self):
        # Otherwise /me/email/ would be a one-call self-promotion.
        self.make_student()
        tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.authenticate(tokens["access"])
        response = self.client.patch(
            "/api/auth/me/email/", {"email": "sneaky@example.com"}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(
            SuperAdminEmail.objects.filter(email="sneaky@example.com").exists()
        )
        self.assertEqual(
            self.client.get("/api/auth/admin/super-emails/").status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_revoked_partner_is_demoted_and_locked_out(self):
        self.make_student()
        student = User.objects.get(username=STUDENT_PAYLOAD["username"])
        student.email = "partner@example.com"
        student.save(update_fields=["email"])

        # The grant has to exist before signing in for it to promote anything.
        added = self.client.post(
            "/api/auth/admin/super-emails/", {"email": "partner@example.com"},
            format="json",
        ).data
        self.client.patch(
            f"/api/auth/admin/super-emails/{added['id']}/", {"is_active": False},
            format="json",
        )
        student.refresh_from_db()
        self.assertEqual(student.role, User.Role.STUDENT)

        tokens = self.login_tokens(STUDENT_PAYLOAD["username"], STUDENT_PAYLOAD["password"])
        self.authenticate(tokens["access"])
        self.assertEqual(
            self.client.get("/api/auth/admin/users/").status_code,
            status.HTTP_403_FORBIDDEN,
        )
