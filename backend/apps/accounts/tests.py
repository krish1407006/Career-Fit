from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import RecruiterProfile, StudentProfile

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
