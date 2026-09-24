from django.contrib import admin

from .models import Question, Quiz, QuizAttempt, QuizQuestionAnswer


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "difficulty", "duration_minutes", "is_active",
                    "question_count", "created_by", "created_at")
    list_filter = ("category", "difficulty", "is_active")
    search_fields = ("title", "description")
    inlines = [QuestionInline]

    @admin.display(description="Questions")
    def question_count(self, obj):
        return obj.questions.count()


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "quiz", "difficulty", "topic", "correct_index")
    list_filter = ("quiz", "difficulty")
    search_fields = ("text", "topic")


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("student", "quiz", "status", "correct_count", "incorrect_count",
                    "total", "score_percent", "submitted_at")
    list_filter = ("quiz__category", "quiz__difficulty", "status")
    search_fields = ("student__username", "quiz__title")
    readonly_fields = ("answers",)


@admin.register(QuizQuestionAnswer)
class QuizQuestionAnswerAdmin(admin.ModelAdmin):
    list_display = ("attempt", "question", "chosen_index", "is_correct")
    search_fields = ("attempt__student__username",)
    readonly_fields = ("attempt", "question", "chosen_index", "is_correct")