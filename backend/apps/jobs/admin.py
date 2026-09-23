from django.contrib import admin

from .models import Job, JobApplication, Skill


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category")
    search_fields = ("name",)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "company_name", "recruiter", "job_type", "is_active", "created_at")
    list_filter = ("job_type", "is_active")
    search_fields = ("title", "company_name")


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ("student", "job", "status", "match_score", "applied_at")
    list_filter = ("status",)
    search_fields = ("student__username", "job__title", "job__company_name")