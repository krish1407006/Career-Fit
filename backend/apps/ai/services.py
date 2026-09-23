"""High-level AI service functions used by feature apps.

Feature apps never import provider SDKs; they call these functions, which route
to the configured external provider or fall back to deterministic offline
logic when no provider/key is set (or the AI call fails and AI_REQUIRED=False).
"""

import logging

from django.conf import settings

from .errors import AiError
from .extraction import build_offline_analysis
from .interview_offline import offline_evaluate, offline_question, offline_summary
from . import providers

logger = logging.getLogger(__name__)

RESUME_ANALYSIS_SYSTEM = """You are an expert technical recruiter. Analyse the \
candidate's resume text and return ONLY valid JSON with this exact shape:

{
  "skills": ["skill1", "skill2"],
  "summary": "one-paragraph professional summary of the candidate",
  "education": [{"degree": "...", "institution": "...", "year": "..."}],
  "experience": [{"role": "...", "org": "...", "duration": "...", "points": ["..."]}],
  "score": 0-100 integer,
  "suggestions": ["3-4 actionable improvement suggestions"]
}

Rules:
- "skills" must be a flat list of the candidate's technical skills.
- "score" must be a realistic 0-100 integer based on resume strength, matching
  quality and completeness.
- Do not invent facts that are not present in the resume.
- Return only JSON, no markdown, no commentary."""


def analyze_resume(text):
    """Analyse resume text -> dict with skills/summary/education/experience/score/suggestions."""
    if not text or not text.strip():
        return build_offline_analysis("")

    if not providers.is_configured():
        return _fallback(text, reason="AI provider not configured")

    try:
        result = providers.chat_json(
            [
                {"role": "system", "content": RESUME_ANALYSIS_SYSTEM},
                {"role": "user", "content": f"RESUME:\n{text}"},
            ],
            temperature=0.2,
            timeout=90,
        )
        result.setdefault("skills", [])
        result.setdefault("summary", "")
        result.setdefault("education", [])
        result.setdefault("experience", [])
        result.setdefault("score", 0)
        result.setdefault("suggestions", [])
        result["source"] = "ai"
        return result
    except AiError as exc:
        logger.warning("Resume AI analysis failed (%s); falling back to offline.", exc)
        if settings.AI_REQUIRED:
            raise
        return build_offline_analysis(text)


def _fallback(text, reason):
    logger.info("Resume analysis using offline path: %s", reason)
    return build_offline_analysis(text)


INTERVIEW_QUESTION_SYSTEM = """You are an expert technical interviewer for a \
software role. Ask ONE concise, realistic interview question (never more than \
one). The question must be relevant to the stated role and to the conversation \
history, and should invite a detailed answer rather than a yes/no response.
Return ONLY JSON: {"question": "..."}"""


def next_interview_question(position, transcript, index, total):
    """Return the next interview question string for ``position`` at stage ``index``/``total``.

    Uses the AI provider when configured; otherwise falls back to a canned bank.
    """
    if not providers.is_configured():
        return offline_question(position, index)

    history = "\n".join(
        f"{role.upper()}: {t['content']}"
        for t in _assistant_user_rows(transcript)
    ) or "No prior answers yet."
    try:
        result = providers.chat_json(
            [
                {"role": "system", "content": INTERVIEW_QUESTION_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Role: {position}. Question index {index + 1} of {total}.\n"
                        f"Conversation so far:\n{history}\n\nReturn the next question."
                    ),
                },
            ],
            temperature=0.7,
            timeout=60,
        )
        return (result.get("question") or "").strip()
    except AiError as exc:
        logger.warning("Interview question generation failed (%s); using offline bank.", exc)
        if settings.AI_REQUIRED:
            raise
        return offline_question(position, index)


INTERVIEW_EVALUATE_SYSTEM = """You are an expert technical interviewer evaluating \
a candidate's answer during a mock interview. Return ONLY JSON:
{
  "score": 0-100 integer,
  "feedback": "2-3 sentences with specific praise and what to improve",
  "suggestions": "one actionable tip"
}
Be fair and specific, referencing the answer and the role."""


def evaluate_interview_answer(position, question, answer):
    """Evaluate a candidate answer -> {score, feedback, suggestions, source}."""
    if not providers.is_configured():
        return offline_evaluate(question, answer)

    try:
        result = providers.chat_json(
            [
                {"role": "system", "content": INTERVIEW_EVALUATE_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Role: {position}\nQuestion: {question}\nCandidate answer: {answer}\n"
                        "Evaluate the answer."
                    ),
                },
            ],
            temperature=0.4,
            timeout=60,
        )
        result["source"] = "ai"
        return result
    except AiError as exc:
        logger.warning("Answer evaluation failed (%s); using offline scoring.", exc)
        if settings.AI_REQUIRED:
            raise
        return offline_evaluate(question, answer)


INTERVIEW_SUMMARY_SYSTEM = """You are an interview coach. Summarise a mock \
interview into a short report for the candidate. Return ONLY JSON:
{
  "summary": "3-4 sentences covering overall performance, strengths and focus areas"
}"""


def summarize_interview(position, transcript):
    """Produce a final report string for a completed interview."""
    if not providers.is_configured():
        return offline_summary(position, transcript)

    history = "\n".join(
        f"{t.get('role', 'user').upper()}: {t.get('content', '')}"
        for t in transcript
    )
    try:
        result = providers.chat_json(
            [
                {"role": "system", "content": INTERVIEW_SUMMARY_SYSTEM},
                {
                    "role": "user",
                    "content": f"Role: {position}\n\nInterview transcript:\n{history}",
                },
            ],
            temperature=0.4,
            timeout=60,
        )
        return (result.get("summary") or "").strip()
    except AiError as exc:
        logger.warning("Interview summary failed (%s); using offline summary.", exc)
        if settings.AI_REQUIRED:
            raise
        return offline_summary(position, transcript)


def _assistant_user_rows(transcript):
    """Return human-readable transcript rows to feed into a prompt."""
    return [
        {"role": t["role"], "content": t.get("content", "")}
        for t in transcript
        if t.get("content")
    ]