import os
import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import models

from apps.accounts.models import User


def resume_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower() or ".pdf"
    return os.path.join("resumes", str(instance.user_id), f"{uuid.uuid4().hex}{ext}")


class Resume(models.Model):
    class Status(models.TextChoices):
        PROCESSING = "processing", "Processing"
        ANALYZED = "analyzed", "Analyzed"
        FAILED = "failed", "Failed"
        UPLOADED = "uploaded", "Uploaded"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="resumes")
    file = models.FileField(upload_to=resume_upload_path)
    original_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UPLOADED)
    error_message = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.user.username}: {self.original_name} ({self.status})"

    def delete(self, *args, **kwargs):
        if self.file and default_storage.exists(self.file.name):
            default_storage.delete(self.file.name)
        super().delete(*args, **kwargs)


class ResumeAnalysis(models.Model):
    """Structured, AI-assisted feedback for one of the student's resumes.

    Phase 6 additions are the ``status``/``detected_skills``/``strengths``/
    ``skill_gaps``/``improvements``/``recommended_roles``/``job_relevance``/
    ``extracted_text``/``error_message``/``provider``/``notice``/``updated_at``
    fields. The Phase 1-5 fields (``skills``, ``summary``, ``education``,
    ``experience``, ``score``, ``suggestions``, ``source``, ``raw``,
    ``analyzed_at``) are kept so job matching and existing API consumers keep
    working unchanged.

    No student data is duplicated here: ownership is always derived through
    ``resume.user``.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    resume = models.OneToOneField(Resume, on_delete=models.CASCADE, related_name="analysis")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED)
    skills = models.JSONField(default=list, blank=True)
    detected_skills = models.JSONField(default=list, blank=True)
    summary = models.TextField(blank=True)
    education = models.JSONField(default=list, blank=True)
    experience = models.JSONField(default=list, blank=True)
    strengths = models.JSONField(default=list, blank=True)
    skill_gaps = models.JSONField(default=list, blank=True)
    score = models.PositiveSmallIntegerField(default=0)
    suggestions = models.JSONField(default=list, blank=True)
    improvements = models.JSONField(default=list, blank=True)
    recommended_roles = models.JSONField(default=list, blank=True)
    job_relevance = models.JSONField(default=dict, blank=True)
    extracted_text = models.TextField(blank=True)
    source = models.CharField(max_length=20, default="offline")  # "ai" | "offline"
    provider = models.CharField(max_length=40, blank=True)
    notice = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    raw = models.JSONField(default=dict, blank=True)
    analyzed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "resume analyses"

    def __str__(self):
        return f"Analysis for {self.resume.original_name}"

    @property
    def is_completed(self):
        return self.status == self.Status.COMPLETED

    @property
    def score_note(self):
        """Explicit disclaimer: the score describes the document, not hiring odds."""
        return "Resume quality indicator only. It is not a hiring probability."
