from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models


class UserManager(DjangoUserManager):
    """Default manager that pins superuser/admin accounts to the admin role."""

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        RECRUITER = "recruiter", "Recruiter"
        ADMIN = "admin", "Admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    role_label = None  # explicit marker so permissions read `role`, never a stale label
    phone = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_recruiter(self):
        return self.role == self.Role.RECRUITER

    @property
    def is_admin_role(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    def __str__(self):
        return f"{self.username} ({self.role})"


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    full_name = models.CharField(max_length=150)
    college = models.CharField(max_length=150, blank=True)
    degree = models.CharField(max_length=150, blank=True)
    branch = models.CharField(max_length=120, blank=True)
    graduation_year = models.PositiveIntegerField(null=True, blank=True)
    cgpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    location = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)
    preferred_roles = models.JSONField(default=list, blank=True)
    preferred_technologies = models.JSONField(default=list, blank=True)
    skills = models.ManyToManyField("jobs.Skill", related_name="student_profiles", blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name or self.user.username


class SuperAdminEmail(models.Model):
    """An email address that is granted admin access.

    Any signed-in account whose email appears here is treated as an admin. This
    is the "super email" switch: it survives the account being deleted, and it
    lets a second person be given admin rights without sharing a password.

    Because an entry here is full admin access, the list is deliberately
    auditable: every addition records who added it and when.
    """

    email = models.EmailField(unique=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="super_emails_added",
    )
    note = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "super admin email"
        verbose_name_plural = "super admin emails"

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Addresses are compared case-insensitively, so normalise on the way in
        # or "Admin@x.com" and "admin@x.com" would both be accepted.
        if self.email:
            self.email = self.email.strip().lower()
        return super().save(*args, **kwargs)


class RecruiterProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="recruiter_profile")
    company_name = models.CharField(max_length=200)
    location = models.CharField(max_length=120, blank=True)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name or self.user.username