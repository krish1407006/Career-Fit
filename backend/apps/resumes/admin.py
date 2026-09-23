from django.contrib import admin

from .models import Resume, ResumeAnalysis


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("user", "original_name", "status", "uploaded_at")
    list_filter = ("status", "uploaded_at")
    search_fields = ("user__username", "original_name")


@admin.register(ResumeAnalysis)
class ResumeAnalysisAdmin(admin.ModelAdmin):
    list_display = ("resume", "score", "source", "analyzed_at")
    search_fields = ("resume__user__username",)