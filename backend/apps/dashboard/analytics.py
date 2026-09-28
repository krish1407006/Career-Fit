"""Phase 8: student performance analytics, built only from data CareerAI stores.

Nothing in this module invents a score, a match or a recommendation. Every
number is either a value already written by Phases 1-7 or an aggregate over
those values:

* quiz scores come from ``QuizAttempt.score_percent``, which the Phase 4
  submit path computes server-side and never trusts the client for;
* interview scores come from ``InterviewSession.report_data["score"]`` written
  by the Phase 7 report;
* skill gaps reuse ``apps.jobs.matching.skill_gap`` -- the same function the
  job-match API uses, so the dashboard cannot disagree with the Jobs page.

The "no data" answer is always ``None``, never ``0``. A student who has never
attempted a quiz has no average, and showing them "0%" is a false claim about
their ability. The frontend renders ``None`` as an empty state.

Every function takes the authenticated student as its only argument. There is
no student id parameter, so there is no way for a caller to ask for somebody
else's dashboard.
"""

from django.db.models import Avg, Count, FloatField
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast

from apps.accounts.models import StudentProfile
from apps.assessments.models import Quiz, QuizAttempt
from apps.interviews.models import InterviewSession
from apps.jobs.matching import normalise, skill_gap
from apps.jobs.models import Job, JobApplication
from apps.jobs.views import candidate_skills_for
from apps.profiles.utils import profile_completion
from apps.resumes.models import Resume, ResumeAnalysis

# Rows the dashboard charts or lists. Bounded so a heavy account cannot turn one
# dashboard request into an unbounded read.
RECENT_LIMIT = 5
TREND_LIMIT = 20
GAP_SAMPLE_LIMIT = 25

# A quiz category below this average is worth a neutral nudge. Not a pass mark:
# PASS_THRESHOLD in apps.assessments is the actual pass/fail line.
WEAK_CATEGORY_PERCENT = 60


def _clean(values, limit=None):
    """Normalise a stored list-of-strings field into tidy, de-duplicated text."""
    seen = set()
    out = []
    for value in values or []:
        if isinstance(value, dict):
            value = value.get("name") or value.get("skill") or ""
        text = str(value or "").strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out[:limit] if limit else out


def _round(value, places=1):
    return None if value is None else round(value, places)


# ---------------------------------------------------------------- resume
def resume_summary(student):
    """Latest resume plus whatever analysis has been run against it."""
    resume = Resume.objects.filter(user=student).first()
    analysis = None
    if resume is not None:
        # Reverse one-to-one raises RelatedObjectDoesNotExist, which subclasses
        # AttributeError, so hasattr() is the correct test here.
        if hasattr(resume, "analysis"):
            analysis = resume.analysis
    completed = bool(analysis and analysis.status == ResumeAnalysis.Status.COMPLETED)
    return {
        "uploaded": resume is not None,
        "status": resume.status if resume else "none",
        "original_name": resume.original_name if resume else None,
        "uploaded_at": resume.uploaded_at if resume else None,
        "analysis_completed": completed,
        "analysis_status": analysis.status if analysis else None,
        # Phase 1-5 keys kept so existing consumers do not break.
        "score": analysis.score if analysis else None,
        "source": analysis.source if analysis else None,
        "skills_count": len(analysis.skills) if analysis else 0,
        "suggestions_count": len(analysis.suggestions) if analysis else 0,
        "detected_skills_count": len(analysis.detected_skills) if analysis else 0,
        "skill_gaps_count": len(analysis.skill_gaps) if analysis else 0,
        "strengths_count": len(analysis.strengths) if analysis else 0,
        "improvements_count": len(analysis.improvements) if analysis else 0,
        "recommended_roles_count": len(analysis.recommended_roles) if analysis else 0,
        # Phase 8: the actual lists, so the dashboard does not have to re-fetch.
        "detected_skills": _clean(analysis.detected_skills) if analysis else [],
        "skill_gaps": _clean(analysis.skill_gaps) if analysis else [],
        "improvements": _clean(analysis.improvements) if analysis else [],
        "strengths": _clean(analysis.strengths) if analysis else [],
        "recommended_roles": _clean(analysis.recommended_roles) if analysis else [],
    }


# ---------------------------------------------------------------- skills
def skills_insight(student):
    """Profile skills, resume-detected skills, and gaps from real matching.

    ``job_gaps`` is the union of the skills the jobs this student actually
    applied to require but that are absent from their profile, ranked by how
    many of those jobs ask for them. It reuses ``skill_gap`` rather than
    re-deriving coverage, so it can never disagree with the match percentage
    shown on the Jobs page.
    """
    profile = getattr(student, "student_profile", None)
    current = [s.name for s in profile.skills.all()] if profile else []

    analysis = (
        ResumeAnalysis.objects.filter(resume__user=student)
        .order_by("-resume__uploaded_at")
        .first()
    )
    detected = _clean(analysis.detected_skills) if analysis else []
    analysis_gaps = _clean(analysis.skill_gaps) if analysis else []

    candidate = candidate_skills_for(student)
    applied_jobs = list(
        JobApplication.objects.filter(student=student)
        .select_related("job")
        .prefetch_related("job__required_skills")
        .values_list("job", flat=True)[:GAP_SAMPLE_LIMIT]
    )
    jobs = list(
        Job.objects.filter(pk__in=applied_jobs).prefetch_related("required_skills")
    )
    # skill_gap() normalises to lower case so matching compares fairly, but a
    # dashboard should read "Kubernetes", not "kubernetes". Map each normalised
    # name back to the Skill row's own spelling for display. This is
    # presentation only -- the set of gaps is still exactly what skill_gap()
    # decided, so the count can never disagree with the Jobs page.
    display = {}
    for job in jobs:
        for skill in job.required_skills.all():
            display.setdefault(normalise(skill.name), skill.name)

    frequency = {}
    for job in jobs:
        gap = skill_gap(candidate, job.required_skills.all())
        for skill in gap["missing"]:
            key = display.get(skill, skill)
            frequency[key] = frequency.get(key, 0) + 1
    job_gaps = [
        {"skill": name, "required_by": count}
        for name, count in sorted(frequency.items(), key=lambda kv: (-kv[1], kv[0].lower()))
    ]

    return {
        "current": sorted(current, key=str.lower),
        "current_count": len(current),
        "detected": detected,
        "detected_count": len(detected),
        "gaps": analysis_gaps,
        "gaps_count": len(analysis_gaps),
        "job_gaps": job_gaps,
        "job_gap_count": len(job_gaps),
    }


# ---------------------------------------------------------------- quizzes
def quiz_performance(student):
    """Quiz statistics from submitted attempts only.

    An attempt is only counted once ``submitted_at`` is set, and attempts with
    no questions (``total == 0``) are excluded: Phase 4 stores ``score_percent
    = 0`` for those, and averaging a non-attempt in would understate a real
    score.
    """
    attempts = QuizAttempt.objects.filter(student=student).select_related("quiz")
    submitted = attempts.filter(submitted_at__isnull=False, total__gt=0)

    totals = submitted.aggregate(avg=Avg("score_percent"), n=Count("id"))
    average = totals["avg"]
    best = submitted.order_by("-score_percent").values_list(
        "score_percent", flat=True
    ).first()

    category_labels = dict(Quiz.Category.choices)
    by_category = [
        {
            "category": row["quiz__category"],
            "label": category_labels.get(row["quiz__category"], row["quiz__category"]),
            "attempts": row["n"],
            "average": _round(row["avg"]),
        }
        for row in submitted.values("quiz__category")
        .annotate(avg=Avg("score_percent"), n=Count("id"))
        .order_by("quiz__category")
    ]

    recent = [
        {
            "id": row.id,
            "quiz_id": row.quiz_id,
            "title": row.quiz.title,
            "category": row.quiz.category,
            "score_percent": row.score_percent,
            "correct_count": row.correct_count,
            "total": row.total,
            "submitted_at": row.submitted_at,
        }
        for row in submitted.order_by("-submitted_at")[:RECENT_LIMIT]
    ]

    return {
        "attempts_total": attempts.count(),
        "attempts_completed": totals["n"] or 0,
        "in_progress": attempts.filter(submitted_at__isnull=True).count(),
        # None, not 0: "no attempts" is not "an average of zero percent".
        "average_score": int(average) if average is not None else None,
        "average_score_exact": _round(average),
        "highest_score": best,
        "passed": submitted.filter(score_percent__gte=60).count(),
        "by_category": by_category,
        "recent_attempts": recent,
    }


# ---------------------------------------------------------------- interviews
def _report_score(session):
    """The stored 0-10 report score, or None when the report has no score."""
    value = (session.report_data or {}).get("score")
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _pluralized(n, noun):
    """\"1 attempt\" / \"3 attempts\" for report strings."""
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def interview_performance(student):
    """Interview statistics from Phase 7 sessions and their stored reports."""
    sessions = InterviewSession.objects.filter(student=student)
    completed = sessions.filter(status=InterviewSession.Status.COMPLETED)
    # A session with an empty report was completed but never scored; averaging
    # over it would drag the mean down for a missing number rather than a low one.
    scored = completed.exclude(report_data={})

    # The score lives inside the report JSON, so it is averaged in SQL rather
    # than by loading every report into Python. KeyTextTransform yields text and
    # the Cast makes it numeric: aggregating "report_data__score" directly makes
    # Django run the JSONField decoder over the resulting float and raise.
    # A session whose report has no score yields NULL, which Avg ignores.
    # Counted on the score itself, not on the row: a session can be completed
    # with a report that simply has no score, and that is not a scored result.
    totals = scored.annotate(
        score_value=Cast(KeyTextTransform("score", "report_data"), FloatField())
    ).aggregate(avg=Avg("score_value"), n=Count("score_value"))
    average = totals["avg"]

    recent = []
    for session in completed.order_by("-completed_at", "-created_at")[:RECENT_LIMIT]:
        report = session.report_data or {}
        recent.append({
            "id": session.id,
            "position": session.position,
            "mode": session.mode,
            "score": _report_score(session),
            "summary": report.get("summary", ""),
            "areas_to_improve": _clean(report.get("areas_to_improve")),
            "topics_to_prepare": _clean(report.get("topics_to_prepare")),
            "questions_answered": report.get("questions_answered"),
            "completed_at": session.completed_at or session.created_at,
        })

    latest = recent[0] if recent else None
    # Drives "Resume interview" instead of "Start interview".
    active = sessions.filter(status=InterviewSession.Status.IN_PROGRESS).first()

    return {
        "total": sessions.count(),
        "completed": completed.count(),
        "in_progress": sessions.filter(
            status=InterviewSession.Status.IN_PROGRESS
        ).count(),
        "cancelled": sessions.filter(status=InterviewSession.Status.CANCELLED).count(),
        "average_score": _round(average),
        "scored_interviews": totals["n"] or 0,
        "latest": latest,
        "recent_interviews": recent,
        "active_session": (
            {
                "id": active.id,
                "position": active.position,
                "state": active.state,
                "question_index": active.question_index,
                "total_questions": active.total_questions,
            }
            if active else None
        ),
    }


# ---------------------------------------------------------------- applications
def application_summary(student):
    """Application counts using only the statuses the model actually defines."""
    apps = JobApplication.objects.filter(student=student)
    totals = apps.values("status").annotate(n=Count("id"))
    by_status = {row["status"]: row["n"] for row in totals}

    recent = [
        {
            "id": row.id,
            "job_id": row.job_id,
            "title": row.job.title,
            "company": row.job.company_name,
            "location": row.job.location,
            "status": row.status,
            "match_score": row.match_score,
            "applied_at": row.applied_at,
        }
        for row in apps.select_related("job").order_by("-applied_at")[:RECENT_LIMIT]
    ]

    return {
        "total": apps.count(),
        "by_status": by_status,
        "best_match": apps.order_by("-match_score").values_list(
            "match_score", flat=True
        ).first(),
        "recent": recent,
    }


# ---------------------------------------------------------------- trend
def performance_trend(student):
    """One chronological list of real scored results, quizzes and interviews.

    Quizzes report a percentage; interviews report a score out of 10. Both are
    normalised to 0-100 so a single axis is honest, and the raw pair is kept on
    every point so the UI can label it precisely. No point is ever invented:
    only submitted attempts and completed interviews with a stored score appear.
    """
    points = []

    quiz_points = (
        QuizAttempt.objects.filter(student=student, submitted_at__isnull=False, total__gt=0)
        .select_related("quiz")
        .order_by("-submitted_at")[:TREND_LIMIT]
    )
    for attempt in quiz_points:
        points.append({
            "kind": "quiz",
            "label": attempt.quiz.title,
            "category": attempt.quiz.category,
            "score": attempt.score_percent,
            "raw_score": attempt.score_percent,
            "max_score": 100,
            "date": attempt.submitted_at,
        })

    session_points = (
        InterviewSession.objects.filter(student=student, status=InterviewSession.Status.COMPLETED)
        .exclude(report_data={})
        .order_by("-completed_at", "-created_at")[:TREND_LIMIT]
    )
    for session in session_points:
        raw = _report_score(session)
        if raw is None:
            continue
        points.append({
            "kind": "interview",
            "label": session.position,
            "category": None,
            "score": int(round(raw * 10)),
            "raw_score": raw,
            "max_score": 10,
            "date": session.completed_at or session.created_at,
        })

    points.sort(key=lambda p: p["date"])
    return points[-TREND_LIMIT:]


# ---------------------------------------------------------------- insights
def preparation_insights(resume, skills, quizzes, interviews, applications):
    """Neutral, data-backed nudges.

    Every entry names the stored figure it came from, and the wording
    deliberately suggests practice rather than asserting ability -- the data
    shows one account's recent attempts, not a person's ceiling.
    """
    insights = []

    if not resume["uploaded"]:
        insights.append({
            "id": "no-resume",
            "tone": "action",
            "title": "No resume uploaded yet",
            "detail": "Upload a resume to unlock skill insights and job matching.",
            "link": "/student/profile",
            "link_label": "Upload resume",
        })
    elif not resume["analysis_completed"]:
        insights.append({
            "id": "resume-not-analyzed",
            "tone": "action",
            "title": "Resume uploaded but not analyzed",
            "detail": "Analyze your resume to see your skill insights.",
            "link": "/student/profile",
            "link_label": "Analyze resume",
        })

    if resume["skill_gaps"]:
        insights.append({
            "id": "resume-gaps",
            "tone": "info",
            "title": f"{_pluralized(len(resume['skill_gaps']), 'skill gap')} flagged in your resume",
            "detail": f"Your analysis flagged: {', '.join(resume['skill_gaps'][:6])}"
                      + ("." if len(resume["skill_gaps"]) <= 6 else " and more."),
            "link": "/student/profile",
            "link_label": "View analysis",
        })

    if skills["job_gaps"]:
        top = skills["job_gaps"][:5]
        detail = ", ".join(
            f"{item['skill']} (asked for by {item['required_by']} of your applications)"
            for item in top
        )
        insights.append({
            "id": "job-skill-gaps",
            "tone": "info",
            "title": "Skills your target jobs ask for that are not on your profile",
            "detail": detail + ("." if len(skills["job_gaps"]) <= 5 else ", and more."),
            "link": "/student/profile",
            "link_label": "Add skills",
        })

    weak = [
        row for row in quizzes["by_category"]
        if row["average"] is not None and row["average"] < WEAK_CATEGORY_PERCENT
    ]
    if weak:
        worst = min(weak, key=lambda row: row["average"])
        insights.append({
            "id": "weak-quiz-category",
            "tone": "info",
            "title": f"Consider practising {worst['label']}",
            "detail": f"Your average across {_pluralized(worst['attempts'], worst['label'].lower() + ' attempt')} "
                      f"is {worst['average']:.0f}%, the lowest of your categories.",
            "link": "/student/quizzes",
            "link_label": "Browse quizzes",
        })

    for interview in interviews["recent_interviews"][:1]:
        if interview["areas_to_improve"]:
            insights.append({
                "id": "interview-areas",
                "tone": "info",
                "title": "Consider reviewing the areas flagged in your latest interview",
                "detail": ", ".join(interview["areas_to_improve"][:5]) + ".",
                "link": "/student/interview",
                "link_label": "Practise interview",
            })
        if interview["topics_to_prepare"]:
            insights.append({
                "id": "interview-topics",
                "tone": "info",
                "title": "Topics to prepare from your latest interview",
                "detail": ", ".join(interview["topics_to_prepare"][:5]) + ".",
                "link": "/student/interview",
                "link_label": "Practise interview",
            })

    if applications["total"] == 0:
        insights.append({
            "id": "no-applications",
            "tone": "action",
            "title": "No applications yet",
            "detail": "Browse open jobs to find roles matching your current skills.",
            "link": "/student/jobs",
            "link_label": "Browse jobs",
        })

    return insights


# ---------------------------------------------------------------- assembly
def student_analytics(student):
    """The full Phase 8 payload for one authenticated student."""
    profile, _ = StudentProfile.objects.get_or_create(user=student)
    resume = resume_summary(student)
    skills = skills_insight(student)
    quizzes = quiz_performance(student)
    interviews = interview_performance(student)
    applications = application_summary(student)

    return {
        "student": {
            "id": student.pk,
            "username": student.username,
            "full_name": profile.full_name or student.username,
        },
        "overview": {
            "resume_uploaded": resume["uploaded"],
            "resume_analyzed": resume["analysis_completed"],
            "skills_count": skills["current_count"],
            "skill_gaps_count": resume["skill_gaps_count"],
            "jobs_available": Job.objects.filter(is_active=True).count(),
            "applications": applications["total"],
            "quiz_attempts": quizzes["attempts_completed"],
            "average_quiz_score": quizzes["average_score"],
            "interviews_completed": interviews["completed"],
            "average_interview_score": interviews["average_score"],
        },
        "profile": {
            "completion": profile_completion(profile),
            "skills_count": skills["current_count"],
            "projects_count": profile.projects.count(),
            "resume_uploaded": resume["uploaded"],
        },
        "resume": resume,
        "skills": skills,
        "quiz_performance": quizzes,
        "interview_performance": interviews,
        "applications": applications,
        "performance_trend": performance_trend(student),
        "preparation_insights": preparation_insights(
            resume, skills, quizzes, interviews, applications
        ),
    }
