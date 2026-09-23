from rest_framework import serializers

from .models import Question, Quiz, QuizAttempt


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ["id", "text", "options", "correct_index", "explanation"]


class QuestionReadSerializer(serializers.ModelSerializer):
    """Question without answer key (for the student during the attempt)."""

    class Meta:
        model = Question
        fields = ["id", "text", "options"]


class QuizListSerializer(serializers.ModelSerializer):
    total_questions = serializers.SerializerMethodField()
    attempted = serializers.SerializerMethodField()
    attempt_id = serializers.SerializerMethodField()
    score_percent = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = ["id", "title", "description", "category", "duration_minutes",
                  "total_questions", "is_active", "attempted", "attempt_id", "score_percent"]

    def get_total_questions(self, obj):
        return getattr(obj, "total_questions", None) or obj.questions.count()

    def get_attempted(self, obj):
        return getattr(obj, "_attempt", None) is not None

    def get_attempt_id(self, obj):
        att = getattr(obj, "_attempt", None)
        return att.id if att else None

    def get_score_percent(self, obj):
        att = getattr(obj, "_attempt", None)
        return att.score_percent if att and att.submitted_at else None


class QuizDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    total_questions = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = ["id", "title", "description", "category", "duration_minutes",
                  "total_questions", "created_at", "questions"]

    def get_total_questions(self, obj):
        return getattr(obj, "total_questions", None) or obj.questions.count()


class QuizStartSerializer(serializers.Serializer):
    attempt_id = serializers.IntegerField()
    quiz = QuizDetailSerializer(read_only=True)
    questions = QuestionReadSerializer(many=True, read_only=True)
    countdown_seconds = serializers.IntegerField()


class QuestionResultSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    correct_index = serializers.IntegerField()
    your_index = serializers.IntegerField()
    is_correct = serializers.BooleanField()
    explanation = serializers.CharField()


class QuizSubmitResultSerializer(serializers.Serializer):
    attempt_id = serializers.IntegerField()
    correct_count = serializers.IntegerField()
    total = serializers.IntegerField()
    score_percent = serializers.IntegerField()
    passed = serializers.BooleanField()
    per_question = QuestionResultSerializer(many=True)


class QuizAttemptSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    quiz_category = serializers.CharField(source="quiz.category", read_only=True)

    class Meta:
        model = QuizAttempt
        fields = ["id", "quiz", "quiz_title", "quiz_category", "correct_count",
                  "total", "score_percent", "started_at", "submitted_at"]