from rest_framework import serializers

from .models import Question, Quiz, QuizAttempt

PASS_THRESHOLD = 60


# ---------------------------------------------------------------- helpers
def build_review(attempt):
    """Per-question review for a stored attempt (safe: includes the answer key,
    so it is only surfaced AFTER the attempt is submitted)."""
    questions = list(attempt.quiz.questions.all())
    answers = attempt.answers or {}
    rows = []
    for q in questions:
        chosen = answers.get(str(q.id))
        try:
            chosen = int(chosen) if chosen is not None else None
        except (TypeError, ValueError):
            chosen = None
        if chosen is not None and not (0 <= chosen < len(q.options)):
            chosen = None
        rows.append({
            "question_id": q.id,
            "text": q.text,
            "options": q.options,
            "chosen_index": chosen,
            "correct_index": q.correct_index,
            "is_correct": chosen is not None and chosen == q.correct_index,
            "explanation": q.explanation,
        })
    return rows


# ---------------------------------------------------------------- questions
class QuestionSerializer(serializers.ModelSerializer):
    """Full question including the answer key (admin / post-submission review)."""

    quiz_id = serializers.IntegerField(source="quiz.id", read_only=True)

    class Meta:
        model = Question
        fields = ["id", "quiz_id", "text", "options", "correct_index",
                  "explanation", "topic", "difficulty"]


class QuestionAdminSerializer(serializers.ModelSerializer):
    """Write serializer for admin question CRUD."""

    class Meta:
        model = Question
        fields = ["id", "quiz", "text", "options", "correct_index",
                  "explanation", "topic", "difficulty"]

    def validate(self, attrs):
        options = attrs.get("options")
        correct = attrs.get("correct_index")
        if options is None:
            if self.instance is None:
                raise serializers.ValidationError({"options": "options are required."})
        else:
            options = list(options)
            if len(options) < 2:
                raise serializers.ValidationError({"options": "At least 2 options are required."})
            attrs["options"] = options
        if correct is not None:
            reference = options if options is not None else getattr(self.instance, "options", None)
            if reference is None:
                raise serializers.ValidationError(
                    {"correct_index": "correct_index must point inside options."})
            try:
                ci = int(correct)
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    {"correct_index": "correct_index must be an integer."})
            if not (0 <= ci < len(reference)):
                raise serializers.ValidationError(
                    {"correct_index": "correct_index must point inside options."})
        return attrs


class QuestionReadSerializer(serializers.ModelSerializer):
    """Question as shown during the attempt: NO answer key."""

    class Meta:
        model = Question
        fields = ["id", "text", "options", "topic", "difficulty"]


# ---------------------------------------------------------------- quizzes
class QuizListSerializer(serializers.ModelSerializer):
    total_questions = serializers.SerializerMethodField()
    attempted = serializers.SerializerMethodField()
    attempt_id = serializers.SerializerMethodField()
    score_percent = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = ["id", "title", "description", "category", "difficulty",
                  "duration_minutes", "total_questions", "is_active",
                  "attempted", "attempt_id", "score_percent"]

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
    """Quiz meta only - never includes questions/answers for students."""

    total_questions = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = ["id", "title", "description", "category", "difficulty",
                  "duration_minutes", "total_questions", "is_active",
                  "created_at", "updated_at"]

    def get_total_questions(self, obj):
        return getattr(obj, "total_questions", None) or obj.questions.count()


class QuizAdminDetailSerializer(serializers.ModelSerializer):
    """Admin view of a quiz incl. the full question list with answers."""

    questions = QuestionSerializer(many=True, read_only=True)
    total_questions = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = ["id", "title", "description", "category", "difficulty",
                  "duration_minutes", "total_questions", "is_active",
                  "created_by", "created_at", "updated_at", "questions"]

    def get_total_questions(self, obj):
        return getattr(obj, "total_questions", None) or obj.questions.count()


# ---------------------------------------------------------------- attempts
class QuestionResultSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    text = serializers.CharField()
    options = serializers.ListField(child=serializers.CharField())
    chosen_index = serializers.IntegerField(allow_null=True)
    correct_index = serializers.IntegerField()
    is_correct = serializers.BooleanField()
    explanation = serializers.CharField()


class QuizAttemptSerializer(serializers.ModelSerializer):
    """History row for a student's attempts."""

    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    quiz_category = serializers.CharField(source="quiz.category", read_only=True)
    quiz_difficulty = serializers.CharField(source="quiz.difficulty", read_only=True)

    class Meta:
        model = QuizAttempt
        fields = ["id", "quiz", "quiz_title", "quiz_category", "quiz_difficulty",
                  "status", "correct_count", "incorrect_count", "total",
                  "score_percent", "started_at", "submitted_at"]


class QuizAttemptDetailSerializer(serializers.ModelSerializer):
    """Single attempt incl. per-question review (only for completed attempts)."""

    quiz_title = serializers.CharField(source="quiz.title", read_only=True)
    quiz_category = serializers.CharField(source="quiz.category", read_only=True)
    quiz_difficulty = serializers.CharField(source="quiz.difficulty", read_only=True)
    passed = serializers.SerializerMethodField()
    score_percent = serializers.SerializerMethodField()
    per_question = serializers.SerializerMethodField()

    class Meta:
        model = QuizAttempt
        fields = ["id", "quiz", "quiz_title", "quiz_category", "quiz_difficulty",
                  "status", "correct_count", "incorrect_count", "total",
                  "score_percent", "passed", "started_at", "submitted_at",
                  "per_question"]

    def get_passed(self, obj):
        return obj.status == QuizAttempt.Status.COMPLETED and obj.score_percent >= PASS_THRESHOLD

    def get_score_percent(self, obj):
        if obj.status != QuizAttempt.Status.COMPLETED:
            return None
        return obj.score_percent

    def get_per_question(self, obj):
        if obj.status != QuizAttempt.Status.COMPLETED:
            return []
        return build_review(obj)