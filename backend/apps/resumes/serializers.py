from rest_framework import serializers

from .models import Resume, ResumeAnalysis


class ResumeAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumeAnalysis
        fields = ["skills", "summary", "education", "experience", "score",
                  "suggestions", "source", "analyzed_at"]


class ResumeSerializer(serializers.ModelSerializer):
    analysis = ResumeAnalysisSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Resume
        fields = ["id", "original_name", "file_url", "status", "error_message",
                  "uploaded_at", "updated_at", "analysis"]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not obj.file:
            return None
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url


class ResumeUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ["id", "file", "original_name", "status", "uploaded_at"]
        read_only_fields = ["original_name", "status", "uploaded_at"]

    def validate_file(self, value):
        name = (getattr(value, "name", "") or "").lower()
        if not name.endswith((".pdf", ".docx", ".txt")):
            raise serializers.ValidationError("Only PDF, DOCX or TXT files are supported.")
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size must be under 10 MB.")
        return value

    def create(self, validated_data):
        file = validated_data.pop("file")
        resume = Resume(**validated_data, original_name=file.name, file=file)
        resume.save()
        return resume