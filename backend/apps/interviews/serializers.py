from rest_framework import serializers

from .models import InterviewSession, InterviewTurn


class InterviewSessionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewSession
        fields = [
            "id", "position", "status", "question_index", "total_questions",
            "report", "created_at", "updated_at",
        ]


class InterviewTurnSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewTurn
        fields = ["id", "role", "kind", "content", "score", "feedback", "suggestions", "created_at"]


class InterviewSessionDetailSerializer(serializers.ModelSerializer):
    turns = InterviewTurnSerializer(many=True, read_only=True)

    class Meta:
        model = InterviewSession
        fields = [
            "id", "position", "status", "question_index", "total_questions",
            "report", "created_at", "updated_at", "turns",
        ]


class StartInterviewSerializer(serializers.Serializer):
    position = serializers.CharField(max_length=150, allow_blank=False)
    total_questions = serializers.IntegerField(min_value=1, max_value=10, default=5)

    def validate_position(self, value):
        if not value.strip():
            raise serializers.ValidationError("Position / role is required.")
        return value.strip()


class AnswerSerializer(serializers.Serializer):
    answer = serializers.CharField(allow_blank=False, max_length=20000)

    def validate_answer(self, value):
        if not value.strip():
            raise serializers.ValidationError("Answer cannot be empty.")
        return value.strip()