"""High-level AI service functions used by feature apps.

Feature apps never import provider SDKs; they call these functions, which route
to the configured external provider or fall back to deterministic offline
logic when no provider/key is set (or the AI call fails and AI_REQUIRED=False).
"""

import logging

from django.conf import settings

from .errors import AiError
from . import interview_service, providers, resume_analyzer

logger = logging.getLogger(__name__)

RESUME_ANALYSIS_SYSTEM = "(superseded by apps.ai.resume_analyzer.SYSTEM_PROMPT)"


def analyze_resume(text):
    """Legacy flat resume analysis: {skills, summary, education, experience, score, suggestions}.

    Thin wrapper over :mod:`apps.ai.resume_analyzer`, which owns the actual
    prompt, provider call and output validation. New code should call
    :func:`apps.ai.resume_analyzer.analyze_resume_text` directly to get the
    structured Phase 6 payload.
    """
    try:
        result = resume_analyzer.analyze_resume_text(text or "")
    except (AiError, resume_analyzer.AiParseError) as exc:
        logger.warning("Resume AI analysis failed (%s); falling back to offline.", exc.__class__.__name__)
        if settings.AI_REQUIRED:
            raise
        result = resume_analyzer._offline_analysis(  # noqa: SLF001 - same package
            text or "", notice=resume_analyzer.OFFLINE_FALLBACK_NOTICE
        )
    return {
        "skills": result["detected_skills"],
        "summary": result["summary"],
        "education": result["education"],
        "experience": result["experience"],
        "score": result["score"],
        "suggestions": result["improvements"],
        "source": result["source"],
    }



INTERVIEW_QUESTION_SYSTEM = (
    "(superseded by apps.ai.interview_service.QUESTION_SYSTEM)"
)


def next_interview_question(position, transcript, index, total):
    """Return the next interview question string for ``position`` at stage ``index``/``total``.

    Phase 1-6 flat helper. Thin wrapper over
    :mod:`apps.ai.interview_service`, which owns the contextual/adaptive prompt
    and validation. New code should call
    :func:`apps.ai.interview_service.generate_question`.
    """
    payload = interview_service.generate_question(
        context="", position=position, transcript=transcript, index=index, total=total
    )
    return payload["question"]


INTERVIEW_EVALUATE_SYSTEM = (
    "(superseded by apps.ai.interview_service.EVALUATE_SYSTEM)"
)


def evaluate_interview_answer(position, question, answer):
    """Evaluate a candidate answer -> {score, feedback, suggestions, source}.

    Phase 1-6 flat helper. Delegates to
    :mod:`apps.ai.interview_service` and maps the structured Phase 7 result back
    onto the legacy key names so existing consumers keep working.
    """
    result = interview_service.evaluate_answer(
        context="", position=position, question=question, answer=answer
    )
    return {
        "score": (result.get("score") or 0) * 10,
        "feedback": result.get("feedback", ""),
        "suggestions": " ".join(result.get("improvements") or []),
        "source": result.get("source", "offline"),
    }


INTERVIEW_SUMMARY_SYSTEM = (
    "(superseded by apps.ai.interview_service.REPORT_SYSTEM)"
)


def summarize_interview(position, transcript):
    """Produce a final report string for a completed interview (Phase 1-6 helper)."""
    rows = list(transcript)
    pairs = []
    current = None
    for row in rows:
        kind = row.get("kind")
        if kind == "question":
            current = {"question": row.get("content", ""), "answer": "",
                       "score": None, "feedback": ""}
            pairs.append(current)
        elif kind == "answer" and current is not None:
            current["answer"] = row.get("content", "")
        elif kind == "evaluation" and current is not None:
            current["score"] = row.get("score")
            current["feedback"] = row.get("content", "")
    report = interview_service.build_report(
        context="", position=position, per_question=pairs
    )
    return report.get("summary", "")


def _assistant_user_rows(transcript):
    """Return human-readable transcript rows to feed into a prompt."""
    return [
        {"role": t["role"], "content": t.get("content", "")}
        for t in transcript
        if t.get("content")
    ]