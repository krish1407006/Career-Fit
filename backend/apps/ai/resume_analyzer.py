"""Structured AI resume analysis (Phase 6).

This is the only place that talks to the external provider for resume work.
Views call :func:`analyze_resume_text`, get a plain, already-validated dict
back, and never see an API key, an HTTP payload or a stack trace.

Provider selection and credentials come from environment variables read in
``config.settings`` (``AI_PROVIDER``, ``AI_API_KEY``, ``AI_BASE_URL``,
``AI_MODEL``, ``AI_REQUIRED``). Nothing is hard-coded and no key is ever
logged or returned to a client.

Contract returned to callers (always this shape, never raw provider output)::

    {
        "summary": str,
        "detected_skills": [str, ...],
        "strengths": [str, ...],
        "skill_gaps": [str, ...],
        "improvements": [str, ...],
        "recommended_roles": [str, ...],
        "education": [str, ...],
        "experience": [str, ...],
        "score": int,               # document-quality indicator, 0-100
        "source": "ai" | "offline",
        "provider": str,
        "notice": str,              # shown to the student (e.g. offline mode)
        "raw": dict,                # provider payload, for auditing only
    }

Failure modes:
  * no provider/key configured -> :class:`ProviderUnavailable` when the
    deployment demands AI (``AI_REQUIRED``/``require_ai``), otherwise a
    deterministic offline analysis flagged with ``source="offline"``.
  * network/provider failure or unparsable answer -> :class:`AiParseError`
    (or :class:`ProviderUnavailable`), never a raw traceback.
  * structurally valid JSON that is not a usable analysis ->
    :class:`AiParseError`.
"""

import logging

from django.conf import settings

from . import providers
from .errors import AiError, AiParseError, ProviderUnavailable
from .extraction import build_offline_analysis, extract_skills_offline

logger = logging.getLogger(__name__)

MIN_TEXT_LENGTH = 40
MAX_LIST_ITEMS = 12
MAX_TEXT_LENGTH = 600

SYSTEM_PROMPT = """You are an expert technical resume reviewer helping a \
final-year engineering student improve their resume. Read the resume text and \
return ONLY valid JSON with exactly this shape:

{
  "summary": "2-3 short sentences describing the candidate's profile",
  "detected_skills": ["skill", "..."],
  "strengths": ["short strength", "..."],
  "skill_gaps": ["skill or area the resume does not evidence", "..."],
  "improvements": ["actionable edit to make", "..."],
  "recommended_roles": ["job role title", "..."],
  "education": ["degree, institution"],
  "experience": ["role or project with evidence"],
  "score": 0
}

Rules:
- Every list holds short strings (max 12 items, max 4-6 words each).
- "score" is an integer 0-100 describing how complete, well-structured and
  evidence-rich the DOCUMENT is. Never estimate hiring or interview chances.
- Only report what the resume actually shows; do not invent skills.
- Return JSON only: no markdown fences, no commentary."""

USER_PROMPT = """Analyse the resume below.

RESUME TEXT:
{text}

Return the JSON object described in the instructions."""


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
def _clean_text(value, limit=MAX_TEXT_LENGTH):
    if value is None:
        return ""
    if isinstance(value, (list, tuple, dict)):
        return ""
    text = " ".join(str(value).split())
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0]
    return text


def _string_list(value, *, limit=MAX_LIST_ITEMS, item_limit=MAX_TEXT_LENGTH):
    """Coerce arbitrary AI output into a clean list of short strings.

    Accepts a list of strings or of dicts (using a sensible key) and drops
    anything unusable - numbers, nested structures, empty strings - instead of
    trusting it.
    """
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return []
    out = []
    seen = set()
    for item in value:
        if isinstance(item, dict):
            for key in ("name", "skill", "title", "role", "item", "text", "value"):
                if isinstance(item.get(key), str) and item.get(key).strip():
                    item = item[key]
                    break
            else:
                continue
        if not isinstance(item, str):
            continue
        text = _clean_text(item, limit=item_limit)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= limit:
            break
    return out



def _clean_score(value):
    try:
        score = int(float(value))
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, score))


def validate_analysis(payload, *, provider="ai"):
    """Return a normalised analysis dict, or raise :class:`AiParseError`.

    Only keys from the documented contract are kept, and at least one
    substantive field must survive, so an arbitrary/empty provider answer can
    never be written to the database.
    """
    if not isinstance(payload, dict):
        raise AiParseError("AI response was not a JSON object.")

    normalised = {
        "summary": _clean_text(payload.get("summary"), limit=800),
        "detected_skills": _string_list(payload.get("detected_skills") or payload.get("skills")),
        "strengths": _string_list(payload.get("strengths"), item_limit=200),
        "skill_gaps": _string_list(payload.get("skill_gaps"), item_limit=200),
        "improvements": _string_list(payload.get("improvements") or payload.get("suggestions"),
                                     item_limit=240),
        "recommended_roles": _string_list(payload.get("recommended_roles"), limit=6, item_limit=120),
        "education": _string_list(payload.get("education"), item_limit=200),
        "experience": _string_list(payload.get("experience"), item_limit=240),
        "score": _clean_score(payload.get("score")),
    }

    substantive = any([
        normalised["summary"],
        normalised["detected_skills"],
        normalised["strengths"],
        normalised["skill_gaps"],
        normalised["improvements"],
        normalised["recommended_roles"],
    ])
    if not substantive:
        raise AiParseError("AI response contained no usable resume feedback.")

    normalised["source"] = "offline" if provider == "offline" else "ai"
    normalised["provider"] = provider
    normalised["notice"] = ""
    normalised["raw"] = payload
    return normalised


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def is_ai_configured():
    """True when an external provider and API key are available."""
    return providers.is_configured()


def validate_resume_text(text):
    """Return a clean, meaningful resume text or raise :class:`AiParseError`."""
    cleaned = " ".join((text or "").split())
    if not cleaned:
        raise AiParseError(
            "No readable text was found in this PDF. If it is a scanned image, "
            "export a text-based PDF and upload it again."
        )
    if len(cleaned) < MIN_TEXT_LENGTH:
        raise AiParseError(
            "This PDF contains too little readable text to analyse. "
            "Upload a text-based PDF resume."
        )
    return cleaned


def analyze_resume_text(text, *, require_ai=False):
    """Analyse resume text and return the validated structured analysis.

    ``require_ai=True`` (used when ``AI_REQUIRED`` is on) makes a missing
    provider configuration an error instead of an offline fallback.
    """
    cleaned = validate_resume_text(text)

    if not providers.is_configured():
        if require_ai or settings.AI_REQUIRED:
            raise ProviderUnavailable(
                "AI resume analysis is not configured. Set AI_PROVIDER and "
                "AI_API_KEY in the server environment and try again."
            )
        logger.info("Resume analysis running offline: no AI provider configured.")
        return _offline_analysis(cleaned, notice=OFFLINE_NOTICE)

    provider = providers.provider_name()
    try:
        payload = providers.chat_json(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT.format(text=cleaned[:12000])},
            ],
            temperature=0.2,
            timeout=90,
        )
    except AiError as exc:
        # Already a safe, typed error: no key or traceback in the message.
        logger.warning("Resume AI analysis failed (%s): %s", provider, exc.__class__.__name__)
        if require_ai or settings.AI_REQUIRED:
            raise
        return _offline_analysis(cleaned, notice=OFFLINE_FALLBACK_NOTICE)

    return validate_analysis(payload, provider=provider)


OFFLINE_NOTICE = (
    "AI provider is not configured, so these results come from the built-in "
    "rule-based checker. Add a GitHub project, measurable results and links to "
    "improve your resume."
)
OFFLINE_FALLBACK_NOTICE = (
    "The AI service could not be reached, so these results come from the "
    "built-in rule-based checker instead."
)


def _offline_analysis(text, *, notice):
    """Deterministic analysis used when the external provider is unavailable."""
    base = build_offline_analysis(text)
    skills = extract_skills_offline(text)
    payload = {
        "summary": base.get("summary", ""),
        "detected_skills": skills,
        "strengths": _offline_strengths(skills, text),
        "skill_gaps": _offline_gaps(skills),
        "improvements": base.get("suggestions", []),
        "recommended_roles": _offline_roles(skills),
        "education": [],
        "experience": [],
        "score": base.get("score", 0),
    }
    result = validate_analysis(payload, provider="offline")
    result["notice"] = notice
    return result


def _offline_strengths(skills, text):
    strengths = []
    if skills:
        strengths.append(f"Resume lists {len(skills)} recognisable technical skills")
    lowered = text.lower()
    if any(k in lowered for k in ("project", "projects")):
        strengths.append("Mentions project work")
    if any(k in lowered for k in ("internship", "experience", "work")):
        strengths.append("Shows practical experience or internship")
    if any(k in lowered for k in ("b.tech", "b.e", "degree", "university", "college")):
        strengths.append("Education details are present")
    if not strengths:
        strengths.append("Resume text was extracted successfully")
    return strengths


def _offline_gaps(skills):
    common = ["Git", "SQL", "REST API", "Docker", "CI/CD"]
    have = {s.lower() for s in skills}
    return [s for s in common if s.lower() not in have]


def _offline_roles(skills):
    have = {s.lower() for s in skills}
    catalogue = [
        ("Full Stack Developer", ("react", "html", "css", "javascript", "typescript")),
        ("Backend Developer", ("python", "django", "flask", "fastapi", "java", "node.js")),
        ("Data Analyst", ("sql", "pandas", "numpy", "power bi", "tableau")),
        ("ML Engineer", ("machine learning", "deep learning", "pytorch", "tensorflow")),
        ("DevOps Engineer", ("docker", "kubernetes", "aws", "ci/cd", "linux")),
    ]
    roles = [title for title, keys in catalogue if have & set(keys)]
    return roles or ["Software Development Engineer (entry level)"]
