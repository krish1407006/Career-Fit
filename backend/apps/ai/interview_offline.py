"""Deterministic offline interview content used when no AI provider is configured.

A realistic but canned interview experience: question banks per broad role type,
length/keyword-based scoring, and a summarised report.
"""

GENERIC_QUESTIONS = [
    "Walk me through how you would approach designing a feature from requirements to delivery.",
    "Describe a challenging technical problem you solved and how you tackled it.",
    "How do you handle disagreements with a teammate about a technical decision?",
    "Explain a project you are proud of and what your specific contribution was.",
    "How do you stay updated with new tools and technologies?",
    "Tell me about a time you had to learn something quickly under deadline pressure.",
]

PYTHON_QUESTIONS = [
    "Explain the difference between a list and a tuple, and when you would use each.",
    "What is the Global Interpreter Lock (GIL) and how does it affect threading in Python?",
    "What are list comprehensions and generators? Give an example of each.",
    "How does Python handle memory management and garbage collection?",
    "Explain decorators and give a real-world use case.",
    "What is the difference between `__str__` and `__repr__`?",
]

DJANGO_QUESTIONS = [
    "Explain the request lifecycle in Django from URL to response.",
    "What is the Django ORM and how do you optimise queries to avoid the N+1 problem?",
    "How do you handle authentication and permissions in a Django REST API?",
    "What is a migration and how would you revert a bad one?",
    "How would you design a system for soft-deleting records across the ORM?",
    "Explain middleware, signals, and when you should (and shouldn't) use them.",
]

WEB_QUESTIONS = [
    "Explain how a browser renders a page after a URL is typed.",
    "What is the difference between cookies, sessionStorage, and localStorage?",
    "What is CORS and why do browsers enforce it?",
    "Explain RESTful API design principles you follow.",
    "What is the difference between HTTP and HTTPS at the protocol level?",
    "How do you make a web app performant end to end?",
]

FRONTEND_QUESTIONS = [
    "Explain the difference between React state and props.",
    "What is the virtual DOM and how does React use it?",
    "How do you manage global state in a large React application?",
    "Explain hooks like useEffect, useMemo, and useCallback in plain terms.",
    "How would you optimise re-renders in a React component tree?",
    "Describe what a controlled versus uncontrolled input is in React.",
]

DATA_QUESTIONS = [
    "What is the difference between supervised and unsupervised learning?",
    "How do you handle missing or imbalanced data in a dataset?",
    "Explain precision, recall, and the F1 score.",
    "How would you detect outliers in a dataset?",
    "Explain the bias-variance tradeoff.",
    "You have a pandas DataFrame; how do you clean and reshape it for modelling?",
]

BANKS = {
    "python": PYTHON_QUESTIONS,
    "django": DJANGO_QUESTIONS,
    "frontend": FRONTEND_QUESTIONS,
    "react": FRONTEND_QUESTIONS,
    "web": WEB_QUESTIONS,
    "data": DATA_QUESTIONS,
    "machine learning": DATA_QUESTIONS,
    "ml": DATA_QUESTIONS,
    "ai": DATA_QUESTIONS,
}

_TOPIC_HINTS = {
    "python": ["tuple", "list", "gil", "generator", "decorator", "memory"],
    "django": ["orm", "migration", "django", "queryset", "middleware", "rest"],
    "web": ["http", "cookie", "cors", "rest", "browser", "cache", "static"],
    "frontend": ["react", "state", "component", "hook", "dom", "rend", "jsx"],
    "data": ["model", "data", "feature", "accuracy", "training", "dataset", "learn"],
}


def _bank_for_position(position):
    pos = (position or "").lower()
    for key in BANKS:
        if key in pos:
            return BANKS[key]
    return GENERIC_QUESTIONS


def offline_question(position, index):
    bank = _bank_for_position(position)
    return bank[index % len(bank)]


def offline_evaluate(question, answer):
    """Heuristic evaluation: length signals + topic keyword coverage."""
    words = (answer or "").split()
    pos = (question or "").lower()
    hints = []
    for bank_key, kw in _TOPIC_HINTS.items():
        if any(k in pos for k in ["python", "django", "orm"]):
            hints = _TOPIC_HINTS["python"] + _TOPIC_HINTS["django"]
        elif any(k in pos for k in ["react", "javascript", "frontend", "dom"]):
            hints = _TOPIC_HINTS["frontend"]
        elif any(k in pos for k in ["http", "web", "rest", "browser"]):
            hints = _TOPIC_HINTS["web"]
        elif bank_key in pos:
            hints = kw

    covered = sum(1 for h in hints if h in (answer or "").lower())
    length = len(words)
    if length < 8:
        base = 20
        feedback = "Your answer was quite short. Expand it with a structure: definition, example, and trade-offs."
        suggestions = "Give a 1-2 minute structured answer. Name concrete examples or tools."
    elif length < 20:
        base = 45
        feedback = "Decent coverage, but the answer would benefit from more depth and a concrete example."
        suggestions = "Add a small example or experience from a project, and state a conclusion."
    elif covered == 0 and len(hints):
        base = 55
        feedback = "Good length, but it didn't touch on the key concepts an interviewer expects for this topic."
        suggestions = ", ".join(hints[:4]) if hints else "Cover the core concepts directly."
    else:
        base = min(85, 60 + covered * 8)
        feedback = "Strong, structured answer that addresses the topic with relevant detail."
        suggestions = "Keep this up; consider relating the answer to an actual project experience."

    score = max(10, min(95, base + min(length // 10, 5)))
    return {
        "source": "offline",
        "score": score,
        "feedback": feedback,
        "suggestions": suggestions,
    }


def offline_summary(position, transcript):
    """Build a simple final report from the stored stages."""
    qs = [t["content"] for t in transcript if t.get("role") == "assistant" and t.get("kind") == "question"]
    evals = [
        t for t in transcript if t.get("role") == "assistant" and t.get("kind") == "evaluation"
    ]
    scores = [int(t.get("score") or 0) for t in evals]
    avg = round(sum(scores) / len(scores)) if scores else 0
    strengths = "consistent structure and relevant examples." if avg >= 60 else \
        "needs more depth and topic-specific vocabulary."
    return (
        f"You completed a mock interview for the position of {position or 'your target role'} "
        f"({len(qs)} questions). Average score: {avg}/100. Overall: your answers show {strengths} "
        "Review the feedback per question, prepare more concrete project examples, and retake "
        "the mock interview to track improvement."
    )