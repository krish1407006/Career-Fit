"""Skill-gap and job-matching logic used by the jobs API and the dashboard."""

import re

SPLIT_RE = re.compile(r"[,\n/|]+")


def normalise(text):
    return text.strip().lower().replace("_", " ")


def tokenise_skills(raw):
    """Turn a raw list/dict of skill names into a list of normalised strings."""
    if not raw:
        return []
    if isinstance(raw, str):
        chunks = SPLIT_RE.split(raw)
    else:
        chunks = []
        for item in raw:
            if not item:
                continue
            if isinstance(item, dict):
                item = item.get("name") or item.get("skill") or ""
            chunks.extend(SPLIT_RE.split(str(item)))
    return sorted({normalise(c) for c in chunks if c and len(c) >= 2})


def skill_gap(candidate_skills, required_skills):
    """Compare two skill sets.

    candidate_skills / required_skills may be lists or dicts; normalised.
    Returns {matched, missing, coverage, score}.
    """
    have = set(tokenise_skills(candidate_skills))
    need = set(tokenise_skills(required_skills))
    if not need:
        matched = set(have)
        missing = []
        coverage = 100.0
    else:
        matched = have & need
        missing = sorted(need - have)
        coverage = round((len(matched) / len(need)) * 100, 1)
    return {
        "have": sorted(have),
        "needed": sorted(need),
        "matched": sorted(matched),
        "missing": missing,
        "coverage": coverage,
        "score": round(coverage),
    }


def match_job_to_student(job, candidate_skills, preferred_roles=None):
    """Rank a job against a student's profile. Returns a 0-100 explainable score."""
    gap = skill_gap(candidate_skills, job.skills_required)
    skills_score = gap["score"]

    role_bonus = 0
    if preferred_roles:
        hay = f"{job.title} {job.company_name}".lower()
        for role in preferred_roles:
            role_l = role.lower()
            if role_l and role_l in hay or any(
                t in hay for t in role_l.split() if len(t) > 2
            ):
                role_bonus = 30
                break

    # Weight: 70% skills coverage, 30% role preference match.
    score = round(0.7 * skills_score + role_bonus)
    return {
        "score": score,
        "skill_gap": {
            "matched": gap["matched"],
            "missing": gap["missing"],
            "coverage": gap["coverage"],
        },
    }