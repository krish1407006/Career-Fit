from django.contrib import admin

from .models import InterviewSession, InterviewTurn


class InterviewTurnInline(admin.TabularInline):
    model = InterviewTurn
    extra = 0


@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    list_display = ["student", "position", "status", "question_index", "total_questions", "created_at"]
    list_filter = ["status", "position"]
    inlines = [InterviewTurnInline]