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
        plain = User.objects.create_user(
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
