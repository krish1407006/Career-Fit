from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import RecruiterProfile, StudentProfile
from apps.jobs.models import Skill
from apps.resumes.models import Resume

User = get_user_model()

STUDENT_PAYLOAD = {
    "username": "jane_student",
    "email": "jane@example.com",
    "password": "Str0ngPass!23",
    "first_name": "Jane",
    "last_name": "Doe",
    "role": "student",
}

OTHER_PAYLOAD = {
    "username": "ryan_student",
    "email": "ryan@example.com",
    "password": "Str0ngPass!23",
    "first_name": "Ryan",
    "last_name": "Reed",
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


class ProfileAPITestCase(APITestCase):
    def make_user(self, payload):
        payload = dict(payload)
        raw_password = payload.pop("password")
        user = User.objects.create_user(**payload, password=raw_password)
        user._raw_password = raw_password
        if user.role == User.Role.STUDENT:
            StudentProfile.objects.create(
                user=user, full_name=f"{user.first_name} {user.last_name}".strip()
            )
        elif user.role == User.Role.RECRUITER:
            RecruiterProfile.objects.create(user=user, company_name=user.username)
        return user

    def login(self, user):
        response = self.client.post(
            "/api/auth/login/",
            {"username": user.username, "password": user._raw_password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")


class ProfileAPITests(ProfileAPITestCase):
    def setUp(self):
        self.student = self.make_user(STUDENT_PAYLOAD)
        self.other = self.make_user(OTHER_PAYLOAD)
        self.recruiter = self.make_user(RECRUITER_PAYLOAD)
        self.admin = self.make_user(ADMIN_PAYLOAD)

    def test_student_can_view_own_profile(self):
        self.login(self.student)
        response = self.client.get("/api/profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["profile"]["full_name"], "Jane Doe")
        self.assertIn("skills", response.data)
        self.assertIn("education", response.data)
        self.assertIn("projects", response.data)
        self.assertIn("certifications", response.data)
        self.assertIn("completion", response.data)

    def test_student_can_edit_profile(self):
        self.login(self.student)
        response = self.client.put(
            "/api/profile/",
            {
                "full_name": "Jane Q. Doe",
                "college": "MIT",
                "degree": "B.Tech",
                "branch": "CSE",
                "graduation_year": 2027,
                "cgpa": 8.7,
                "phone": "9876543210",
                "location": "Bangalore",
                "bio": "CS undergrad",
                "preferred_roles": ["SDE"],
                "preferred_technologies": ["Python", "Django"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["profile"]["degree"], "B.Tech")
        self.assertEqual(response.data["profile"]["bio"], "CS undergrad")
        self.assertEqual(response.data["profile"]["preferred_roles"], ["SDE"])

    def test_recruiter_and_admin_cannot_access_student_profile(self):
        self.login(self.recruiter)
        response = self.client.get("/api/profile/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.login(self.admin)
        response = self.client.get("/api/profile/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_access_denied(self):
        response = self.client.get("/api/profile/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_skills_add_and_remove(self):
        self.login(self.student)
        response = self.client.post("/api/profile/skills/", {"name": "Python"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        skill_id = response.data["id"]

        response = self.client.get("/api/profile/skills/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([s["name"] for s in response.data], ["Python"])

        response = self.client.delete(f"/api/profile/skills/{skill_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get("/api/profile/skills/")
        self.assertEqual(response.data, [])

    def test_skills_reuse_catalog(self):
        Skill.objects.create(name="Python", category="Language")
        self.login(self.student)
        response = self.client.post("/api/profile/skills/", {"name": "python"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Skill.objects.filter(name__iexact="python").count(), 1)
        self.assertEqual(response.data["name"], "Python")

    def test_education_crud(self):
        self.login(self.student)
        response = self.client.post(
            "/api/education/",
            {"institution": "IIT-M", "degree": "B.Tech", "field_of_study": "CSE", "start_year": 2023, "end_year": 2027, "cgpa": 8.5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        edu_id = response.data["id"]

        response = self.client.put(
            f"/api/education/{edu_id}/",
            {"institution": "IIT-M", "degree": "B.Tech", "field_of_study": "CSE", "cgpa": 9.1},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["cgpa"], "9.10")

        response = self.client.get("/api/education/")
        self.assertEqual(len(response.data), 1)

        response = self.client.delete(f"/api/education/{edu_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(StudentProfile.objects.get(user=self.student).education.count(), 0)

    def test_projects_crud(self):
        self.login(self.student)
        response = self.client.post(
            "/api/projects/",
            {"title": "Career Fit", "description": "Job portal", "technologies": ["Django", "React"], "link": "https://example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        project_id = response.data["id"]

        response = self.client.put(
            f"/api/projects/{project_id}/",
            {"title": "Career Fit v2", "description": "Job portal with AI", "technologies": ["Django", "React", "AI"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Career Fit v2")

        response = self.client.delete(f"/api/projects/{project_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(StudentProfile.objects.get(user=self.student).projects.count(), 0)

    def test_certifications_crud(self):
        self.login(self.student)
        response = self.client.post(
            "/api/certifications/",
            {"name": "AWS Developer", "issuer": "Amazon", "issue_date": "2025-06-01", "credential_url": "https://example.com/cred"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        cert_id = response.data["id"]

        response = self.client.put(
            f"/api/certifications/{cert_id}/",
            {"name": "AWS Developer Associate", "issuer": "Amazon"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "AWS Developer Associate")

        response = self.client.delete(f"/api/certifications/{cert_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(StudentProfile.objects.get(user=self.student).certifications.count(), 0)

    def test_student_isolation_privacy(self):
        self.login(self.other)
        response = self.client.post(
            "/api/projects/",
            {"title": "Other's project", "description": "secret"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        jane_profile = StudentProfile.objects.get(user=self.student)
        project = jane_profile.projects.create(title="Jane's project", description="private")
        edu = jane_profile.education.create(institution="College", degree="B.Sc")

        self.login(self.other)
        response = self.client.get(f"/api/projects/{project.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.delete(f"/api/projects/{project.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(jane_profile.projects.filter(id=project.id).exists())

        response = self.client.get(f"/api/education/{edu.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        jane_skill = Skill.objects.create(name="JaneSkill")
        jane_profile.skills.add(jane_skill)
        response = self.client.delete(f"/api/profile/skills/{jane_skill.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(jane_profile.skills.filter(id=jane_skill.id).exists())

    def test_dashboard_returns_profile_stats(self):
        self.login(self.student)
        skill = Skill.objects.create(name="Python")
        profile = StudentProfile.objects.get(user=self.student)
        profile.skills.add(skill)
        profile.projects.create(title="Project A", description="x")

        response = self.client.get("/api/dashboard/student/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("profile", response.data)
        self.assertEqual(response.data["profile"]["skills_count"], 1)
        self.assertEqual(response.data["profile"]["projects_count"], 1)
        self.assertEqual(response.data["profile"]["resume_uploaded"], False)

    def test_recruiter_login_and_dashboard_still_work(self):
        self.login(self.recruiter)
        response = self.client.get("/api/dashboard/recruiter/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("jobs", response.data)

    def test_admin_login_and_admin_routes_still_work(self):
        self.login(self.admin)
        response = self.client.get("/api/dashboard/admin/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("users", response.data)

        response = self.client.get("/api/auth/admin/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)