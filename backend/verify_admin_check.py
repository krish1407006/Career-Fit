"""Temporary end-to-end check of the admin capabilities against the real DB.

Runs the full matrix an admin would exercise, then removes everything it
created. Delete this file once it has been run.
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from rest_framework.test import APIClient  # noqa: E402

from apps.accounts.models import StudentProfile, User  # noqa: E402
from apps.assessments.models import Question, Quiz, QuizAttempt  # noqa: E402
from apps.interviews.models import InterviewSession, InterviewTurn  # noqa: E402
from apps.jobs.models import Job, JobApplication  # noqa: E402
from apps.resumes.models import Resume, ResumeAnalysis  # noqa: E402

SUFFIX = "_admincheck"
STUDENT = f"checker_student{SUFFIX}"
OTHER = f"checker_other{SUFFIX}"
RECRUITER = f"checker_hr{SUFFIX}"
ADMIN = f"checker_admin{SUFFIX}"
PASSWORD = "Check@12345"

ok = fail = 0


def check(label, condition, extra=""):
    global ok, fail
    if condition:
        ok += 1
        print(f"  PASS  {label} {extra}")
    else:
        fail += 1
        print(f"  FAIL  {label} {extra}")


def purge():
    """Remove anything a previous run left behind, newest first."""
    for user in User.objects.filter(username__endswith=SUFFIX):
        user.delete()
    Job.objects.filter(company_name="Check Co").delete()


def client_for(username, role):
    user = User.objects.create_user(
        username=username, email=f"{username}@check.local", password=PASSWORD, role=role
    )
    if role == User.Role.STUDENT:
        StudentProfile.objects.create(user=user, full_name="Check Student")
    client = APIClient()
    client.force_authenticate(user)
    # APIClient defaults to host "testserver", which is not in ALLOWED_HOSTS.
    client.defaults["HTTP_HOST"] = "127.0.0.1"
    return user, client


def main():
    purge()
    admin, admin_c = client_for(ADMIN, User.Role.ADMIN)
    student, student_c = client_for(STUDENT, User.Role.STUDENT)
    other, _ = client_for(OTHER, User.Role.STUDENT)
    recruiter, recruiter_c = client_for(RECRUITER, User.Role.RECRUITER)

    job = Job.objects.create(
        recruiter=recruiter, company_name="Check Co", title="SDE",
        description="Build", location="Remote",
    )
    application = JobApplication.objects.create(student=student, job=job, match_score=71)
    resume = Resume.objects.create(
        user=student, original_name="check.pdf", file=f"resumes/{student.id}/check.pdf"
    )
    ResumeAnalysis.objects.create(
        resume=resume, status=ResumeAnalysis.Status.COMPLETED,
        detected_skills=["Python"], score=64, source="offline",
    )
    quiz = Quiz.objects.create(title="Check quiz", duration_minutes=5)
    question = Question.objects.create(quiz=quiz, text="1+1?", options=["1", "2"], correct_index=1)
    attempt = QuizAttempt.objects.create(
        student=student, quiz=quiz, status=QuizAttempt.Status.COMPLETED,
        correct_count=1, total=1, score_percent=100,
        answers={str(question.id): 1}, submitted_at="2026-01-01T00:00:00Z",
    )
    session = InterviewSession.objects.create(
        student=student, position="SDE", status=InterviewSession.Status.COMPLETED,
        report_data={"score": 7, "summary": "ok"},
    )
    for kind in (InterviewTurn.Kind.QUESTION, InterviewTurn.Kind.ANSWER):
        InterviewTurn.objects.create(session=session, kind=kind, content=f"{kind} text")

    print("\n1. Admin can use the student experience")
    r = admin_c.get("/api/dashboard/student/")
    check("student dashboard", r.status_code == 200 and "resume" in r.data, r.status_code)
    r = admin_c.get("/api/dashboard/")
    check("role-aware dashboard stays admin", r.status_code == 200 and "colleges" in r.data)
    r = admin_c.get("/api/profile/")
    check("own student profile", r.status_code == 200 and r.data["profile"]["full_name"] == "")
    r = admin_c.put(
        "/api/auth/me/", {"profile": {"full_name": "Check Admin"}}, format="json"
    )
    check(
        "edits own student profile, stays admin",
        r.status_code == 200 and admin.is_admin_role and admin.role == User.Role.ADMIN,
    )
    r = admin_c.post(f"/api/jobs/{job.id}/apply/", {}, format="json")
    check("can apply to a job", r.status_code == 201, r.status_code)
    r = admin_c.get("/api/applications/mine/")
    rows = r.data["results"]
    check("application is the admin's own", r.status_code == 200 and len(rows) == 1
          and rows[0]["job_id"] == job.id, rows)
    r = admin_c.get("/api/applications/mine/?job=%d" % job.id)
    check("admin application visible on its job", r.status_code == 200)
    r = student_c.get("/api/applications/mine/")
    check("student's application untouched",
          r.status_code == 200 and r.data["results"][0]["id"] == application.id)
    r = admin_c.post("/api/quizzes/%d/start/" % quiz.id, {}, format="json")
    check("can start a quiz", r.status_code == 200, r.status_code)
    admin_attempt_id = r.data["attempt_id"]
    r = admin_c.post(
        "/api/quizzes/%d/submit/" % quiz.id,
        {"answers": {str(question.id): 1}}, format="json",
    )
    check("can submit a quiz", r.status_code == 200 and r.data["score_percent"] == 100,
          r.status_code)
    r = admin_c.post(
        "/api/interviews/start/",
        {"position": "SDE", "total_questions": 2, "mode": "text"}, format="json",
    )
    check("can start a mock interview", r.status_code in (200, 201), r.status_code)
    admin_session_id = r.data["id"]
    r = admin_c.post(f"/api/interviews/{admin_session_id}/complete/", {}, format="json")
    check("can complete a mock interview", r.status_code == 200
          and "report" in r.data, r.status_code)

    print("\n2. Admin read-only inspection screens")
    r = admin_c.get("/api/resumes/admin/")
    check("resumes list", r.status_code == 200 and len(r.data) == 1
          and r.data[0]["student_username"] == student.username, r.status_code)
    r = admin_c.get(f"/api/resumes/admin/?student={other.id}")
    check("resumes filter by student", r.status_code == 200 and r.data == [])
    r = admin_c.get(f"/api/resumes/admin/{resume.id}/analysis/")
    check("resume analysis", r.status_code == 200 and r.data["detected_skills"] == ["Python"],
          r.status_code)
    r = admin_c.get("/api/admin/applications/")
    check("applications list", r.status_code == 200
          and r.data["count"] == 2, r.data.get("count"))
    r = admin_c.get(f"/api/admin/applications/?student={student.id}")
    check("applications filter by student", r.status_code == 200
          and r.data["count"] == 1, r.data.get("count"))
    r = admin_c.get("/api/interviews/admin/")
    check("interviews list", r.status_code == 200 and len(r.data) == 2, r.status_code)
    by_id = {row["id"]: row for row in r.data}
    check("interview answer count", by_id[session.id]["answers"] == 1,
          by_id[session.id]["answers"])
    check("interview report score", by_id[session.id]["report_score"] == 7)
    r = admin_c.get(f"/api/interviews/{session.id}/")
    check("any transcript readable", r.status_code == 200 and len(r.data["turns"]) == 2,
          r.status_code)
    r = admin_c.get(f"/api/resumes/{resume.id}/download/")
    check("admin can download a resume", r.status_code == 200, r.status_code)
    r = admin_c.get("/api/quiz-attempts/")
    check("attempt list names the student", r.status_code == 200
          and {row["student_username"] for row in r.data} == {student.username, ADMIN},
          [row["student_username"] for row in r.data])
    r = admin_c.get(f"/api/quiz-attempts/{attempt.id}/")
    check("attempt review", r.status_code == 200
          and r.data["per_question"][0]["is_correct"] is True, r.status_code)
    r = admin_c.get("/api/quiz-attempts/?status=completed")
    check("attempt filter by status", r.status_code == 200 and len(r.data) == 2, r.status_code)

    print("\n3. Inspection screens are read only")
    for url in ("/api/resumes/admin/", "/api/admin/applications/",
                "/api/interviews/admin/", "/api/quiz-attempts/"):
        for method in ("post", "put", "patch", "delete"):
            response = getattr(admin_c, method)(url, {}, format="json")
            check(f"{method.upper()} {url}", response.status_code == 405,
                  response.status_code)

    print("\n4. Students and recruiters are locked out")
    for label, c in (("student", student_c), ("recruiter", recruiter_c)):
        for url in ("/api/resumes/admin/", "/api/admin/applications/",
                    "/api/interviews/admin/", "/api/quiz-attempts/"):
            r = c.get(url)
            check(f"{label} blocked from {url}", r.status_code == 403, r.status_code)
        r = c.get(f"/api/resumes/{resume.id}/")
        check(f"{label} cannot read a foreign resume", r.status_code == 404, r.status_code)
        r = c.get("/api/dashboard/student/" if label == "recruiter"
                  else "/api/dashboard/recruiter/")
        check(f"{label} blocked from the other dashboard", r.status_code == 403, r.status_code)

    print(f"\n{ok} passed, {fail} failed")
    return 1 if fail else 0


if __name__ == "__main__":
    try:
        code = main()
    finally:
        purge()
    raise SystemExit(code)
