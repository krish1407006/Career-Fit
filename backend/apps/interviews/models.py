from django.conf import settings
from django.db import models


class InterviewSession(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        ABORTED = "aborted", "Aborted"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="interview_sessions"
    )
    position = models.CharField(max_length=150)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    question_index = models.IntegerField(default=0)
    total_questions = models.IntegerField(default=5)
    report = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student} - {self.position} ({self.status})"


class InterviewTurn(models.Model):
    class Role(models.TextChoices):
        ASSISTANT = "assistant", "Assistant"
        USER = "user", "User"

    session = models.ForeignKey(
        InterviewSession, on_delete=models.CASCADE, related_name="turns"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    kind = models.CharField(max_length=20, default="question")  # question | answer | evaluation
    content = models.TextField()
    score = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    suggestions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.role}:{self.kind} @ {self.session_id}"