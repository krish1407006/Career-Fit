"""Deterministic offline interview content used when no AI provider is configured.

A realistic but canned interview experience: question banks per broad role type,
structured keyword/length-based answer evaluation, and a practice report.

Everything here is pure Python with no Django import, so it is trivially
testable and can never leak a traceback to a client.
"""

CATEGORIES = ("technical", "behavioral", "situational", "project", "general")

SCORE_NOTE = (
    "These scores are self-practice indicators produced by an offline rule engine. "
    "They are not an objective measure of interview ability and are not a hiring decision."
)

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

_BEHAVIOURAL_MARKERS = (
    "tell me about a time", "describe a", "how do you handle", "walk me through",
    "how would you", "give an example", "explain", "what is", "what are",
)


def _bank_for_position(position):
    pos = (position or "").lower()
    for key in BANKS:
        if key in pos:
            return BANKS[key]
    return GENERIC_QUESTIONS


def offline_question(position, index):
    bank = _bank_for_position(position)
    return bank[index % len(bank)]


def _hints_for_question(question):
    pos = (question or "").lower()
    if any(k in pos for k in ("python", "django", "orm")):
        return _TOPIC_HINTS["python"] + _TOPIC_HINTS["django"]
    if any(k in pos for k in ("react", "javascript", "frontend", "dom")):
        return _TOPIC_HINTS["frontend"]
    if any(k in pos for k in ("http", "web", "rest", "browser")):
        return _TOPIC_HINTS["web"]
    for bank_key, keywords in _TOPIC_HINTS.items():
        if bank_key in pos:
            return keywords
    if any(marker in pos for marker in _BEHAVIOURAL_MARKERS):
        return ["situation", "task", "action", "result", "example", "team", "deadline"]
    return []


def offline_evaluate(question, answer):
    """Heuristic structured evaluation: length signals + topic keyword coverage.

    Returns the Phase 7 contract. ``suggestions`` is kept for backwards
    compatibility with the Phase 1-6 flat evaluation consumers.
    """
    words = (answer or "").split()
    hints = _hints_for_question(question)
    lowered = (answer or "").lower()
    covered = [h for h in hints if h in lowered]
    length = len(words)

    if length < 8:
        base = 2
        feedback = (
            "Your answer was very short. A strong answer here would give a definition, "
            "a concrete example and the trade-off you would pick."
        )
        improvements = [
            "Give a 1-2 minute structured answer: definition, example, trade-off",
            "Name a real project or code you have written that covers this",
        ]
    elif length < 20:
        base = 4
        feedback = (
            "You covered the main idea, but the answer would be stronger with more "
            "depth and one concrete example."
        )
        improvements = [
            "Add a small example or a project you used this in",
            "State your conclusion or recommendation explicitly",
        ]
    elif not hints:
        base = 5
        feedback = "Good length and a relevant answer. Structure it clearly and stay concrete."
        improvements = ["Open with your conclusion, then justify it with an example"]
    elif not covered:
        base = 5
        feedback = (
            "Good length, but it did not touch on the key concepts an interviewer "
            "expects for this topic."
        )
        improvements = [f"Cover the core concepts directly, e.g. {', '.join(hints[:4])}"]
    else:
        base = min(8, 5 + len(covered))
        feedback = (
            "Strong, structured answer that addresses the topic with relevant detail."
        )
        improvements = [
            "Tie the answer explicitly to a project outcome or metric",
        ]

    score = max(1, min(10, base + min(length // 25, 2)))
    relevance = (
        "Your answer addresses the question directly."
        if length >= 8
        else "Too little content to judge relevance yet; expand on the question asked."
    )
    clarity = (
        "The answer flows in a readable order."
        if length >= 20
        else "The answer is hard to follow without more structure."
    )
    completeness = (
        f"It touches on {len(covered)} of the expected key ideas for this topic."
        if hints
        else "Depth could be increased with an example and its consequences."
    )
    strengths = []
    if length >= 20:
        strengths.append("Gave a substantive answer rather than a one-liner")
    if covered:
        strengths.append(f"Mentioned relevant concepts ({', '.join(covered[:3])})")
    if not strengths:
        strengths.append("Attempted the question directly")

    return {
        "source": "offline",
        "score": score,
        "technical_correctness": (
            "Concepts look consistent with the topic. Verify the details of "
            f"{', '.join(covered[:3])} against the official documentation."
            if covered
            else "Not enough technical detail to assess correctness; add specifics."
        ),
        "relevance": relevance,
        "clarity": clarity,
        "completeness": completeness,
        "strengths": strengths[:4],
        "improvements": improvements[:4],
        "feedback": feedback,
        "suggestions": improvements[0] if improvements else "",
    }


def offline_summary(position, transcript):
    """Phase 1-6 flat summary string (kept for backwards compatibility)."""
    qs = [t["content"] for t in transcript if t.get("role") == "assistant" and t.get("kind") == "question"]
    evals = [
        t for t in transcript if t.get("role") == "assistant" and t.get("kind") == "evaluation"
    ]
    scores = [int(t.get("score") or 0) for t in evals]
    avg = round(sum(scores) / len(scores)) if scores else 0
    strength = (
        "consistent structure and relevant examples."
        if avg >= 60
        else "needs more depth and topic-specific vocabulary."
    )
    return (
        f"You completed a mock interview for the position of {position or 'your target role'} "
        f"({len(qs)} questions). Average score: {avg}/100. Overall: your answers show {strength} "
        "Review the feedback per question, prepare more concrete project examples, and retake "
        "the mock interview to track improvement."
    )


def _merge_unique(*lists):
    out, seen = [], set()
    for items in lists:
        for item in items or []:
            text = str(item).strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(text)
    return out


def offline_report(position, per_question):
    """Build the structured Phase 7 practice report without any AI call."""
    pairs = [p for p in (per_question or [])]
    answered = [p for p in pairs if (p.get("answer") or "").strip()]
    scores = [p["score"] for p in answered if isinstance(p.get("score"), int)]
    average = int(round(sum(scores) / len(scores))) if scores else None

    strengths = _merge_unique(*[p.get("strengths") or [] for p in answered])[:5]
    improvements = _merge_unique(*[p.get("improvements") or [] for p in answered])[:5]

    # Topics to prepare: gaps mentioned in feedback plus low-scoring question
    # keywords, so the list is specific to this interview.
    topics = []
    for pair in answered:
        if isinstance(pair.get("score"), int) and pair["score"] <= 5:
            question = (pair.get("question") or "").strip()
            if question:
                topics.append(question)
        topics.extend(pair.get("improvements") or [])
    topics = _merge_unique(topics)[:5]

    if not answered:
        summary = (
            f"No answers were submitted for this {position or 'mock interview'}, so there is "
            "nothing to assess yet. Start a new voice interview and answer at least one "
            "question to get per-answer feedback and a practice report."
        )
    else:
        band = (
            "a solid base to build on"
            if (average or 0) >= 7
            else "a reasonable foundation with clear gaps"
            if (average or 0) >= 5
            else "significant room to prepare"
        )
        summary = (
            f"You answered {len(answered)} of {len(pairs)} questions for the "
            f"{position or 'target'} role and averaged {average}/10, which is {band}. "
            "Work through the question-wise feedback below, then retake the interview "
            "and compare your scores to track progress. Remember these are practice "
            "indicators from an offline rule engine, not an objective measurement."
        )

    return {
        "summary": summary,
        "questions_answered": len(answered),
        "score": average,
        "technical_strengths": strengths,
        "areas_to_improve": improvements,
        "topics_to_prepare": topics,
        "per_question": [
            {
                "question": str(p.get("question") or "").strip(),
                "answer": str(p.get("answer") or "").strip(),
                "score": p.get("score") if isinstance(p.get("score"), int) else None,
                "feedback": str(p.get("feedback") or "").strip(),
                "strengths": list(p.get("strengths") or [])[:4],
                "improvements": list(p.get("improvements") or [])[:4],
                "category": p.get("category") or "",
            }
            for p in pairs
        ],
        "score_note": SCORE_NOTE,
        "source": "offline",
        "provider": "offline",
        "notice": "",
        "raw": {},
    }
