from django.contrib import admin

from .models import Question, Quiz, QuizAttempt


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "duration_minutes", "is_active", "created_by")
    list_filter = ("category", "is_active")
    search_fields = ("title",)
    inlines = [QuestionInline]


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("student", "quiz", "correct_count", "total", "score_percent", "submitted_at")
    list_filter = ("quiz__category",)
    search_fields = ("student__username", "quiz__title")