from django.db import models

from apps.accounts.models import User


class Quiz(models.Model):
    class Category(models.TextChoices):
        TECHNICAL = "technical", "Technical"
        APTITUDE = "aptitude", "Aptitude"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.TECHNICAL)
    duration_minutes = models.PositiveIntegerField(default=15)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="quizzes_created")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.CharField(max_length=500)
    options = models.JSONField()  # list of strings
    correct_index = models.PositiveSmallIntegerField()
    explanation = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.text[:60]


class QuizAttempt(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quiz_attempts")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    answers = models.JSONField(default=dict, blank=True)  # {question_id: chosen_index}
    correct_count = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)
    score_percent = models.PositiveSmallIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(fields=["student", "quiz"], name="unique_student_quiz_attempt"),
        ]

    def __str__(self):
        return f"{self.student.username} -> {self.quiz.title} ({self.score_percent}%)"