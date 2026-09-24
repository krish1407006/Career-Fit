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
    resume = models.OneToOneField(Resume, on_delete=models.CASCADE, related_name="analysis")
    skills = models.JSONField(default=list, blank=True)
    summary = models.TextField(blank=True)
    education = models.JSONField(default=list, blank=True)
    experience = models.JSONField(default=list, blank=True)
    score = models.PositiveSmallIntegerField(default=0)
    suggestions = models.JSONField(default=list, blank=True)
    source = models.CharField(max_length=20, default="offline")  # "ai" | "offline"
    raw = models.JSONField(default=dict, blank=True)
    analyzed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analysis for {self.resume.original_name}"