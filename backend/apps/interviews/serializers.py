import re

from rest_framework import serializers

from .models import InterviewSession, InterviewTurn

_CLIENT_TOKEN_RE = re.compile(r"^[A-Za-z0-9._:-]{8,64}$")


class InterviewTurnSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewTurn
        fields = [
            "id", "role", "kind", "content", "score", "feedback", "suggestions",
            "evaluation", "category", "source", "created_at",
        ]
        read_only_fields = fields


class InterviewSessionListSerializer(serializers.ModelSerializer):
    answered_count = serializers.IntegerField(read_only=True)
    is_resumable = serializers.BooleanField(read_only=True)

    class Meta:
        model = InterviewSession
        fields = [
            "id", "position", "job", "status", "mode", "state", "question_index",
            "total_questions", "answered_count", "is_resumable", "report",
            "created_at", "updated_at", "started_at", "completed_at",
        ]
        read_only_fields = fields


class InterviewSessionDetailSerializer(InterviewSessionListSerializer):
    turns = InterviewTurnSerializer(many=True, read_only=True)
    # Current question the student must answer, or null when it is their turn to
    # speak nothing / the interview is finished. Drives the resume flow.
    current_question = serializers.SerializerMethodField()

    class Meta(InterviewSessionListSerializer.Meta):
        fields = InterviewSessionListSerializer.Meta.fields + [
            "turns", "current_question", "last_error", "report_data",
        ]
        read_only_fields = fields

    def get_current_question(self, obj):
        from .services import _pending_question

        turn = _pending_question(obj)
        if turn is None:
            return None
        return {
            "turn_id": turn.id,
            "content": turn.content,
            "category": turn.category,
            "source": turn.source,
        }


class StartInterviewSerializer(serializers.Serializer):
    position = serializers.CharField(max_length=150, allow_blank=False)
    total_questions = serializers.IntegerField(min_value=1, max_value=10, default=5)
    job = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    mode = serializers.ChoiceField(
        choices=InterviewSession.Mode.choices,
        default=InterviewSession.Mode.TEXT,
    )
    # Return the in-progress session instead of raising 409.
    resume = serializers.BooleanField(required=False, default=False)

    def validate_position(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Target role is required.")
        return value

    def validate_job(self, value):
        # The job only supplies question context; session authorisation always
        # comes from the authenticated student, never from this value.
        return value


class AnswerSerializer(serializers.Serializer):
    answer = serializers.CharField(allow_blank=False, max_length=20000)
    client_token = serializers.CharField(required=False, allow_blank=True, max_length=64)

    def validate_answer(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Answer cannot be empty.")
        return value

    def validate_client_token(self, value):
        value = (value or "").strip()
        if value and not _CLIENT_TOKEN_RE.match(value):
            raise serializers.ValidationError(
                "client_token may only contain letters, digits and . _ : - (8-64 chars)."
            )
        return value


class CompleteInterviewSerializer(serializers.Serializer):
    """Body is optional; present so the endpoint accepts `{}` or nothing."""


class InterviewReportSerializer(serializers.Serializer):
    """Read-only projection of the stored structured report."""

    id = serializers.IntegerField(read_only=True)
    position = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    mode = serializers.CharField(read_only=True)
    questions_answered = serializers.IntegerField(read_only=True)
    summary = serializers.CharField(read_only=True)
    score = serializers.IntegerField(read_only=True, allow_null=True)
    technical_strengths = serializers.ListField(child=serializers.CharField(), read_only=True)
    areas_to_improve = serializers.ListField(child=serializers.CharField(), read_only=True)
    topics_to_prepare = serializers.ListField(child=serializers.CharField(), read_only=True)
    per_question = serializers.ListField(read_only=True)
    score_note = serializers.CharField(read_only=True)
    source = serializers.CharField(read_only=True)
    notice = serializers.CharField(read_only=True)
    completed_at = serializers.DateTimeField(read_only=True)
