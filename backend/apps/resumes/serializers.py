from django.conf import settings
from rest_framework import serializers

from .models import Resume, ResumeAnalysis

# Every PDF starts with this header. The specification allows a little junk in
# front of it, so a small run of whitespace is tolerated before the check.
PDF_MAGIC = b"%PDF-"
PDF_MAGIC_SEARCH_WINDOW = 1024


def _looks_like_pdf(head: bytes) -> bool:
    return PDF_MAGIC in head[:PDF_MAGIC_SEARCH_WINDOW]


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


class AdminResumeSerializer(ResumeSerializer):
    """A resume row on the admin inspection screen.

    Adds the owner so an admin can tell whose upload (and whose analysis) they
    are looking at without cross-referencing another screen.
    """

    student_id = serializers.IntegerField(source="user.id", read_only=True)
    student_username = serializers.CharField(source="user.username", read_only=True)
    student_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta(ResumeSerializer.Meta):
        fields = ResumeSerializer.Meta.fields + [
            "student_id", "student_username", "student_email",
        ]


class ResumeUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ["id", "file", "original_name", "status", "uploaded_at"]
        read_only_fields = ["original_name", "status", "uploaded_at"]

    def validate_file(self, value):
        """Reject anything that is not really a PDF, before it reaches storage.

        The extension and the browser supplied content type are both attacker
        controlled: a file called ``resume.pdf`` can contain anything at all.
        Without a content check such a file is stored and later streamed back
        from the download endpoint, so the real bytes are what has to be
        verified, not the name.
        """
        name = (getattr(value, "name", "") or "").lower()
        if not name.endswith(".pdf"):
            raise serializers.ValidationError("Only PDF files are supported.")

        max_bytes = getattr(settings, "MAX_RESUME_UPLOAD_BYTES", 10 * 1024 * 1024)
        if value.size > max_bytes:
            raise serializers.ValidationError(
                f"File size must be under {max_bytes // (1024 * 1024)} MB."
            )
        if value.size == 0:
            raise serializers.ValidationError("The file is empty.")

        # Read the head without consuming the stream, then rewind so the
        # analysis step still sees the file from the beginning.
        position = value.tell()
        head = value.read(len(PDF_MAGIC) + PDF_MAGIC_SEARCH_WINDOW)
        value.seek(position)
        if not _looks_like_pdf(head):
            raise serializers.ValidationError(
                "That file is not a PDF. Its contents do not start with a PDF header."
            )
        return value

    def create(self, validated_data):
        file = validated_data.pop("file")
        resume = Resume(**validated_data, original_name=file.name, file=file)
        resume.save()
        return resume