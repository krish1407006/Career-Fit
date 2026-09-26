"""Interview orchestration (Phase 7).

Views stay thin: they resolve the *authenticated* student, delegate here, and
serialise the result. This module owns session lifecycle rules (no duplicate
sessions, no duplicate answers, resumability) and calls
:mod:`apps.ai.interview_service` for all question/evaluation/report work, so an
AI key, HTTP payload or provider traceback can never reach a view or a client.
"""

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.ai import interview_service
from apps.ai.errors import AiError

from .models import InterviewSession, InterviewTurn

logger = logging.getLogger(__name__)

# Fixed, student-safe messages. Never interpolate a provider exception here.
GENERIC_AI_ERROR = (
    "The AI interviewer is temporarily unavailable. Your answer was saved - "
    "please try again."
)
QUESTION_ERROR = (
    "We could not prepare the next question right now. Your answer was saved - "
    "please try again."
)
REPORT_ERROR = "We could not build the interview report right now. Please try again."
NO_ACTIVE_SESSION = "You already have an interview in progress. Resume it or end it first."


class InterviewError(Exception):
    """Business-rule failure with a message that is safe to return to the student."""

    def __init__(self, message, code="invalid_request", status=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


def active_session(user):
    """The student's resumable session, if any (newest wins)."""
    return (
        InterviewSession.objects.filter(
            student=user, status=InterviewSession.Status.IN_PROGRESS
        )
        .order_by("-updated_at", "-id")
        .first()
    )


def _resolve_job(user, job_id):
    """Look up a target job. Ownership of the *session* is what authorises the
    interview; a job id only supplies context, so any active published job is
    acceptable and a bad id is ignored rather than fatal."""
    if not job_id:
        return None
    from apps.jobs.models import Job

    return (
        Job.objects.filter(pk=job_id, is_active=True)
        .select_related("recruiter")
        .prefetch_related("required_skills", "preferred_skills")
        .first()
    )


def _context_for(session):
    return interview_service.build_context(
        session.student, job=session.job, position=session.position
    )


def _next_question(session, require_ai=False):
    """Generate and store the next question turn. Returns the question dict."""
    transcript = list(
        session.turns.filter(
            kind__in=[InterviewTurn.Kind.QUESTION, InterviewTurn.Kind.ANSWER]
        ).values("role", "kind", "content")
    )
    payload = interview_service.generate_question(
        context=_context_for(session),
        position=session.position,
        transcript=transcript,
        index=session.question_index,
        total=session.total_questions,
        require_ai=require_ai,
    )
    turn = InterviewTurn.objects.create(
        session=session,
        role=InterviewTurn.Role.ASSISTANT,
        kind=InterviewTurn.Kind.QUESTION,
        content=payload["question"],
        category=payload.get("category", ""),
        source=payload.get("source", ""),
    )
    session.state = InterviewSession.State.AWAITING_ANSWER
    return payload, turn


def start_session(user, *, position, total_questions, job_id=None, mode=None,
                  resume=False, require_ai=False):
    """Start a new interview, or return the student's existing in-progress one.

    Raises :class:`InterviewError` with ``status=409`` when a session is already
    running, so a student can never end up with two concurrent interviews (or
    two concurrent AI conversations) by double-clicking.
    """
    position = (position or "").strip()
    if not position:
        raise InterviewError("Target role is required.", code="position_required")

    total_questions = max(1, min(10, int(total_questions or 5)))
    mode = mode if mode in dict(InterviewSession.Mode.choices) else InterviewSession.Mode.TEXT

    existing = active_session(user)
    if existing is not None:
        if resume:
            return existing, False
        raise InterviewError(
            NO_ACTIVE_SESSION, code="interview_in_progress", status=409
        )

    job = _resolve_job(user, job_id)
    now = timezone.now()
    session = InterviewSession.objects.create(
        student=user,
        position=position,
        job=job,
        total_questions=total_questions,
        mode=mode,
        state=InterviewSession.State.PREPARING,
        question_index=0,
        started_at=now,
    )
    try:
        _next_question(session, require_ai=require_ai)
    except AiError:
        # The session row must not be left stranded in "preparing".
        InterviewSession.objects.filter(pk=session.pk).delete()
        raise InterviewError(GENERIC_AI_ERROR, code="ai_unavailable", status=503)
    session.save(update_fields=["state", "updated_at"])
    return session, True


def resume_session(session, require_ai=False):
    """Restore a resumable session, regenerating a question if one is missing."""
    if not session.is_resumable:
        raise InterviewError(
            "This interview is no longer in progress.",
            code="not_in_progress",
            status=400,
        )
    has_question = session.turns.filter(kind=InterviewTurn.Kind.QUESTION).exists()
    if not has_question:
        try:
            _next_question(session, require_ai=require_ai)
            session.save(update_fields=["state", "updated_at"])
        except AiError:
            raise InterviewError(GENERIC_AI_ERROR, code="ai_unavailable", status=503)
    elif session.state == InterviewSession.State.PREPARING:
        session.state = InterviewSession.State.AWAITING_ANSWER
        session.save(update_fields=["state", "updated_at"])
    return session


def _already_answered(session, client_token):
    if not client_token:
        return None
    return session.turns.filter(kind=InterviewTurn.Kind.ANSWER, client_token=client_token).first()


def submit_answer(session, answer, client_token="", require_ai=False):
    """Store one answer, evaluate it, then continue or complete the interview.

    Duplicate protection: the same ``client_token`` never produces a second
    answer turn, so a retried/double-submitted request is answered with the
    original result instead of double-evaluating.
    """
    if not session.is_resumable:
        raise InterviewError(
            "This interview is not in progress, so no more answers can be added.",
            code="interview_closed",
            status=400,
        )

    answer = (answer or "").strip()
    if not answer:
        raise InterviewError("Answer cannot be empty.", code="answer_required")

    previous = _already_answered(session, client_token)
    if previous is not None:
        evaluation = _evaluation_payload(previous)
        return {
            "duplicate": True,
            "evaluation": evaluation,
            "next_question": _pending_content(session),
            "question_index": session.question_index,
            "total_questions": session.total_questions,
            "completed": not session.is_resumable,
            "session": session,
        }

    pending = _pending_question(session)
    question = pending.content if pending else "Tell me about yourself."

    InterviewSession.objects.filter(pk=session.pk).update(
        state=InterviewSession.State.PROCESSING
    )

    try:
        with transaction.atomic():
            answer_turn = InterviewTurn.objects.create(
                session=session,
                role=InterviewTurn.Role.USER,
                kind=InterviewTurn.Kind.ANSWER,
                content=answer,
                client_token=client_token or "",
            )
    except IntegrityError:
        # Lost a race against a concurrent identical submission.
        session.refresh_from_db()
        existing = _already_answered(session, client_token)
        return {
            "duplicate": True,
            "evaluation": _evaluation_payload(existing) if existing else {},
            "next_question": _pending_content(session),
            "question_index": session.question_index,
            "total_questions": session.total_questions,
            "completed": not session.is_resumable,
            "session": session,
        }

    session.state = InterviewSession.State.EVALUATING
    session.save(update_fields=["state", "updated_at"])

    try:
        evaluation = interview_service.evaluate_answer(
            context=_context_for(session),
            position=session.position,
            question=question,
            answer=answer,
            require_ai=require_ai,
        )
    except AiError:
        # The transcript is already saved, so the student can retry safely.
        session.last_error = GENERIC_AI_ERROR
        session.state = InterviewSession.State.AWAITING_ANSWER
        session.save(update_fields=["last_error", "state", "updated_at"])
        raise InterviewError(
            GENERIC_AI_ERROR, code="evaluation_unavailable", status=503
        )

    InterviewTurn.objects.create(
        session=session,
        role=InterviewTurn.Role.ASSISTANT,
        kind=InterviewTurn.Kind.EVALUATION,
        content=evaluation.get("feedback", ""),
        score=evaluation.get("score"),
        feedback=evaluation.get("feedback", ""),
        suggestions=" ".join(evaluation.get("improvements") or [])[:2000],
        evaluation=_evaluation_payload(evaluation),
        source=evaluation.get("source", ""),
    )

    session.question_index += 1
    session.last_error = ""

    if session.question_index >= session.total_questions:
        complete_session(session, require_ai=require_ai)
        return {
            "duplicate": False,
            "evaluation": _evaluation_payload(evaluation),
            "next_question": "",
            "question_index": session.question_index,
            "total_questions": session.total_questions,
            "completed": True,
            "session": session,
        }

    try:
        _next_question(session, require_ai=require_ai)
    except AiError:
        # Answer + evaluation are safe; only the follow-up failed.
        session.state = InterviewSession.State.AWAITING_ANSWER
        session.save(update_fields=["state", "updated_at"])
        raise InterviewError(
            QUESTION_ERROR, code="question_unavailable", status=503
        )
    session.save(update_fields=["question_index", "state", "updated_at"])
    return {
        "duplicate": False,
        "evaluation": _evaluation_payload(evaluation),
        "next_question": session.turns.filter(kind=InterviewTurn.Kind.QUESTION).last().content,
        "question_index": session.question_index,
        "total_questions": session.total_questions,
        "completed": False,
        "session": session,
    }


def complete_session(session, require_ai=False):
    """Mark the interview completed and build the structured practice report."""
    if session.status == InterviewSession.Status.COMPLETED and session.report_data:
        return session

    pairs = _question_answer_pairs(session)
    try:
        report = interview_service.build_report(
            context=_context_for(session),
            position=session.position,
            per_question=pairs,
            require_ai=require_ai,
        )
    except AiError:
        raise InterviewError(REPORT_ERROR, code="report_unavailable", status=503)

    session.status = InterviewSession.Status.COMPLETED
    session.state = InterviewSession.State.COMPLETED
    session.completed_at = timezone.now()
    session.report = report.get("summary", "")[:5000]
    session.report_data = report
    session.save(
        update_fields=[
            "status", "state", "completed_at", "report", "report_data", "updated_at",
        ]
    )
    return session


def cancel_session(session):
    session.status = InterviewSession.Status.CANCELLED
    session.completed_at = timezone.now()
    session.save(update_fields=["status", "completed_at", "updated_at"])
    return session


def _question_answer_pairs(session):
    """Pair each question with the answer and evaluation that followed it."""
    pairs, current = [], None
    for turn in session.turns.select_related(None).order_by("created_at", "id"):
        if turn.kind == InterviewTurn.Kind.QUESTION:
            current = {
                "question": turn.content,
                "category": turn.category or "",
                "answer": "",
                "score": None,
                "feedback": "",
                "strengths": [],
                "improvements": [],
            }
            pairs.append(current)
        elif turn.kind == InterviewTurn.Kind.ANSWER and current is not None:
            current["answer"] = turn.content
        elif turn.kind == InterviewTurn.Kind.EVALUATION and current is not None:
            payload = turn.evaluation or {}
            current["score"] = turn.score if turn.score is not None else payload.get("score")
            current["feedback"] = turn.feedback or turn.content
            current["strengths"] = payload.get("strengths") or []
            current["improvements"] = payload.get("improvements") or (
                [turn.suggestions] if turn.suggestions else []
            )
    return pairs


def _pending_question(session):
    """The question the student is currently answering, if any.

    Walks the ordered turns: the pending question is the last one that has no
    answer turn after it.
    """
    last_question = None
    answered = False
    for turn in session.turns.order_by("created_at", "id").only("kind"):
        if turn.kind == InterviewTurn.Kind.QUESTION:
            last_question = turn
            answered = False
        elif turn.kind == InterviewTurn.Kind.ANSWER and last_question is not None:
            answered = True
    if last_question is not None and not answered:
        return last_question
    return None


def _pending_content(session):
    """Text of the question the student still owes an answer to (or "")."""
    turn = _pending_question(session)
    return turn.content if turn is not None else ""


def _evaluation_payload(evaluation):
    """Public evaluation shape: structured fields only, no provider payload.

    Accepts either a raw evaluation dict or a stored evaluation turn (used when
    replaying a duplicate submission).
    """
    if not evaluation:
        return {}
    if isinstance(evaluation, InterviewTurn):
        stored = evaluation.evaluation or {}
        return {
            "score": evaluation.score if evaluation.score is not None else stored.get("score"),
            "technical_correctness": stored.get("technical_correctness", ""),
            "relevance": stored.get("relevance", ""),
            "clarity": stored.get("clarity", ""),
            "completeness": stored.get("completeness", ""),
            "strengths": stored.get("strengths") or [],
            "improvements": stored.get("improvements") or [],
            "feedback": evaluation.feedback or evaluation.content or "",
            "source": evaluation.source or "",
            "notice": stored.get("notice", ""),
        }
    return {
        "score": evaluation.get("score"),
        "technical_correctness": evaluation.get("technical_correctness", ""),
        "relevance": evaluation.get("relevance", ""),
        "clarity": evaluation.get("clarity", ""),
        "completeness": evaluation.get("completeness", ""),
        "strengths": evaluation.get("strengths") or [],
        "improvements": evaluation.get("improvements") or [],
        "feedback": evaluation.get("feedback", ""),
        "source": evaluation.get("source", ""),
        "notice": evaluation.get("notice", ""),
    }

