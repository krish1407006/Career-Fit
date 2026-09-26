"""Resume-analysis orchestration for the resumes app.

Views stay thin: they call :func:`run_resume_analysis`, which

1. extracts text with the existing :mod:`apps.resumes.text_extraction` service,
2. validates that meaningful text was found (no OCR in this phase),
3. calls the AI service layer (:mod:`apps.ai.resume_analyzer`) - no provider
   SDK or HTTP call is made from here or from the views,
4. merges AI-detected skills into the existing ``Skill`` catalogue and the
   student's profile **without ever removing or renaming manual skills**,
5. reuses the existing skill-matching logic (:mod:`apps.jobs.matching`) for
   job-role relevance,
6. stores the validated, structured result on ``ResumeAnalysis``.

No external AI call is made by this module itself; failures are surfaced as
``AnalysisError`` with a student-safe message.
"""

import logging

from django.db import transaction

from apps.ai.errors import AiError, AiParseError, ProviderUnavailable
from apps.ai.resume_analyzer import analyze_resume_text
from apps.accounts.models import StudentProfile
from apps.jobs.matching import match_job_to_student, normalise
from apps.jobs.models import Job, Skill

from .models import Resume, ResumeAnalysis
from .text_extraction import extract_text_from_resume

logger = logging.getLogger(__name__)

MAX_SYNCED_SKILLS = 40


class AnalysisError(Exception):
    """Analysis could not be completed; message is safe to show a student."""

    def __init__(self, message, *, code="analysis_failed"):
        super().__init__(message)
        self.message = message
        self.code = code


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------
def extract_resume_text(resume):
    """Extract plain text from a stored resume file.

    Reuses the existing extraction service (PDF/DOCX/TXT). No OCR: a scanned
    image PDF yields a clear, user-facing error instead.
    """
    if not resume or not resume.file:
        raise AnalysisError("This resume has no file to read. Upload a PDF and try again.",
                            code="no_file")
    try:
        resume.file.open("rb")
        try:
            text = extract_text_from_resume(resume.file)
        finally:
            resume.file.close()
    except AnalysisError:
        raise
    except Exception as exc:  # noqa: BLE001 - never leak parser internals
        logger.warning("Resume text extraction failed for resume %s: %s",
                       resume.pk, exc.__class__.__name__)
        raise AnalysisError(
            "We could not read this PDF. Make sure it is a text-based PDF "
            "(not a scanned image) and try again.",
            code="extraction_failed",
        )
    if not text or not text.strip():
        raise AnalysisError(
            "No readable text was found in this PDF. If it is a scanned image, "
            "export a text-based PDF and upload it again.",
            code="empty_text",
        )
    return text


# ---------------------------------------------------------------------------
# Skill integration
# ---------------------------------------------------------------------------
def ai_detected_skill_names(user):
    """Canonical AI-detected skill names from the user's latest analysis."""
    analysis = (
        ResumeAnalysis.objects
        .filter(resume__user=user, status=ResumeAnalysis.Status.COMPLETED)
        .order_by("-resume__uploaded_at", "-id")
        .first()
    )
    if not analysis:
        return []
    return list(analysis.detected_skills or analysis.skills or [])


def skill_source_map(user):
    """Map normalised skill name -> "ai" | "manual" for the student's skills.

    Keeps AI-detected skills distinguishable from manually entered ones without
    duplicating or mutating the shared ``Skill`` catalogue: a skill counts as
    AI-detected when the latest completed analysis reported it.
    """
    ai_names = {normalise(n) for n in ai_detected_skill_names(user) if n}
    return ai_names


def sync_detected_skills(user, names):
    """Add AI-detected skills to the catalogue and the student's profile.

    Only ever adds: existing manual skills, their names and categories are left
    untouched, and nothing is removed. Returns the list of linked ``Skill``
    records.
    """
    linked = []
    seen = set()
    for raw in list(names or [])[:MAX_SYNCED_SKILLS]:
        name = str(raw).strip()
        if len(name) < 2 or len(name) > 120:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        skill = Skill.objects.filter(name__iexact=name).first()
        if skill is None:
            skill = Skill.objects.create(name=name)
        linked.append(skill)

    if linked:
        profile, _ = StudentProfile.objects.get_or_create(user=user)
        # add() is additive: manual skills are preserved.
        profile.skills.add(*linked)
    return linked


# ---------------------------------------------------------------------------
# Job relevance (reuses the existing matching algorithm)
# ---------------------------------------------------------------------------
def job_relevance_for(user, analysis, job=None):
    """Skill-match the analysed resume against a job, using apps.jobs.matching.

    ``job`` may be a ``Job`` instance or an id. Returns {} when no job applies.
    """
    if job is None:
        return {}
    if not isinstance(job, Job):
        job = Job.objects.prefetch_related("required_skills", "preferred_skills")\
            .filter(pk=job).first()
        if job is None:
            return {}
    candidate_skills = list(analysis.detected_skills or analysis.skills or [])
    profile = getattr(user, "student_profile", None)
    if profile:
        candidate_skills.extend(s.name for s in profile.skills.all())
    preferred_roles = list(profile.preferred_roles) if profile else []
    match = match_job_to_student(job, candidate_skills, preferred_roles)
    return {
        "job_id": job.id,
        "job_title": job.title,
        "company_name": job.company_name,
        "match_score": match["score"],
        "matched_skills": match["skill_gap"]["matched"],
        "missing_skills": match["skill_gap"]["missing"],
        "coverage": match["skill_gap"]["coverage"],
        "role_hint": match.get("role_hint", False),
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def run_resume_analysis(resume, *, user=None, job=None, require_ai=False):
    """Analyse ``resume`` and persist a structured ``ResumeAnalysis``.

    ``user`` defaults to the resume owner. Raises :class:`AnalysisError` with a
    student-safe message for extraction problems, missing AI configuration or
    unusable AI output.

    Failures are persisted (status ``failed``) *outside* the transaction that
    stores a successful result, so a failure is never rolled back and the
    student can see what went wrong.
    """
    owner = user or resume.user
    analysis, _ = ResumeAnalysis.objects.get_or_create(
        resume=resume, defaults={"status": ResumeAnalysis.Status.PENDING}
    )
    analysis.status = ResumeAnalysis.Status.PENDING
    analysis.error_message = ""
    analysis.notice = ""
    analysis.save(update_fields=["status", "error_message", "notice", "updated_at"])

    try:
        text = extract_resume_text(resume)
    except AnalysisError as exc:
        _mark_failed(resume, analysis, exc.message)
        raise

    try:
        result = analyze_resume_text(text, require_ai=require_ai)
    except AiError as exc:
        message = _safe_ai_message(exc)
        _mark_failed(resume, analysis, message)
        raise AnalysisError(message, code="ai_unavailable") from None
    except Exception:  # noqa: BLE001 - unknown failure, no traceback to client
        logger.exception("Unexpected resume analysis failure for resume %s", resume.pk)
        message = "Resume analysis failed unexpectedly. Please try again."
        _mark_failed(resume, analysis, message)
        raise AnalysisError(message, code="analysis_failed") from None

    with transaction.atomic():
        detected = result["detected_skills"]
        linked = sync_detected_skills(owner, detected)

        analysis.status = ResumeAnalysis.Status.COMPLETED
        analysis.extracted_text = text[:20000]
        analysis.detected_skills = detected
        analysis.skills = [s.name for s in linked] or detected
        analysis.summary = result["summary"]
        analysis.strengths = result["strengths"]
        analysis.skill_gaps = result["skill_gaps"]
        analysis.improvements = result["improvements"]
        analysis.recommended_roles = result["recommended_roles"]
        analysis.education = result["education"]
        analysis.experience = result["experience"]
        analysis.suggestions = result["improvements"]
        analysis.score = result["score"]
        analysis.source = result["source"]
        analysis.provider = result.get("provider", "")
        analysis.notice = result.get("notice", "")
        analysis.error_message = ""
        analysis.raw = result.get("raw", {}) if isinstance(result.get("raw"), dict) else {}
        analysis.job_relevance = job_relevance_for(owner, analysis, job)
        analysis.save()

        resume.status = Resume.Status.ANALYZED
        resume.error_message = ""
        resume.save(update_fields=["status", "error_message", "updated_at"])

    return analysis


def _mark_failed(resume, analysis, message):
    analysis.status = ResumeAnalysis.Status.FAILED
    analysis.error_message = message
    analysis.save(update_fields=["status", "error_message", "updated_at"])
    resume.status = Resume.Status.FAILED
    resume.error_message = message
    resume.save(update_fields=["status", "error_message", "updated_at"])


def _safe_ai_message(exc):
    """Map a typed AI error to a fixed, student-facing message.

    Provider text is never echoed back verbatim, so API keys, endpoint URLs,
    HTTP details and internal exception class names cannot leak to a client.
    The original error is recorded server-side by the caller instead.
    """
    if isinstance(exc, ProviderUnavailable) and "not configured" in str(exc).lower():
        return (
            "AI resume analysis is not configured on the server. "
            "Please try again later or contact your administrator."
        )
    if isinstance(exc, AiParseError):
        return (
            "The AI service returned a response we could not read. "
            "Please try again in a few minutes."
        )
    return "The AI service is unavailable right now. Please try again in a few minutes."

