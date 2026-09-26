from django.conf import settings
from django.db import models


class InterviewSession(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        # Retained for historical sessions created before Phase 7.
        ABORTED = "aborted", "Aborted"

    class Mode(models.TextChoices):
        VOICE = "voice", "Voice"
        TEXT = "text", "Text"

    class State(models.TextChoices):
        """Whose turn it is, so a reload can restore the exact conversation step."""

        PREPARING = "preparing", "Preparing interview"
        AI_SPEAKING = "ai_speaking", "AI is speaking"
        AWAITING_ANSWER = "awaiting_answer", "Your turn"
        LISTENING = "listening", "Listening"
        PROCESSING = "processing", "Processing answer"
        EVALUATING = "evaluating", "AI is evaluating"
        COMPLETED = "completed", "Interview completed"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="interview_sessions"
    )
    position = models.CharField(max_length=150)
    # Optional link to a real Job posting so questions can use its required skills.
    # SET_NULL keeps historic interviews readable when a recruiter deletes the job.
    job = models.ForeignKey(
        "jobs.Job", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="interview_sessions",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.TEXT)
    state = models.CharField(max_length=20, choices=State.choices, default=State.PREPARING)
    question_index = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=5)
    report = models.TextField(blank=True)
    # Structured Phase 7 report (summary, strengths, per-question feedback...).
    report_data = models.JSONField(default=dict, blank=True)
    # Student-safe message when a step failed; never a traceback or a provider detail.
    last_error = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["student", "status"])]

    def __str__(self):
        return f"{self.student} - {self.position} ({self.status})"

    @property
    def is_resumable(self):
        return self.status == self.Status.IN_PROGRESS

    @property
    def answered_count(self):
        return self.turns.filter(kind=InterviewTurn.Kind.ANSWER).count()


class InterviewTurn(models.Model):
    class Role(models.TextChoices):
        ASSISTANT = "assistant", "Assistant"
        USER = "user", "User"

    class Kind(models.TextChoices):
        QUESTION = "question", "Question"
        ANSWER = "answer", "Answer"
        EVALUATION = "evaluation", "Evaluation"

    session = models.ForeignKey(
        InterviewSession, on_delete=models.CASCADE, related_name="turns"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.QUESTION)
    content = models.TextField()
    score = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    suggestions = models.TextField(blank=True)
    # Full structured evaluation (technical_correctness, relevance, strengths...).
    evaluation = models.JSONField(default=dict, blank=True)
    # Browser-generated idempotency key: stops a double-clicked / re-sent answer
    # from being evaluated twice.
    client_token = models.CharField(max_length=64, blank=True, db_index=True)
    # How this question was produced, and which category it belongs to.
    category = models.CharField(max_length=40, blank=True)
    source = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "client_token"],
                condition=~models.Q(client_token=""),
                name="unique_interview_answer_client_token",
            )
        ]

    def __str__(self):
        return f"{self.role}:{self.kind} @ {self.session_id}"
