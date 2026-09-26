"""Phase 6 API + integration tests for AI resume analysis.

The external AI provider is mocked everywhere: no test performs a real AI call.
"""

import shutil
import tempfile
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import StudentProfile
from apps.ai import providers
from apps.ai.errors import AiParseError, ProviderUnavailable
from apps.jobs.models import Job, Skill
from apps.jobs.views import candidate_skills_for
from apps.resumes.models import Resume, ResumeAnalysis
from apps.resumes.text_extraction import extract_text_from_resume

User = get_user_model()

TEMP_MEDIA = tempfile.mkdtemp(prefix="careerai_analysis_tests_")

PASSWORD = "Str0ngPass!23"

AI_PAYLOAD = {
    "summary": "Final-year CSE student with Django and React project experience.",
    "detected_skills": ["Python", "Django", "PostgreSQL", "Redis"],
    "strengths": ["Backend project with a measurable outcome"],
    "skill_gaps": ["No evidence of Docker or cloud deployment"],
    "improvements": ["Add measurable results to each project bullet"],
    "recommended_roles": ["Backend Developer"],
    "education": ["B.Tech CSE"],
    "experience": ["Backend developer intern"],
    "score": 74,
}

# A real, text-based PDF so the existing extraction service is exercised.
REAL_PDF_TEXT = (
    b"BT /F1 12 Tf 72 720 Td (Jane Doe - B.Tech Computer Science and Engineering) Tj "
    b"0 -20 Td (Skills: Python, Django, PostgreSQL, Git and Docker) Tj "
    b"0 -20 Td (Project: CareerAI placement platform with Django and React.) Tj "
    b"0 -20 Td (Internship: backend intern, reduced API latency by 40 percent.) Tj ET"
)


def build_pdf(text_lines=REAL_PDF_TEXT):
    """Assemble a minimal single-page PDF whose text stream is extractable."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(text_lines)).encode() + b" >>\nstream\n" + text_lines + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF\n"
    ).encode()
    return bytes(out)


def make_student(username, **profile_kwargs):
    user = User.objects.create_user(
        username=username, password=PASSWORD, email=f"{username}@example.com",
        role=User.Role.STUDENT,
    )
    StudentProfile.objects.create(user=user, full_name=username.title(), **profile_kwargs)
    return user


def upload_resume(user, name="jane_cv.pdf", pdf_bytes=None):
    return Resume.objects.create(
        user=user,
        file=SimpleUploadedFile(name, pdf_bytes if pdf_bytes is not None else build_pdf()),
        original_name=name,
    )


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ResumeAnalysisPermissionTests(APITestCase):
    """1/2/3. Ownership rules for analyze + read endpoints."""

    def setUp(self):
        self.student = make_student("owner_student")
        self.other = make_student("other_student")
        self.resume = upload_resume(self.student)

    def login(self, user):
        response = self.client.post(
            "/api/auth/login/", {"username": user.username, "password": PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def mock_ai(self, payload=None):
        return mock.patch.object(
            providers, "chat_json", return_value=payload if payload is not None else AI_PAYLOAD
        )

    def test_student_can_analyze_own_resume(self):
        self.login(self.student)
        with self.mock_ai():
            response = self.client.post(f"/api/resumes/{self.resume.id}/analyze/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["status"], "completed")
        self.assertEqual(response.data["detected_skills"], AI_PAYLOAD["detected_skills"])
        self.assertTrue(ResumeAnalysis.objects.filter(resume=self.resume).exists())

    def test_student_cannot_analyze_another_students_resume(self):
        self.login(self.other)
        with self.mock_ai():
            response = self.client.post(f"/api/resumes/{self.resume.id}/analyze/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(ResumeAnalysis.objects.filter(resume=self.resume).exists())

    def test_student_cannot_view_another_students_analysis(self):
        with self.mock_ai():
            self.login(self.student)
            self.client.post(f"/api/resumes/{self.resume.id}/analyze/")
            analysis_id = ResumeAnalysis.objects.get(resume=self.resume).id

            self.client.credentials()
            self.login(self.other)
            for url in (
                f"/api/resumes/{self.resume.id}/analysis/",
                f"/api/resume-analyses/{analysis_id}/",
            ):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, url)

    def test_owner_can_read_analysis_by_id(self):
        with self.mock_ai():
            self.login(self.student)
            self.client.post(f"/api/resumes/{self.resume.id}/analyze/")
        analysis = ResumeAnalysis.objects.get(resume=self.resume)
        response = self.client.get(f"/api/resume-analyses/{analysis.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["summary"], AI_PAYLOAD["summary"])

    def test_analysis_before_running_returns_404(self):
        self.login(self.student)
        response = self.client.get(f"/api/resumes/{self.resume.id}/analysis/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_is_rejected(self):
        for method, url in (
            ("post", f"/api/resumes/{self.resume.id}/analyze/"),
            ("get", f"/api/resumes/{self.resume.id}/analysis/"),
        ):
            response = getattr(self.client, method)(url)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED, url)

    def test_recruiter_cannot_analyze_a_resume(self):
        recruiter = User.objects.create_user(
            username="rec1", password=PASSWORD, email="rec1@example.com", role=User.Role.RECRUITER
        )
        self.login(recruiter)
        with self.mock_ai():
            response = self.client.post(f"/api/resumes/{self.resume.id}/analyze/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_id_in_body_is_ignored(self):
        self.login(self.other)
        with self.mock_ai():
            response = self.client.post(
                f"/api/resumes/{self.resume.id}/analyze/",
                {"user_id": self.student.id, "student_id": self.student.id},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ResumeAnalysisPipelineTests(APITestCase):
    """4/5/6/8/9/10. Extraction, storage, validation and skill integration."""

    def setUp(self):
        self.student = make_student("pipeline_student")
        self.resume = upload_resume(self.student)
        response = self.client.post(
            "/api/auth/login/",
            {"username": self.student.username, "password": PASSWORD},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def mock_ai(self, payload=None, **kwargs):
        return mock.patch.object(
            providers, "chat_json",
            return_value=payload if payload is not None else AI_PAYLOAD, **kwargs,
        )

    def test_existing_extraction_service_reads_the_uploaded_pdf(self):
        text = extract_text_from_resume(self.resume.file)
        self.assertIn("Python", text)
        self.assertIn("CareerAI", text)

    def test_valid_ai_output_is_saved_and_exposed(self):
        with self.mock_ai():
            response = self.client.post(f"/api/resumes/{self.resume.id}/analyze/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        analysis = ResumeAnalysis.objects.get(resume=self.resume)
        self.assertEqual(analysis.status, ResumeAnalysis.Status.COMPLETED)
        self.assertEqual(analysis.source, "ai")
        self.assertEqual(analysis.provider, "openai")
        self.assertEqual(analysis.score, 74)
        self.assertEqual(analysis.strengths, AI_PAYLOAD["strengths"])
        self.assertEqual(analysis.skill_gaps, AI_PAYLOAD["skill_gaps"])
        self.assertEqual(analysis.improvements, AI_PAYLOAD["improvements"])
        self.assertEqual(analysis.recommended_roles, AI_PAYLOAD["recommended_roles"])
        self.assertIn("Python", analysis.extracted_text)
        self.resume.refresh_from_db()
        self.assertEqual(self.resume.status, Resume.Status.ANALYZED)

    def test_resume_text_and_raw_ai_payload_are_not_exposed(self):
        with self.mock_ai():
            response = self.client.post(f"/api/resumes/{self.resume.id}/analyze/")
        for field in ("extracted_text", "raw", "api_key"):
            self.assertNotIn(field, response.data)
        self.assertNotIn("Jane Doe", str(response.data).replace(
            AI_PAYLOAD["summary"], ""))

    def test_empty_extracted_text_is_reported_clearly(self):
        empty_resume = upload_resume(self.student, "empty.pdf", b"%PDF-1.4\n%%EOF\n")
        with self.mock_ai() as ai:
            response = self.client.post(f"/api/resumes/{empty_resume.id}/analyze/")
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("readable text", response.data["detail"])
        ai.assert_not_called()
        analysis = ResumeAnalysis.objects.get(resume=empty_resume)
        self.assertEqual(analysis.status, ResumeAnalysis.Status.FAILED)
        self.assertIn("readable text", analysis.error_message)

    def test_scanned_pdf_without_text_does_not_crash(self):
        broken = upload_resume(self.student, "broken.pdf", b"not really a pdf at all")
        with self.mock_ai():
            response = self.client.post(f"/api/resumes/{broken.id}/analyze/")
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertNotIn("Traceback", str(response.data))
        self.assertIn("could not read", response.data["detail"].lower())

    def test_ai_service_failure_is_handled_gracefully(self):
        with mock.patch.object(providers, "chat_json",
                               side_effect=ProviderUnavailable("AI provider unreachable (ConnectError)")):
            with self.client.post(f"/api/resumes/{self.resume.id}/analyze/") as response:
                # AI_REQUIRED is off in tests -> deterministic offline fallback
                self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        analysis = ResumeAnalysis.objects.get(resume=self.resume)
        self.assertEqual(analysis.source, "offline")
        self.assertIn("could not be reached", analysis.notice)
        self.assertTrue(analysis.detected_skills)

    @override_settings(AI_REQUIRED=True)
    def test_ai_required_failure_returns_clean_error(self):
        with mock.patch.object(providers, "chat_json",
                               side_effect=ProviderUnavailable("AI provider rejected the configured API key")):
            response = self.client.post(f"/api/resumes/{self.resume.id}/analyze/")
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertNotIn("Traceback", response.data["detail"])
        analysis = ResumeAnalysis.objects.get(resume=self.resume)
        self.assertEqual(analysis.status, ResumeAnalysis.Status.FAILED)

    @override_settings(AI_REQUIRED=True)
    def test_missing_ai_configuration_is_handled_gracefully(self):
        with mock.patch.object(providers, "is_configured", return_value=False):
            response = self.client.post(f"/api/resumes/{self.resume.id}/analyze/")
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("AI_PROVIDER", response.data["detail"])
        self.assertIn("AI_API_KEY", response.data["detail"])
        self.assertEqual(ResumeAnalysis.objects.get(resume=self.resume).status,
                         ResumeAnalysis.Status.FAILED)

    def test_malformed_ai_output_is_rejected_safely(self):
        with self.mock_ai(payload={"totally": "unrelated"}):
            with self.client.post(f"/api/resumes/{self.resume.id}/analyze/") as response:
                self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        analysis = ResumeAnalysis.objects.get(resume=self.resume)
        self.assertEqual(analysis.source, "offline")
        self.assertIn("could not be reached", analysis.notice)

    @override_settings(AI_REQUIRED=True)
    def test_malformed_ai_output_does_not_overwrite_previous_analysis(self):
        with self.mock_ai():
            self.client.post(f"/api/resumes/{self.resume.id}/analyze/")
        good = ResumeAnalysis.objects.get(resume=self.resume)
        good_id = good.id
        with self.mock_ai(payload=[1, 2, 3]):
            with self.client.post(f"/api/resumes/{self.resume.id}/analyze/") as response:
                self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY, response.data)
        failed = ResumeAnalysis.objects.get(pk=good_id)
        self.assertEqual(failed.status, ResumeAnalysis.Status.FAILED)
        self.assertEqual(failed.detected_skills, AI_PAYLOAD["detected_skills"])
        self.assertEqual(failed.summary, AI_PAYLOAD["summary"])

    def test_existing_manual_skills_are_not_overwritten(self):
        profile = self.student.student_profile
        manual = Skill.objects.create(name="Java", category="Language")
        profile.skills.add(manual)

        with self.mock_ai():
            self.client.post(f"/api/resumes/{self.resume.id}/analyze/")

        names = set(profile.skills.values_list("name", flat=True))
        self.assertIn("Java", names)                      # manual skill preserved
        self.assertIn("Python", names)                    # AI skill added
        self.assertTrue(Skill.objects.filter(name="Java", category="Language").exists())

        response = self.client.get("/api/profile/")
        sources = {row["name"]: row["source"] for row in response.data["skills"]}
        self.assertEqual(sources["Java"], "manual")
        self.assertEqual(sources["Python"], "ai")

    def test_repeated_analysis_does_not_duplicate_skills(self):
        with self.mock_ai():
            self.client.post(f"/api/resumes/{self.resume.id}/analyze/")
            self.client.post(f"/api/resumes/{self.resume.id}/analyze/")
        self.assertEqual(Skill.objects.filter(name="Python").count(), 1)
        self.assertEqual(self.student.student_profile.skills.filter(name="Python").count(), 1)
        self.assertEqual(ResumeAnalysis.objects.filter(resume=self.resume).count(), 1)

    def test_existing_job_matching_still_uses_detected_skills(self):
        with self.mock_ai():
            self.client.post(f"/api/resumes/{self.resume.id}/analyze/")
        skills = candidate_skills_for(self.student)
        for name in ("python", "django", "postgresql", "redis"):
            self.assertIn(name, [s.lower() for s in skills])

    def test_analysis_feeds_job_matching_score(self):
        recruiter = User.objects.create_user(
            username="rec_match", password=PASSWORD, email="rec_match@example.com",
            role=User.Role.RECRUITER,
        )
        job = Job.objects.create(
            recruiter=recruiter, title="Backend Engineer", company_name="Acme",
            description="APIs", location="Remote",
        )
        for name in ("Python", "Django", "PostgreSQL", "Redis"):
            job.required_skills.add(Skill.objects.get_or_create(name=name)[0])

        with self.mock_ai():
            self.client.post(f"/api/resumes/{self.resume.id}/analyze/")
        response = self.client.get(f"/api/jobs/{job.id}/match/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["coverage"], 100.0)
        self.assertEqual(response.data["missing"], [])


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class JobRelevanceTests(APITestCase):
    """6. Job relevance reuses the existing matching service."""

    def setUp(self):
        self.student = make_student("relevance_student")
        self.resume = upload_resume(self.student)
        self.recruiter = User.objects.create_user(
            username="rec_rel", password=PASSWORD, email="rec_rel@example.com",
            role=User.Role.RECRUITER,
        )
        self.job = Job.objects.create(
            recruiter=self.recruiter, title="Backend Engineer", company_name="Acme",
            description="APIs", location="Remote",
        )
        for name in ("Python", "Django", "Kubernetes"):
            self.job.required_skills.add(Skill.objects.get_or_create(name=name)[0])
        response = self.client.post(
            "/api/auth/login/",
            {"username": self.student.username, "password": PASSWORD}, format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def analyze(self, **body):
        with mock.patch.object(providers, "chat_json", return_value=AI_PAYLOAD):
            return self.client.post(
                f"/api/resumes/{self.resume.id}/analyze/", body, format="json"
            )

    def test_selected_job_is_matched_with_existing_algorithm(self):
        response = self.analyze(job_id=self.job.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        relevance = response.data["job_relevance"]
        # 2 of 3 required skills detected by the AI analysis.
        self.assertEqual(relevance["match_score"], 67)
        self.assertEqual(sorted(relevance["matched_skills"]), ["django", "python"])
        self.assertEqual(relevance["missing_skills"], ["kubernetes"])
        self.assertEqual(relevance["job_id"], self.job.id)
        self.assertEqual(relevance["job_title"], "Backend Engineer")

    def test_relevance_is_persisted_on_the_analysis(self):
        self.analyze(job_id=self.job.id)
        analysis = ResumeAnalysis.objects.get(resume=self.resume)
        self.assertEqual(analysis.job_relevance["match_score"], 67)

    def test_relevance_is_empty_without_a_selected_job(self):
        response = self.analyze()
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["job_relevance"], {})

    def test_unknown_job_is_rejected(self):
        response = self.analyze(job_id=999999)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(ResumeAnalysis.objects.filter(status=ResumeAnalysis.Status.COMPLETED).exists())

    def test_invalid_job_id_is_rejected(self):
        response = self.analyze(job_id="abc")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class UploadCompatibilityTests(APITestCase):
    """The pre-existing upload flow keeps working unchanged."""

    def setUp(self):
        self.student = make_student("upload_student")
        response = self.client.post(
            "/api/auth/login/",
            {"username": self.student.username, "password": PASSWORD}, format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_upload_then_analyze_then_replace(self):
        upload = self.client.post(
            "/api/resumes/",
            {"file": SimpleUploadedFile("cv.pdf", build_pdf(), content_type="application/pdf")},
            format="multipart",
        )
        self.assertEqual(upload.status_code, status.HTTP_201_CREATED, upload.data)
        self.assertIsNone(upload.data["analysis"])

        with mock.patch.object(providers, "chat_json", return_value=AI_PAYLOAD):
            analyzed = self.client.post(f"/api/resumes/{upload.data['id']}/analyze/")
        self.assertEqual(analyzed.status_code, status.HTTP_200_OK, analyzed.data)
        self.assertEqual(analyzed.data["status"], "completed")

        # Replacing the resume drops the stale analysis with it.
        replaced = self.client.post(
            "/api/resumes/",
            {"file": SimpleUploadedFile("cv2.pdf", build_pdf(), content_type="application/pdf")},
            format="multipart",
        )
        self.assertEqual(replaced.status_code, status.HTTP_201_CREATED, replaced.data)
        self.assertEqual(Resume.objects.filter(user=self.student).count(), 1)
        self.assertEqual(ResumeAnalysis.objects.count(), 0)
        self.assertIsNone(replaced.data["analysis"])

    def test_resume_list_exposes_analysis(self):
        self.client.post(
            "/api/resumes/",
            {"file": SimpleUploadedFile("cv.pdf", build_pdf(), content_type="application/pdf")},
            format="multipart",
        )
        with mock.patch.object(providers, "chat_json", return_value=AI_PAYLOAD):
            self.client.post(f"/api/resumes/{Resume.objects.get().id}/analyze/")
        response = self.client.get("/api/resumes/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["analysis"]["status"], "completed")
        self.assertTrue(response.data[0]["analysis"]["has_analysis"])


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class DashboardAnalysisTests(APITestCase):
    """9. Lightweight resume-analysis block on the student dashboard."""

    def setUp(self):
        self.student = make_student("dash_student")
        response = self.client.post(
            "/api/auth/login/",
            {"username": self.student.username, "password": PASSWORD}, format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_dashboard_without_resume(self):
        response = self.client.get("/api/dashboard/student/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(response.data["resume"]["uploaded"])
        self.assertFalse(response.data["resume"]["analysis_completed"])
        self.assertEqual(response.data["resume"]["detected_skills_count"], 0)
        self.assertEqual(response.data["resume"]["skill_gaps_count"], 0)

    def test_dashboard_after_analysis(self):
        resume = upload_resume(self.student)
        with mock.patch.object(providers, "chat_json", return_value=AI_PAYLOAD):
            self.client.post(f"/api/resumes/{resume.id}/analyze/")
        response = self.client.get("/api/dashboard/student/")
        resume_block = response.data["resume"]
        self.assertTrue(resume_block["uploaded"])
        self.assertTrue(resume_block["analysis_completed"])
        self.assertEqual(resume_block["detected_skills_count"], 4)
        self.assertEqual(resume_block["skill_gaps_count"], 1)
        self.assertEqual(resume_block["score"], 74)
        self.assertEqual(resume_block["source"], "ai")


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class AnalysisParseErrorTests(APITestCase):
    """A provider that answers with non-JSON must not corrupt stored data."""

    def setUp(self):
        self.student = make_student("parse_student")
        self.resume = upload_resume(self.student)
        response = self.client.post(
            "/api/auth/login/",
            {"username": self.student.username, "password": PASSWORD}, format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    @override_settings(AI_REQUIRED=True)
    def test_unparsable_provider_output_is_reported_cleanly(self):
        with mock.patch.object(providers, "chat_json", side_effect=AiParseError("AI returned invalid JSON")):
            response = self.client.post(f"/api/resumes/{self.resume.id}/analyze/")
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertNotIn("Traceback", response.data["detail"])
        self.assertEqual(ResumeAnalysis.objects.get(resume=self.resume).status,
                         ResumeAnalysis.Status.FAILED)


def tearDownModule():
    shutil.rmtree(TEMP_MEDIA, ignore_errors=True)
