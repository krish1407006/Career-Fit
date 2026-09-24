from django.contrib import admin

from .models import Certification, Education, Project


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ["degree", "institution", "profile", "end_year"]
    list_filter = ["is_current"]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "profile"]


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ["name", "issuer", "profile", "issue_date"]