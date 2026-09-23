"""Deterministic, offline text-analysis helpers used when no AI provider is
configured. Keeps the platform functional for local dev and demos, and gives
the AI path a well-defined fallback.
"""

import re

SKILL_TAXONOMY = [
    # Programming languages
    "python", "javascript", "typescript", "java", "c", "c++", "c#", "go",
    "golang", "rust", "kotlin", "swift", "ruby", "php", "scala", "r",
    "dart", "matlab", "shell", "bash", "powershell", "sql",
    # Web / frontend
    "react", "react.js", "react native", "redux", "next.js", "vue", "vue.js",
    "angular", "svelte", "html", "css", "tailwind", "bootstrap", "jquery",
    "webpack", "vite", "rest api", "graphql", "websocket",
    # Backend / frameworks
    "django", "flask", "fastapi", "spring boot", "spring", "node.js", "express",
    "express.js", "rails", "laravel", "asp.net", "fastapi",
    # Databases
    "postgresql", "mysql", "sqlite", "mongodb", "redis", "elasticsearch",
    "cassandra", "dynamodb", "cockroachdb", "oracle", "sql server",
    # Cloud / devops
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s",
    "terraform", "ansible", "jenkins", "github actions", "ci/cd", "nginx",
    "linux", "git", "github", "gitlab", "serverless",
    # Data / ML / AI
    "machine learning", "deep learning", "tensorflow", "pytorch", "keras",
    "scikit-learn", "pandas", "numpy", "matplotlib", "seaborn", "nlp",
    "natural language processing", "computer vision", "opencv", "llm",
    "large language model", "generative ai", "rag", "data analysis",
    "data visualization", "power bi", "tableau", "hadoop", "spark", "airflow",
    # Testing / tools
    "pytest", "junit", "selenium", "cypress", "jest", "mocha", "postman",
    "swagger", "jira", "agile", "scrum", "docker compose",
    # Aptitude / fundamentals used in job postings
    "data structures", "algorithms", "oops", "dbms", "operating systems",
    "computer networks", "system design", "sql queries",
]

_TITLE_TOKEN = re.compile(r"[a-zA-Z0-9+#&.]+")

_EDUCATION_KEYWORDS = ["b.tech", "b.e", "bachelor", "b.sc", "m.tech", "m.sc", "mba",
                       "bca", "mca", "diploma", "degree", "graduation", "high school",
                       "12th", "10th", "class xii", "class x"]

_EXPERIENCE_KEYWORDS = ["experience", "internship", "worked at", "worked on", "project",
                        "training", "freelance", "years"]

_WEAK_WORDS = {"maybe", "i am learning", "basic", "beginner", "familiar", "junior"}


def normalise_skill(name):
    return name.strip().lower().replace("_", " ")


def extract_skills_offline(text):
    """Return canonical skill names found (word-boundary match) in text."""
    if not text:
        return []
    lowered = text.lower()
    found = []
    for skill in SKILL_TAXONOMY:
        if len(skill) < 2:
            continue
        if re.search(r"\b" + re.escape(skill) + r"\b", lowered) and skill not in found:
            found.append(skill)
    return found


def extract_emails(text):
    return re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)


def extract_phone(text):
    match = re.search(r"(\+?\d[\d\s\-()]{8,15}\d)", text)
    return match.group(1).strip() if match else ""


def _score_resume(text, skills):
    """Heuristic 0-100 score used by the offline path."""
    score = 30
    if skills:
        score += min(len(skills) * 3, 30)
    if extract_emails(text):
        score += 10
    if extract_phone(text):
        score += 5
    if any(k in text.lower() for k in ["education", "b.tech", "degree", "college"]):
        score += 10
    if any(k in text.lower() for k in ["project", "internship", "experience"]):
        score += 10
    if any(k in text.lower() for k in ["github", "linkedin", "portfolio", "certification", "certificate"]):
        score += 5
    return min(score, 95)


def build_offline_analysis(text):
    """Fallback resume analysis when the AI provider is unavailable."""
    skills = extract_skills_offline(text)
    return {
        "skills": skills,
        "summary": "Offline analysis: extracted "
                   f"{len(skills)} recognizable skills from the resume. "
                   "Configure an AI provider for richer summary, scoring and suggestions.",
        "education": [],
        "experience": [],
        "score": _score_resume(text, skills),
        "suggestions": [
            "Add measurable outcomes to projects (e.g. 'cut load time by 40%')",
            "Include your GitHub / LinkedIn / portfolio links",
            "Keep the resume to one page for 0-2 years of experience",
            "Tailor the skills section to the target role's requirements",
        ],
        "source": "offline",
    }