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

    candidate_skills / required_skills may be lists, dicts, Skill model
    instances or a queryset of them; all are normalised before comparison.

    Matching percentage = (matched required skills / total required skills) x 100.
    Comparison is case-insensitive and duplicate-tolerant.

    Edge cases:
      * job has no required skills  -> no gaps, coverage 100%
      * student has no skills       -> coverage 0% (when job has requirements)
    Returns {have, needed, matched, missing, coverage, score}.
    """
    have = set(tokenise_skills(candidate_skills))
    need = set(tokenise_skills(required_skills))
    if not need:
        matched = set()
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
    """Rank a job against a student's skillset.

    The score is the transparent skill-matching percentage:
    (matched required skills / total required skills) x 100.

    ``preferred_roles`` is accepted for API compatibility and reported as a
    soft role_hint, but it never changes the match percentage itself.
    """
    gap = skill_gap(candidate_skills, job.required_skills.all())
    role_hint = False
    if preferred_roles:
        hay = f"{job.title} {job.company_name}".lower()
        for role in preferred_roles:
            role_l = role.lower()
            if role_l and (role_l in hay or any(
                t in hay for t in role_l.split() if len(t) > 2
            )):
                role_hint = True
                break
    return {
        "score": gap["score"],
        "role_hint": role_hint,
        "skill_gap": {
            "matched": gap["matched"],
            "missing": gap["missing"],
            "coverage": gap["coverage"],
        },
    }