from django.db import models

from apps.accounts.models import User


class Skill(models.Model):
    name = models.CharField(max_length=120, unique=True)
    category = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Job(models.Model):
    class JobType(models.TextChoices):
        FULL_TIME = "full_time", "Full-time"
        PART_TIME = "part_time", "Part-time"
        INTERNSHIP = "internship", "Internship"
        CONTRACT = "contract", "Contract"

    recruiter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="jobs")
    company_name = models.CharField(max_length=200)
    title = models.CharField(max_length=160)
    description = models.TextField()
    responsibilities = models.JSONField(default=list, blank=True)
    skills_required = models.JSONField(default=list, blank=True)
    job_type = models.CharField(max_length=20, choices=JobType.choices, default=JobType.FULL_TIME)
    location = models.CharField(max_length=120)
    salary_range = models.CharField(max_length=120, blank=True)
    openings = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["is_active", "job_type"])]

    def __str__(self):
        return f"{self.title} @ {self.company_name}"


class JobApplication(models.Model):
    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        SHORTLISTED = "shortlisted", "Shortlisted"
        REJECTED = "rejected", "Rejected"
        SELECTED = "selected", "Selected"

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="job_applications")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)
    match_score = models.PositiveSmallIntegerField(default=0)
    cover_note = models.TextField(blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-applied_at"]
        constraints = [
            models.UniqueConstraint(fields=["student", "job"], name="unique_student_job_application"),
        ]

    def __str__(self):
        return f"{self.student.username} -> {self.job.title}"