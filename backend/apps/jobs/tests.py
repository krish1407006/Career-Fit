import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import RecruiterProfile, StudentProfile

from .models import Job, JobApplication, Skill

User = get_user_model()

TEMP_MEDIA = tempfile.mkdtemp(prefix="careerai_test_media_")


class JobAPITestCase(APITestCase):
    """Shared setup: role users, auth helpers, and job factories."""

    @staticmethod
    def make_student(username, password="Str0ngPass!23", **extra):
        user = User.objects.create_user(
            username=username,
            password=password,
            email=f"{username}@example.com",
            role=User.Role.STUDENT,
            **extra,
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

    def login(self, username, password="Str0ngPass!23"):
        response = self.client.post(
            "/api/auth/login/", {"username": username, "password": password}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response.data

    @staticmethod
    def skills_for(job, required, preferred=None):
        def _resolve(names):
            return {Skill.objects.get_or_create(name=name)[0]
                    for name in (names or []) if str(name).strip()}
        job.required_skills.set(_resolve(required))
        if preferred:
            job.preferred_skills.set(_resolve(preferred))
        return job

    @staticmethod
    def make_job(recruiter, title="Python Developer", company="Acme",
                 description="Build things.", location="Remote", **kwargs):
        return Job.objects.create(
            recruiter=recruiter, title=title, company_name=company,
            description=description, location=location, **kwargs
        )

    @staticmethod
    def give_profile_skills(user, names):
        profile = user.student_profile
        for name in names:
            skill, _ = Skill.objects.get_or_create(name=name)
            profile.skills.add(skill)
        return profile


class ResumeFactory:
    @staticmethod
    def create_for(user):
        from apps.resumes.models import Resume

        return Resume.objects.create(
            user=user,
            file=SimpleUploadedFile("cv.pdf", b"%PDF-1.4 test resume"),
            original_name="cv.pdf",
        )


class RecruiterJobTests(JobAPITestCase):
    """1. Recruiter can create a job. 2. Edit own job. 3. Cannot modify others'."""

    def setUp(self):
        self.recruiter = self.make_recruiter("alice_rec")
        self.other = self.make_recruiter("bob_rec")

    def test_recruiter_can_create_job_with_skills_and_eligibility(self):
        self.login("alice_rec")
        response = self.client.post(
            "/api/jobs/",
            {
                "company_name": "Acme",
                "title": "Django Developer",
                "description": "Build APIs.",
                "location": "Bengaluru",
                "job_type": "full_time",
                "salary_range": "10-15 LPA",
                "education_required": "B.E./B.Tech in CS/IT",
                "min_cgpa": 7.5,
                "experience_required": "1-3 years",
                "application_deadline": "2026-12-31",
                "skills_required": ["Python", "Django", "REST API"],
                "preferred_skills": ["Docker"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        job = Job.objects.get(pk=response.data["id"])
        self.assertEqual(job.recruiter, self.recruiter)
        self.assertCountEqual(response.data["skills_required"], ["Python", "Django", "REST API"])
        self.assertIn("Docker", [s["name"] for s in response.data["preferred_skills"]])
        self.assertEqual(response.data["status"], "active")
        self.assertEqual(response.data["min_cgpa"], "7.50")
        self.assertEqual(response.data["education_required"], "B.E./B.Tech in CS/IT")
        self.assertEqual(str(response.data["application_deadline"]), "2026-12-31")
        self.assertTrue(Skill.objects.filter(name="Django").exists())

    def test_job_creates_skill_records_once(self):
        self.login("alice_rec")
        for title in ("Job A", "Job B"):
            self.client.post(
                "/api/jobs/",
                {"title": title, "description": "d", "location": "Remote",
                 "company_name": "Acme", "skills_required": ["python"]},
                format="json",
            )
        # Case-different names reuse the same catalog record (case-insensitive lookup)
        self.client.post(
            "/api/jobs/",
            {"title": "Job C", "description": "d", "location": "Remote",
             "company_name": "Acme", "skills_required": ["Python"]},
            format="json",
        )
        self.assertEqual(Skill.objects.filter(name__iexact="python").count(), 1)

    def test_recruiter_can_edit_own_job(self):
        self.make_job(self.recruiter, title="Old Title")
        self.login("alice_rec")
        response = self.client.patch(
            "/api/jobs/1/",
            {"title": "New Title", "is_active": False, "min_cgpa": 6.5},
            format="json",
        )
        job = Job.objects.get(title="New Title")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(job.is_active)
        self.assertEqual(job.status, "closed")
        self.assertEqual(float(job.min_cgpa), 6.5)

    def test_recruiter_can_update_skills_on_edit(self):
        job = self.make_job(self.recruiter)
        self.skills_for(job, ["Python", "Django"])
        self.login("alice_rec")
        self.client.put(
            "/api/jobs/%d/" % job.id,
            {"company_name": job.company_name, "title": job.title, "description": job.description,
             "location": job.location, "skills_required": ["Python", "Go"],
             "preferred_skills": ["Kubernetes"]},
            format="json",
        )
        job.refresh_from_db()
        names = set(job.required_skills.values_list("name", flat=True))
        self.assertEqual(names, {"Python", "Go"})

    def test_recruiter_cannot_modify_another_recruiters_job(self):
        foreign = self.make_job(self.other, title="Foreign Job")
        self.login("alice_rec")
        put = self.client.put(
            "/api/jobs/%d/" % foreign.id,
            {"title": "Hijacked", "company_name": "x", "description": "d", "location": "y"},
            format="json",
        )
        self.assertEqual(put.status_code, status.HTTP_403_FORBIDDEN, put.data)
        delete = self.client.delete("/api/jobs/%d/" % foreign.id)
        self.assertEqual(delete.status_code, status.HTTP_403_FORBIDDEN, delete.data)
        foreign.refresh_from_db()
        self.assertEqual(foreign.title, "Foreign Job")

    def test_recruiter_can_delete_own_job(self):
        job = self.make_job(self.recruiter)
        self.login("alice_rec")
        response = self.client.delete("/api/jobs/%d/" % job.id)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Job.objects.filter(pk=job.id).exists())

    def test_recruiter_can_close_job(self):
        job = self.make_job(self.recruiter, is_active=True)
        self.login("alice_rec")
        response = self.client.patch("/api/jobs/%d/" % job.id, {"is_active": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "closed")
        self.assertEqual(response.data["is_active"], False)

    def test_recruiter_jobs_endpoint_lists_own_jobs_only(self):
        self.make_job(self.recruiter, title="Mine")
        self.make_job(self.other, title="Theirs")
        self.login("alice_rec")
        for url in ("/api/recruiter/jobs/", "/api/jobs/mine/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK, url)
            titles = [j["title"] for j in response.data["results"]]
            self.assertEqual(titles, ["Mine"], url)


class StudentJobBrowsingTests(JobAPITestCase):
    """4. Student can view available jobs. 5. Student cannot modify jobs."""

    def setUp(self):
        self.recruiter = self.make_recruiter("carol_rec")
        self.student = self.make_student("student_view")
        job = self.make_job(
            self.recruiter, title="Backend Developer", description="APIs.",
            location="Hyderabad", job_type=Job.JobType.FULL_TIME,
            education_required="B.Tech", min_cgpa=6.0,
            experience_required="0-2 years",
        )
        self.skills_for(job, ["Python", "Django"], ["Redis"])

    def test_student_can_view_available_jobs(self):
        self.login("student_view")
        response = self.client.get("/api/jobs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data), 1)
        job = response.data[0]
        self.assertEqual(job["title"], "Backend Developer")
        self.assertCountEqual(job["skills_required"], ["Python", "Django"])
        self.assertIn("Python", [s["name"] for s in job["required_skills"]])
        self.assertEqual(job["education_required"], "B.Tech")
        self.assertEqual(job["min_cgpa"], "6.00")
        self.assertEqual(job["experience_required"], "0-2 years")
        self.assertIn("application_deadline", job)

    def test_closed_jobs_are_hidden_from_students(self):
        Job.objects.update(is_active=False)
        self.login("student_view")
        response = self.client.get("/api/jobs/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_student_can_filter_jobs(self):
        self.make_job(self.recruiter, title="Data Analyst", location="Remote",
                      job_type=Job.JobType.INTERNSHIP, description="SQL.")
        self.login("student_view")
        cases = [
            ({"job_type": "internship"}, "Data Analyst"),
            ({"location": "Hyderabad"}, "Backend Developer"),
            ({"role": "Backend"}, "Backend Developer"),
            ({"q": "Data"}, "Data Analyst"),
        ]
        for params, expected in cases:
            response = self.client.get("/api/jobs/", params)
            self.assertEqual(response.status_code, status.HTTP_200_OK, params)
            self.assertEqual([j["title"] for j in response.data], [expected], params)

    def test_job_listing_supports_pagination(self):
        for i in range(30):
            self.make_job(self.recruiter, title=f"Job {i}", location="X")
        self.login("student_view")
        response = self.client.get("/api/jobs/", {"page": 1, "page_size": 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertEqual(response.data["count"], 31)
        self.assertIsNotNone(response.data["next"])

    def test_unauthenticated_cannot_view_jobs(self):
        response = self.client.get("/api/jobs/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_student_cannot_create_job(self):
        self.login("student_view")
        response = self.client.post(
            "/api/jobs/",
            {"title": "Fake", "description": "x", "location": "x", "company_name": "x"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_cannot_modify_or_delete_job(self):
        job = Job.objects.first()
        self.login("student_view")
        put = self.client.put(
            "/api/jobs/%d/" % job.id,
            {"title": "Hijacked", "description": "x", "location": "x", "company_name": "x"},
            format="json",
        )
        self.assertEqual(put.status_code, status.HTTP_403_FORBIDDEN)
        patch = self.client.patch("/api/jobs/%d/" % job.id, {"is_active": False}, format="json")
        self.assertEqual(patch.status_code, status.HTTP_403_FORBIDDEN)
        delete = self.client.delete("/api/jobs/%d/" % job.id)
        self.assertEqual(delete.status_code, status.HTTP_403_FORBIDDEN)
        job.refresh_from_db()
        self.assertEqual(job.title, "Backend Developer")

    def test_student_cannot_access_recruiter_endpoints(self):
        self.login("student_view")
        for url in ("/api/recruiter/jobs/", "/api/recruiter/applications/", "/api/jobs/mine/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, url)


class SkillMatchingTests(JobAPITestCase):
    """6/7/8. Matching formula, case-insensitivity, missing skills, edge cases."""

    def setUp(self):
        self.recruiter = self.make_recruiter("dave_rec")
        self.student = self.make_student("match_student")
        self.job = self.make_job(self.recruiter, title="Backend Engineer")
        self.skills_for(
            self.job,
            ["Python", "Django", "REST API", "PostgreSQL", "Git", "Docker"],
        )
        self.give_profile_skills(
            self.student, ["Python", "Django", "PostgreSQL", "Git"]
        )

    def test_matching_percentage_formula(self):
        # 4 matched of 6 required = 66.67%
        self.login("match_student")
        response = self.client.get("/api/jobs/%d/match/" % self.job.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["matched"], ["django", "git", "postgresql", "python"])
        self.assertEqual(response.data["missing"], ["docker", "rest api"])
        self.assertEqual(response.data["coverage"], 66.7)
        self.assertEqual(response.data["score"], 67)

    def test_matching_is_case_insensitive(self):
        profile = self.student.student_profile
        profile.skills.clear()
        self.give_profile_skills(self.student, ["python", "DJANGO", "postGRESQL", "GIT"])
        self.login("match_student")
        response = self.client.get("/api/jobs/%d/match/" % self.job.id)
        self.assertEqual(response.data["coverage"], 66.7)
        self.assertEqual(response.data["missing"], ["docker", "rest api"])

    def test_missing_skills_returned_correctly(self):
        self.login("match_student")
        response = self.client.get("/api/jobs/%d/match/" % self.job.id)
        self.assertEqual(response.data["missing"], ["docker", "rest api"])
        for skill in response.data["matched"]:
            self.assertIn(skill, ["django", "git", "postgresql", "python"])

    def test_job_with_no_required_skills_gives_full_coverage(self):
        empty_job = self.make_job(self.recruiter, title="No Skill Job")
        self.login("match_student")
        response = self.client.get("/api/jobs/%d/match/" % empty_job.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["coverage"], 100.0)
        self.assertEqual(response.data["score"], 100)
        self.assertEqual(response.data["missing"], [])

    def test_student_with_no_skills_gets_zero_coverage(self):
        self.make_student("skillless_student")
        self.login("skillless_student")
        response = self.client.get("/api/jobs/%d/match/" % self.job.id)
        self.assertEqual(response.data["coverage"], 0.0)
        self.assertEqual(response.data["score"], 0)
        self.assertEqual(response.data["matched"], [])
        self.assertEqual(len(response.data["missing"]), 6)

    def test_duplicate_required_skills_are_counted_once(self):
        dup = self.make_job(self.recruiter, title="Dup Job")
        Skill.objects.get_or_create(name="Python")
        dup.required_skills.set(Skill.objects.filter(name="Python"))
        # adding a second identical requirement must not double count
        from .matching import skill_gap
        gap = skill_gap(["python"], ["Python", "PYTHON", "python"])
        self.assertEqual(gap["score"], 100)
        self.assertEqual(gap["coverage"], 100.0)

    def test_job_list_exposes_match_and_gaps_for_student(self):
        self.login("match_student")
        response = self.client.get("/api/jobs/")
        match = response.data[0]["match"]
        self.assertEqual(match["skill_gap"]["missing"], ["docker", "rest api"])
        self.assertEqual(match["skill_gap"]["coverage"], 66.7)
        self.assertEqual(match["score"], 67)

    def test_legacy_skill_gap_endpoint_still_works(self):
        self.login("match_student")
        response = self.client.post("/api/skill-gap/", {"job_id": self.job.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["missing"], ["docker", "rest api"])
        self.assertEqual(response.data["coverage"], 66.7)

    def test_match_endpoint_rejects_non_students(self):
        self.login("dave_rec")
        response = self.client.get("/api/jobs/%d/match/" % self.job.id)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ApplicationTests(JobAPITestCase):
    """9/10/11. Apply, duplicate prevention, and application privacy."""

    def setUp(self):
        self.recruiter = self.make_recruiter("erin_rec")
        self.student = self.make_student("applier")
        self.other_student = self.make_student("bystander")
        self.job = self.make_job(self.recruiter, title="API Engineer")
        self.skills_for(self.job, ["Python", "Django"])

    def test_student_can_apply_to_a_job(self):
        resume = ResumeFactory.create_for(self.student)
        self.login("applier")
        response = self.client.post(
            "/api/jobs/%d/apply/" % self.job.id, {"cover_note": "Hello"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        app = JobApplication.objects.get(pk=response.data["id"])
        self.assertEqual(app.student, self.student)
        self.assertEqual(app.job, self.job)
        self.assertEqual(app.status, JobApplication.Status.APPLIED)
        self.assertEqual(app.resume, resume)
        self.assertEqual(response.data["resume"]["original_name"], "cv.pdf")
        self.assertEqual(response.data["cover_note"], "Hello")

    def test_apply_without_resume_is_allowed(self):
        self.login("applier")
        response = self.client.post("/api/jobs/%d/apply/" % self.job.id, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIsNone(response.data["resume"])

    def test_duplicate_applications_are_rejected(self):
        self.login("applier")
        first = self.client.post("/api/jobs/%d/apply/" % self.job.id, {}, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        second = self.client.post("/api/jobs/%d/apply/" % self.job.id, {}, format="json")
        self.assertEqual(second.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(JobApplication.objects.filter(student=self.student, job=self.job).count(), 1)

    def test_apply_to_closed_job_rejected(self):
        self.job.is_active = False
        self.job.save()
        self.login("applier")
        response = self.client.post("/api/jobs/%d/apply/" % self.job.id, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_recruiter_cannot_apply(self):
        self.login("erin_rec")
        response = self.client.post("/api/jobs/%d/apply/" % self.job.id, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_student_can_view_only_their_own_applications(self):
        self.login("applier")
        self.client.post("/api/jobs/%d/apply/" % self.job.id, {}, format="json")
        self.client.credentials()
        # other student applies to a second job
        other_job = self.make_job(self.recruiter, title="Second Job")
        self.skills_for(other_job, ["Python"])
        self.login("bystander")
        self.client.post("/api/jobs/%d/apply/" % other_job.id, {}, format="json")

        # now view as the first student
        self.login("applier")
        response = self.client.get("/api/applications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["job_title"], "API Engineer")

        self.client.credentials()
        self.login("bystander")
        response = self.client.get("/api/applications/mine/")
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["job_title"], "Second Job")

    def test_recruiter_cannot_access_student_applications(self):
        self.client.post("/api/jobs/%d/apply/" % self.job.id, {}, format="json")
        self.login("erin_rec")
        for url in ("/api/applications/", "/api/applications/mine/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, url)

    def test_application_records_match_score(self):
        self.give_profile_skills(self.student, ["Python"])
        self.login("applier")
        response = self.client.post("/api/jobs/%d/apply/" % self.job.id, {}, format="json")
        self.assertEqual(response.data["match_score"], 50)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class RecruiterApplicationManagementTests(JobAPITestCase):
    """12/13/14. Recruiter views and manages applications for their own jobs."""

    def setUp(self):
        self.recruiter = self.make_recruiter("frank_rec")
        self.rival = self.make_recruiter("gina_rec")
        self.student = self.make_student("candidate_one")
        self.rival_student = self.make_student("candidate_two")
        self.job = self.make_job(self.recruiter, title="Frontend Engineer")
        self.rival_job = self.make_job(self.rival, title="Rival Job")
        self.skills_for(self.job, ["React"])

        self.login("candidate_one")
        self.client.post("/api/jobs/%d/apply/" % self.job.id, {"cover_note": "Hi"}, format="json")
        self.client.credentials()
        self.login("candidate_two")
        self.client.post("/api/jobs/%d/apply/" % self.rival_job.id, {}, format="json")
        self.client.credentials()

    def test_recruiter_can_view_applications_for_own_jobs(self):
        self.login("frank_rec")
        response = self.client.get("/api/recruiter/applications/")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertEqual(len(results), 1)
        row = results[0]
        self.assertEqual(row["job_title"], "Frontend Engineer")
        self.assertEqual(row["username"], "candidate_one")
        self.assertEqual(row["profile"]["full_name"], "Candidate_One")
        self.assertIn("match_score", row)
        self.assertIn("applied_at", row)

    def test_recruiter_applications_endpoint_filters_by_job_and_status(self):
        self.login("frank_rec")
        # no other jobs exist for this recruiter -> empty filter
        empty = self.client.get("/api/recruiter/applications/", {"job_id": 999})
        results = empty.data["results"] if isinstance(empty.data, dict) else empty.data
        self.assertEqual(results, [])
        filtered = self.client.get("/api/recruiter/applications/", {"job_id": self.job.id})
        results = filtered.data["results"] if isinstance(filtered.data, dict) else filtered.data
        self.assertEqual(len(results), 1)

    def test_recruiter_cannot_view_unrelated_applications(self):
        self.login("gina_rec")
        # rival's own jobs list only
        response = self.client.get("/api/recruiter/applications/")
        results = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertEqual([r["job_title"] for r in results], ["Rival Job"])

        # cannot open the other recruiter's job applicants
        applicants = self.client.get("/api/jobs/%d/applicants/" % self.job.id)
        self.assertEqual(applicants.status_code, status.HTTP_403_FORBIDDEN, applicants.data)

        # cannot change status of an application on someone else's job
        app = JobApplication.objects.get(job=self.job)
        patch = self.client.patch(
            "/api/applications/%d/status/" % app.id, {"status": "rejected"}, format="json"
        )
        self.assertEqual(patch.status_code, status.HTTP_403_FORBIDDEN)
        app.refresh_from_db()
        self.assertEqual(app.status, JobApplication.Status.APPLIED)

    def test_recruiter_can_update_application_status(self):
        app = JobApplication.objects.get(job=self.job)
        self.login("frank_rec")
        response = self.client.patch(
            "/api/applications/%d/status/" % app.id,
            {"status": "shortlisted", "remarks": "Calls next week."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        app.refresh_from_db()
        self.assertEqual(app.status, JobApplication.Status.SHORTLISTED)
        self.assertEqual(app.remarks, "Calls next week.")

    def test_recruiter_can_move_application_through_interview_status(self):
        app = JobApplication.objects.get(job=self.job)
        self.login("frank_rec")
        for step in ("interview", "selected"):
            response = self.client.patch(
                "/api/applications/%d/status/" % app.id, {"status": step}, format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            app.refresh_from_db()
            self.assertEqual(app.status, step)
        statuses = {c.value for c in JobApplication.Status}
        self.assertEqual(statuses, {"applied", "shortlisted", "interview", "selected", "rejected"})

    def test_invalid_status_rejected(self):
        app = JobApplication.objects.get(job=self.job)
        self.login("frank_rec")
        response = self.client.patch(
            "/api/applications/%d/status/" % app.id, {"status": "banana"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_applicants_endpoint_shows_candidate_details(self):
        self.login("frank_rec")
        response = self.client.get("/api/jobs/%d/applicants/" % self.job.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(len(response.data), 1)
        row = response.data[0]
        self.assertEqual(row["username"], "candidate_one")
        self.assertIn("profile", row)
        self.assertIn("cover_note", row)
        self.assertIn("remarks", row)

    def test_recruiter_can_download_applicants_resume(self):
        ResumeFactory.create_for(self.student)
        resume = self.student.resumes.first()
        JobApplication.objects.filter(job=self.job).update(resume=resume)

        self.login("frank_rec")
        allowed = self.client.get("/api/resumes/%d/download/" % resume.id)
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        self.assertIn("attachment", allowed["Content-Disposition"])

    def test_unrelated_recruiter_cannot_download_applicants_resume(self):
        ResumeFactory.create_for(self.student)
        resume = self.student.resumes.first()
        JobApplication.objects.filter(job=self.job).update(resume=resume)

        self.login("gina_rec")
        response = self.client.get("/api/resumes/%d/download/" % resume.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_other_student_cannot_download_someone_elses_resume(self):
        ResumeFactory.create_for(self.student)
        resume = self.student.resumes.first()
        self.login("candidate_two")
        response = self.client.get("/api/resumes/%d/download/" % resume.id)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_resume_owner_can_still_download(self):
        resume = ResumeFactory.create_for(self.student)
        self.login("candidate_one")
        response = self.client.get("/api/resumes/%d/download/" % resume.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class JobDetailTests(JobAPITestCase):
    def setUp(self):
        self.recruiter = self.make_recruiter("hank_rec")
        self.student = self.make_student("detail_student")
        self.job = self.make_job(self.recruiter, title="Detail Job")
        self.skills_for(self.job, ["Python", "Django"])

    def test_job_detail_includes_skills_eligibility_and_deadline(self):
        self.login("detail_student")
        response = self.client.get("/api/jobs/%d/" % self.job.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        data = response.data
        self.assertCountEqual(data["skills_required"], ["Python", "Django"])
        self.assertCountEqual([s["name"] for s in data["required_skills"]], ["Python", "Django"])
        self.assertIn("education_required", data)
        self.assertIn("min_cgpa", data)
        self.assertIn("experience_required", data)
        self.assertIn("application_deadline", data)
        self.assertEqual(data["status"], "active")

    def test_job_detail_includes_student_match(self):
        self.give_profile_skills(self.student, ["Python"])
        self.login("detail_student")
        response = self.client.get("/api/jobs/%d/" % self.job.id)
        self.assertEqual(response.data["match"]["score"], 50)
        self.assertEqual(response.data["match"]["skill_gap"]["missing"], ["django"])

    def test_unauthenticated_cannot_view_detail(self):
        response = self.client.get("/api/jobs/%d/" % self.job.id)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_job_returns_404(self):
        self.login("detail_student")
        response = self.client.get("/api/jobs/999999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)