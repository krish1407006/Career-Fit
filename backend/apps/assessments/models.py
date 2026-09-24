from django.db import models

from apps.accounts.models import User


class Difficulty(models.TextChoices):
    EASY = "easy", "Easy"
    MEDIUM = "medium", "Medium"
    HARD = "hard", "Hard"


class Quiz(models.Model):
    class Category(models.TextChoices):
        PYTHON = "python", "Python"
        JAVASCRIPT = "javascript", "JavaScript"
        DJANGO = "django", "Django"
        SQL = "sql", "SQL"
        DBMS = "dbms", "DBMS"
        OPERATING_SYSTEMS = "operating_systems", "Operating Systems"
        COMPUTER_NETWORKS = "computer_networks", "Computer Networks"
        DATA_STRUCTURES = "data_structures", "Data Structures"
        APTITUDE = "aptitude", "Aptitude"
        LOGICAL_REASONING = "logical_reasoning", "Logical Reasoning"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.PYTHON)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, default=Difficulty.MEDIUM)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Leave blank for no time limit.")
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
    options = models.JSONField()  # list of strings (A, B, C, D...)
    correct_index = models.PositiveSmallIntegerField()
    explanation = models.TextField(blank=True)
    topic = models.CharField(max_length=120, blank=True)
    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, default=Difficulty.MEDIUM)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.text[:60]


class QuizAttempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quiz_attempts")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    answers = models.JSONField(default=dict, blank=True)  # {question_id: chosen_index}
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    correct_count = models.PositiveIntegerField(default=0)
    incorrect_count = models.PositiveIntegerField(default=0)
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


class QuizQuestionAnswer(models.Model):
    """One stored student answer, kept separate from the question's answer key."""

    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="question_answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="attempt_answers")
    chosen_index = models.PositiveSmallIntegerField(null=True, blank=True)
    is_correct = models.BooleanField(null=True, blank=True)

    class Meta:
        ordering = ["question_id"]
        constraints = [
            models.UniqueConstraint(fields=["attempt", "question"], name="unique_attempt_question_answer"),
        ]

    def __str__(self):
        return f"{self.attempt_id} -> Q{self.question_id}: {self.chosen_index}"