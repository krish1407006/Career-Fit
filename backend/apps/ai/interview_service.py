"""Structured AI mock-interview service (Phase 7).

This is the only module that talks to the external provider for interview work.
``apps.interviews`` views call the functions here (or, more usually,
``apps.interviews.services`` which orchestrates them) and always receive a
plain, already-validated dict. No API key, HTTP payload, provider exception or
stack trace is ever returned to a client.

Provider selection and credentials come from environment variables read in
``config.settings`` (``AI_PROVIDER``, ``AI_API_KEY``, ``AI_BASE_URL``,
``AI_MODEL``, ``AI_REQUIRED``).

Contracts returned to callers (always this shape, never raw provider output)::

    # generate_question(...)
    {
        "question": str,
        "category": "technical" | "behavioral" | "situational" | "project" | "general",
        "source": "ai" | "offline",
        "provider": str,
        "notice": str,
        "raw": dict,
    }

    # evaluate_answer(...)
    {
        "score": int,                     # 0-10 answer quality indicator
        "technical_correctness": str,
        "relevance": str,
        "clarity": str,
        "completeness": str,
        "strengths": [str, ...],
        "improvements": [str, ...],
        "feedback": str,
        "source": "ai" | "offline",
        "provider": str,
        "notice": str,
        "raw": dict,
    }

    # build_report(...)
    {
        "summary": str,
        "questions_answered": int,
        "score": int | None,              # average, an indicator only
        "technical_strengths": [str, ...],
        "areas_to_improve": [str, ...],
        "topics_to_prepare": [str, ...],
        "per_question": [
            {
                "question": str, "answer": str, "score": int | None,
                "feedback": str, "strengths": [str, ...],
                "improvements": [str, ...], "category": str,
            }, ...
        ],
        "score_note": str,
        "source": "ai" | "offline",
        "provider": str,
        "notice": str,
        "raw": dict,
    }

Failure handling mirrors Phase 6 (``apps/ai/resume_analyzer.py``):

  * no provider/key configured -> deterministic offline content flagged with
    ``source="offline"``, unless the deployment demands AI (``AI_REQUIRED`` /
    ``require_ai``), in which case :class:`ProviderUnavailable` is raised.
  * provider/network failure or unparsable answer -> :class:`AiParseError` or
    :class:`ProviderUnavailable`; when AI is optional the offline content is
    used so the interview never breaks.
  * structurally valid JSON that is not usable -> :class:`AiParseError`.
"""

import logging

from django.conf import settings

from . import providers
from .errors import AiError, AiParseError, ProviderUnavailable
from .interview_offline import (
    CATEGORIES,
    offline_evaluate,
    offline_question,
    offline_report,
)

logger = logging.getLogger(__name__)

MAX_LIST_ITEMS = 8
MAX_TEXT_LENGTH = 700
MAX_ANSWER_CHARS = 12000

OFFLINE_NOTICE = (
    "AI provider is not configured, so questions and feedback come from the "
    "built-in offline interview engine."
)
STALE_CONTEXT_NOTICE = "Live AI follow-up was unavailable, using a prepared question instead."


# ----------------------------------------------------------------------
# Prompts
# ----------------------------------------------------------------------

QUESTION_SYSTEM = """You are a friendly but rigorous technical interviewer \
conducting a live, voice-based mock interview for a student. The interview is a \
conversation, not a questionnaire.

Return ONLY valid JSON with exactly this shape:

{
  "question": "the question, spoken aloud, max 2 sentences",
  "category": "technical" | "behavioral" | "situational" | "project" | "general"
}

Rules:
- Ask exactly ONE question per turn.
- If the candidate has just answered, you MAY build on it: reference a specific \
thing they said and drill one level deeper (for example "Can you explain how you \
implemented authentication in that project?").
- Otherwise move the conversation forward to a new, relevant topic.
- Stay grounded in the candidate's target role, the job's required skills, the \
candidate's own skills and resume analysis. Do not invent facts about them.
- Vary the category across the interview; include at least one behavioral or \
situational question.
- Ask only job-relevant questions. Never ask about age, gender, religion, caste, \
nationality, marital status, health, disability, appearance or accent. Never ask \
for anything the candidate has not been asked to disclose.
- Speak plainly and briefly: this text is read aloud by a text-to-speech voice.
- Return JSON only: no markdown fences, no commentary."""

QUESTION_USER = """Target role: {position}
Question {index} of {total}.

Candidate context:
{context}

Conversation so far:
{history}

Ask the next question."""

EVALUATE_SYSTEM = """You are an expert technical interviewer giving a candidate \
feedback on one answer from a mock interview. Be fair, specific and constructive.

Return ONLY valid JSON with exactly this shape:

{
  "score": 0,
  "technical_correctness": "1-2 sentences on factual/technical accuracy",
  "relevance": "1 sentence on whether it addressed the question",
  "clarity": "1 sentence on structure and communication",
  "completeness": "1 sentence on depth and missing points",
  "strengths": ["short specific strength", "..."],
  "improvements": ["short actionable improvement", "..."],
  "feedback": "2-3 encouraging sentences with concrete praise and the single most useful thing to fix"
}

Rules:
- "score" is an integer 0-10 describing this answer only. It is a practice \
indicator, NOT a hiring decision or an objective measure of ability.
- Judge the answer that was actually given. If it is short, unclear or wrong, say \
so kindly and say what a strong answer would include.
- Never comment on how the candidate spoke: no accent, tone, grammar-as-identity, \
emotion, confidence or personality judgements, and nothing about voice quality.
- Never mention protected characteristics, and never speculate about them.
- Use short lists (max 4 items) of brief strings.
- Return JSON only: no markdown fences, no commentary."""

EVALUATE_USER = """Target role: {position}

Candidate context:
{context}

Question asked:
{question}

Candidate answer:
{answer}

Evaluate this answer."""

REPORT_SYSTEM = """You are an interview coach writing a practice report for a \
student who just finished a mock interview.

Return ONLY valid JSON with exactly this shape:

{
  "summary": "3-5 sentences: how they did overall, their clearest strength and their single biggest focus area",
  "technical_strengths": ["specific demonstrated strength", "..."],
  "areas_to_improve": ["specific area to work on", "..."],
  "topics_to_prepare": ["specific topic to revise", "..."]
}

Rules:
- Base everything only on the transcript and evaluations provided. Do not invent \
projects, employers or results.
- Be specific to what they actually said.
- Never comment on accent, tone, emotion, confidence, personality, gender, age or \
any protected characteristic, and never present a score as a hiring decision.
- Short lists (max 5 items) of brief strings.
- Return JSON only: no markdown fences, no commentary."""

REPORT_USER = """Target role: {position}

Candidate context:
{context}

Evaluated answers:
{evaluations}

Write the practice report."""

SCORE_NOTE = (
    "These scores are self-practice indicators produced by an AI coach. They are "
    "not an objective measure of interview ability and are not a hiring decision."
)


# ----------------------------------------------------------------------
# Candidate context (job, skills, resume analysis) -- no AI involved
# ----------------------------------------------------------------------

def build_context(user, job=None, position=""):
    """Collect the existing CareerAI data a question may legitimately use.

    Reuses the Phase 1-6 profile, skills, jobs and resume-analysis models. Every
    lookup is optional and defensive: a student with nothing on file still gets a
    usable context.
    """
    from apps.accounts.models import StudentProfile

    lines = []

    profile = StudentProfile.objects.filter(user=user).first()
    if profile:
        if profile.full_name:
            lines.append(f"Candidate name: {profile.full_name}")
        if profile.degree or profile.branch:
            lines.append(
                "Studying: "
                + ", ".join(p for p in (profile.degree, profile.branch) if p)
            )
        if profile.graduation_year:
            lines.append(f"Graduation year: {profile.graduation_year}")
        if profile.preferred_roles:
            lines.append(f"Preferred roles: {_join(profile.preferred_roles)}")
        skills = list(profile.skills.values_list("name", flat=True)[:25])
        if skills:
            lines.append(f"Candidate's own skills: {_join(skills)}")
        if profile.bio:
            lines.append(f"Profile summary: {profile.bio[:300]}")

    if job is not None:
        lines.append(f"Target job posting: {job.title} at {job.company_name}")
        required = list(job.required_skills.values_list("name", flat=True)[:15])
        if required:
            lines.append(f"Job required skills: {_join(required)}")
        preferred = list(job.preferred_skills.values_list("name", flat=True)[:15])
        if preferred:
            lines.append(f"Job preferred skills: {_join(preferred)}")
        if job.responsibilities:
            lines.append(f"Job responsibilities: {_join(job.responsibilities[:6])}")
    elif position:
        lines.append(f"Target role (no specific posting selected): {position}")

    # Phase 6 resume analysis: skill gaps make excellent follow-up material.
    from apps.resumes.models import Resume, ResumeAnalysis

    latest = (
        Resume.objects.filter(
            user=user, analysis__status=ResumeAnalysis.Status.COMPLETED
        )
        .select_related("analysis")
        .order_by("-uploaded_at")
        .first()
    )
    latest = getattr(latest, "analysis", None)
    if latest:
        gaps = [g for g in (latest.skill_gaps or []) if g][:8]
        if gaps:
            lines.append(f"Resume skill gaps to probe: {_join(gaps)}")
        strengths = [s for s in (latest.strengths or []) if s][:5]
        if strengths:
            lines.append(f"Resume strengths: {_join(strengths)}")
        roles = [r for r in (latest.recommended_roles or []) if r][:5]
        if roles:
            lines.append(f"Roles suggested by resume analysis: {_join(roles)}")
    if not lines:
        lines.append("No profile, job or resume data available yet.")
    return "\n".join(lines)


def _join(values):
    return ", ".join(str(v) for v in values if str(v).strip())


def _history_lines(transcript):
    """Render the conversation so far as readable prompt lines."""
    lines = []
    for turn in transcript or []:
        kind = turn.get("kind") if isinstance(turn, dict) else getattr(turn, "kind", "")
        role = turn.get("role") if isinstance(turn, dict) else getattr(turn, "role", "")
        content = turn.get("content") if isinstance(turn, dict) else getattr(turn, "content", "")
        if not content:
            continue
        if kind == "question":
            lines.append(f"INTERVIEWER: {content}")
        elif kind == "answer":
            lines.append(f"CANDIDATE: {content}")
    return "\n".join(lines[-24:]) or "No questions asked yet."


def _last_answer(transcript):
    for turn in reversed(list(transcript or [])):
        kind = turn.get("kind") if isinstance(turn, dict) else getattr(turn, "kind", "")
        if kind == "answer":
            content = turn.get("content") if isinstance(turn, dict) else getattr(turn, "content", "")
            if content:
                return str(content)[:1500]
    return ""


# ----------------------------------------------------------------------
# Small normalisers -- every AI field is coerced into a safe, bounded shape
# ----------------------------------------------------------------------

def _as_text(value, limit=MAX_TEXT_LENGTH):
    if value is None or isinstance(value, (dict, list, tuple, set)):
        return ""
    text = str(value).strip()
    return text[:limit]


def _as_list(value, limit=MAX_LIST_ITEMS):
    if isinstance(value, str):
        parts = [p.strip(" -*\t") for p in value.replace("\n", ",").split(",")]
        items = [p for p in parts if p]
    elif isinstance(value, (list, tuple, set)):
        items = [_as_text(v, 200) for v in value]
    elif value is None:
        items = []
    else:
        items = [_as_text(value, 200)]
    out, seen = [], set()
    for item in items:
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item[:200])
        if len(out) >= limit:
            break
    return out


def _as_score(value, maximum=10, default=0):
    try:
        if isinstance(value, bool):
            raise TypeError
        number = float(value)
    except (TypeError, ValueError):
        return default
    number = max(0.0, min(float(maximum), number))
    return int(round(number))


def _normalise_category(value):
    text = (value or "").strip().lower()
    return text if text in CATEGORIES else "general"


# ----------------------------------------------------------------------
# Question generation (adaptive: uses the conversation so far)
# ----------------------------------------------------------------------

def generate_question(context, position, transcript=None, index=0, total=5, require_ai=False):
    """Return the next question dict. Adaptive when a provider is configured."""
    transcript = transcript or []

    if not providers.is_configured():
        question = offline_question(position, index)
        return {
            "question": question,
            "category": _category_for_offline(position, index),
            "source": "offline",
            "provider": providers.provider_name(),
            "notice": OFFLINE_NOTICE,
            "raw": {},
        }

    try:
        result = providers.chat_json(
            [
                {"role": "system", "content": QUESTION_SYSTEM},
                {
                    "role": "user",
                    "content": QUESTION_USER.format(
                        position=position or "software engineering",
                        index=index + 1,
                        total=total,
                        context=context or "No extra context.",
                        history=_history_lines(transcript),
                    ),
                },
            ],
            temperature=0.7,
            timeout=60,
        )
        if not isinstance(result, dict):
            raise AiParseError("AI question response was not a JSON object")
        question = _as_text(result.get("question"), 500)
        if len(question) < 8:
            raise AiParseError("AI question response had no usable question text")
    except AiError as exc:
        logger.warning("Interview question generation failed (%s).", exc.__class__.__name__)
        if require_ai or settings.AI_REQUIRED:
            raise
        return {
            "question": offline_question(position, index),
            "category": _category_for_offline(position, index),
            "source": "offline",
            "provider": providers.provider_name(),
            "notice": STALE_CONTEXT_NOTICE,
            "raw": {},
        }

    return {
        "question": question,
        "category": _normalise_category(result.get("category")),
        "source": "ai",
        "provider": providers.provider_name(),
        "notice": "",
        "raw": result,
    }


def _category_for_offline(position, index):
    """Rotate through categories so the offline engine still feels varied."""
    return CATEGORIES[index % len(CATEGORIES)]


# ----------------------------------------------------------------------
# Answer evaluation
# ----------------------------------------------------------------------

def evaluate_answer(context, position, question, answer, require_ai=False):
    """Evaluate one answer -> structured dict (see module docstring)."""
    answer = (answer or "").strip()[:MAX_ANSWER_CHARS]
    question = (question or "").strip()[:1000]

    if not providers.is_configured():
        return dict(offline_evaluate(question, answer), provider=providers.provider_name(),
                    notice=OFFLINE_NOTICE, raw={})

    try:
        result = providers.chat_json(
            [
                {"role": "system", "content": EVALUATE_SYSTEM},
                {
                    "role": "user",
                    "content": EVALUATE_USER.format(
                        position=position or "software engineering",
                        context=context or "No extra context.",
                        question=question or "(question unavailable)",
                        answer=answer or "(no answer given)",
                    ),
                },
            ],
            temperature=0.4,
            timeout=60,
        )
        if not isinstance(result, dict):
            raise AiParseError("AI evaluation response was not a JSON object")
        feedback = _as_text(result.get("feedback"))
        if not feedback and not _as_list(result.get("strengths")):
            raise AiParseError("AI evaluation response had no usable feedback")
    except AiError as exc:
        logger.warning("Interview answer evaluation failed (%s).", exc.__class__.__name__)
        if require_ai or settings.AI_REQUIRED:
            raise
        return dict(offline_evaluate(question, answer), provider=providers.provider_name(),
                    notice=STALE_CONTEXT_NOTICE, raw={})

    return {
        "score": _as_score(result.get("score"), maximum=10, default=5),
        "technical_correctness": _as_text(result.get("technical_correctness"), 400),
        "relevance": _as_text(result.get("relevance"), 400),
        "clarity": _as_text(result.get("clarity"), 400),
        "completeness": _as_text(result.get("completeness"), 400),
        "strengths": _as_list(result.get("strengths"), 4),
        "improvements": _as_list(result.get("improvements"), 4),
        "feedback": feedback or "Answer reviewed.",
        "source": "ai",
        "provider": providers.provider_name(),
        "notice": "",
        "raw": result,
    }


# ----------------------------------------------------------------------
# Final report
# ----------------------------------------------------------------------

def build_report(context, position, per_question, require_ai=False):
    """Build the structured practice report -> dict (see module docstring)."""
    pairs = [p for p in (per_question or [])]
    answered = [p for p in pairs if (p.get("answer") or "").strip()]
    scores = [p["score"] for p in answered if isinstance(p.get("score"), int)]
    average = int(round(sum(scores) / len(scores))) if scores else None

    if not providers.is_configured():
        report = offline_report(position, pairs)
        report.update(
            {"score": average, "provider": providers.provider_name(),
             "notice": OFFLINE_NOTICE, "raw": {}}
        )
        return report

    evaluations = "\n".join(
        f"Q{i + 1}: {p.get('question', '')}\n"
        f"A: {(p.get('answer') or '')[:1200]}\n"
        f"Coach score: {p.get('score')}/10 - {p.get('feedback', '')[:400]}"
        for i, p in enumerate(answered)
    ) or "No answers were submitted."

    try:
        result = providers.chat_json(
            [
                {"role": "system", "content": REPORT_SYSTEM},
                {
                    "role": "user",
                    "content": REPORT_USER.format(
                        position=position or "software engineering",
                        context=context or "No extra context.",
                        evaluations=evaluations,
                    ),
                },
            ],
            temperature=0.4,
            timeout=90,
        )
        if not isinstance(result, dict):
            raise AiParseError("AI report response was not a JSON object")
        summary = _as_text(result.get("summary"), 2000)
        if not summary:
            raise AiParseError("AI report response had no usable summary")
    except AiError as exc:
        logger.warning("Interview report generation failed (%s).", exc.__class__.__name__)
        if require_ai or settings.AI_REQUIRED:
            raise
        report = offline_report(position, pairs)
        report.update(
            {"score": average, "provider": providers.provider_name(),
             "notice": STALE_CONTEXT_NOTICE, "raw": {}}
        )
        return report

    return {
        "summary": summary,
        "questions_answered": len(answered),
        "score": average,
        "technical_strengths": _as_list(result.get("technical_strengths"), 5),
        "areas_to_improve": _as_list(result.get("areas_to_improve"), 5),
        "topics_to_prepare": _as_list(result.get("topics_to_prepare"), 5),
        "per_question": [
            {
                "question": _as_text(p.get("question"), 500),
                "answer": _as_text(p.get("answer"), 2000),
                "score": p.get("score") if isinstance(p.get("score"), int) else None,
                "feedback": _as_text(p.get("feedback"), 1000),
                "strengths": _as_list(p.get("strengths"), 4),
                "improvements": _as_list(p.get("improvements"), 4),
                "category": p.get("category") or "",
            }
            for p in pairs
        ],
        "score_note": SCORE_NOTE,
        "source": "ai",
        "provider": providers.provider_name(),
        "notice": "",
        "raw": result,
    }


__all__ = [
    "MAX_ANSWER_CHARS",
    "SCORE_NOTE",
    "ProviderUnavailable",
    "build_context",
    "build_report",
    "evaluate_answer",
    "generate_question",
]

