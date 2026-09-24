import atexit
import os
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import StudentProfile
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

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"

_MEDIA_ROOT = tempfile.mkdtemp(prefix="careerai-resume-tests-")


def make_pdf(name="resume.pdf"):
    return SimpleUploadedFile(name, PDF_BYTES, content_type="application/pdf")


def make_user(payload):
    payload = dict(payload)
    raw_password = payload.pop("password")
    user = User.objects.create_user(**payload, password=raw_password)
    user._raw_password = raw_password
    StudentProfile.objects.create(
        user=user, full_name=f"{user.first_name} {user.last_name}".strip()
    )
    return user


@override_settings(MEDIA_ROOT=_MEDIA_ROOT)
class ResumeAPITests(APITestCase):
    def setUp(self):
        self.student = make_user(STUDENT_PAYLOAD)
        self.other = make_user(OTHER_PAYLOAD)

    def login(self, user):
        response = self.client.post(
            "/api/auth/login/",
            {"username": user.username, "password": user._raw_password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def upload(self, upload_file):
        return self.client.post("/api/resumes/", {"file": upload_file}, format="multipart")

    def test_upload_pdf(self):
        self.login(self.student)
        response = self.upload(make_pdf())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        resume = Resume.objects.get(pk=response.data["id"])
        self.assertEqual(resume.original_name, "resume.pdf")
        self.assertEqual(resume.status, Resume.Status.UPLOADED)
        self.assertIn("download_url", response.data)
        self.assertTrue(resume.file.storage.exists(resume.file.name))

    def test_upload_rejects_non_pdf(self):
        self.login(self.student)
        for name in ("resume.docx", "resume.txt", "resume.pdf.txt"):
            response = self.upload(SimpleUploadedFile(name, b"hello", content_type="text/plain"))
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, name)
            self.assertIn("PDF", response.data["file"][0])
        self.assertEqual(Resume.objects.count(), 0)

    def test_upload_rejects_oversize(self):
        self.login(self.student)
        big = SimpleUploadedFile("big.pdf", b"x" * (11 * 1024 * 1024), content_type="application/pdf")
        response = self.upload(big)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Resume.objects.count(), 0)

    def test_upload_replaces_previous_resume(self):
        self.login(self.student)
        first = self.upload(make_pdf("first.pdf"))
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Resume.objects.count(), 1)
        first_file_name = Resume.objects.get(pk=first.data["id"]).file.name

        second = self.upload(make_pdf("second.pdf"))
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Resume.objects.count(), 1)
        self.assertEqual(Resume.objects.first().original_name, "second.pdf")
        old_path = os.path.join(_MEDIA_ROOT, first_file_name)
        self.assertFalse(os.path.exists(old_path), "old resume file should be deleted")

    def test_list_and_delete_resume(self):
        self.login(self.student)
        self.upload(make_pdf())
        resume_id = Resume.objects.first().id

        response = self.client.get("/api/resumes/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.client.delete(f"/api/resumes/{resume_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Resume.objects.count(), 0)

    def test_secure_download_owner_only(self):
        self.login(self.student)
        self.upload(make_pdf("Jane - CV.pdf"))
        resume = Resume.objects.first()

        response = self.client.get(f"/api/resumes/{resume.id}/download/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("Jane", response["Content-Disposition"])

        self.login(self.other)
        response = self.client.get(f"/api/resumes/{resume.id}/download/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_isolation_for_resumes(self):
        self.login(self.student)
        self.upload(make_pdf())
        resume_id = Resume.objects.first().id

        self.login(self.other)
        response = self.client.get(f"/api/resumes/{resume_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        response = self.client.delete(f"/api/resumes/{resume_id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Resume.objects.filter(id=resume_id).exists())

    def test_unauthenticated_upload_and_download_denied(self):
        response = self.upload(make_pdf())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


atexit.register(lambda: shutil.rmtree(_MEDIA_ROOT, ignore_errors=True))