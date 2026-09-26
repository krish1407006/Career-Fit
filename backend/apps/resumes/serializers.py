from rest_framework import serializers

from .models import Resume, ResumeAnalysis


class ResumeAnalysisSerializer(serializers.ModelSerializer):
    """Student-facing analysis payload.

    ``extracted_text`` and ``raw`` are intentionally never exposed: the resume
    text stays server-side and the raw provider payload is for auditing only.
    """

    resume_id = serializers.IntegerField(source="resume.id", read_only=True)
    resume_name = serializers.CharField(source="resume.original_name", read_only=True)
    score_note = serializers.CharField(read_only=True)
    has_analysis = serializers.SerializerMethodField()

    class Meta:
        model = ResumeAnalysis
        fields = [
            "id", "resume_id", "resume_name", "status", "has_analysis",
            "summary", "detected_skills", "strengths", "skill_gaps",
            "improvements", "recommended_roles", "education", "experience",
            "job_relevance", "score", "score_note", "source", "provider",
            "notice", "error_message", "analyzed_at", "updated_at",
        ]
        read_only_fields = fields

    def get_has_analysis(self, obj):
        return obj.is_completed


class ResumeSerializer(serializers.ModelSerializer):
    analysis = ResumeAnalysisSerializer(read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Resume
        fields = ["id", "original_name", "download_url", "status", "error_message",
                  "uploaded_at", "updated_at", "analysis"]

    def get_download_url(self, obj):
        request = self.context.get("request")
        if not obj.file:
            return None
        path = f"/api/resumes/{obj.id}/download/"
        return request.build_absolute_uri(path) if request else path


class ResumeUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ["id", "file", "original_name", "status", "uploaded_at"]
        read_only_fields = ["original_name", "status", "uploaded_at"]

    def validate_file(self, value):
        name = (getattr(value, "name", "") or "").lower()
        if not name.endswith(".pdf"):
            raise serializers.ValidationError("Only PDF files are supported.")
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size must be under 10 MB.")
        return value

    def create(self, validated_data):
        file = validated_data.pop("file")
        resume = Resume(**validated_data, original_name=file.name, file=file)
        resume.save()
        return resume