from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainSerializer

from .models import RecruiterProfile, StudentProfile, User


class LoginSerializer(TokenObtainSerializer):
    """Login serializer whose error message is actually true.

    SimpleJWT raises ``no_active_account`` whenever ``authenticate()`` returns
    ``None``, which also covers a perfectly valid account with a wrong password.
    Telling the student their account does not exist pushes them into registering
    a duplicate. This wording covers both cases without revealing which one it
    was, so username enumeration stays closed.
    """

    default_error_messages = {
        **TokenObtainSerializer.default_error_messages,
        "no_active_account": "Incorrect username or password. Please try again.",
    }


class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = [
            "full_name", "college", "degree", "branch", "graduation_year",
            "cgpa", "phone", "location", "bio", "preferred_roles",
            "preferred_technologies",
        ]


class RecruiterProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecruiterProfile
        fields = ["company_name", "website", "description", "location"]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "role",
                  "phone", "is_student", "is_recruiter", "is_admin_role"]


class AdminUserSerializer(serializers.ModelSerializer):
    """Everything an admin needs to identify an account on one screen."""

    full_name = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    related_counts = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "full_name",
                  "phone", "role", "is_active", "is_staff", "date_joined",
                  "last_login", "company_name", "related_counts"]

    def get_full_name(self, obj):
        return (f"{obj.first_name} {obj.last_name}").strip()

    def get_company_name(self, obj):
        profile = getattr(obj, "recruiter_profile", None)
        return profile.company_name if profile else ""

    def get_related_counts(self, obj):
        """What deleting this account will take with it."""
        counts = {
            "resumes": 0, "applications": 0, "interviews": 0,
            "quiz_attempts": 0, "jobs": 0,
        }
        # Collected here rather than by annotating the queryset so the serializer
        # stays usable for a single object too.
        for attr, key in (
            ("resumes", "resumes"), ("applications", "applications"),
            ("interview_sessions", "interviews"), ("quiz_attempts", "quiz_attempts"),
        ):
            related = getattr(obj, attr, None)
            if related is not None and hasattr(related, "count"):
                counts[key] = related.count()
        if obj.role == User.Role.RECRUITER:
            related = getattr(obj, "jobs", None)
            if related is not None and hasattr(related, "count"):
                counts["jobs"] = related.count()
        return counts


class UserAdminUpdateSerializer(serializers.ModelSerializer):
    """Admin editing of a user: change role and/or activation state."""

    role = serializers.ChoiceField(choices=User.Role.choices)

    class Meta:
        model = User
        fields = ["role", "is_active"]

    def update(self, instance, validated_data):
        instance.role = validated_data.get("role", instance.role)
        instance.is_active = validated_data.get("is_active", instance.is_active)
        instance.save()
        return instance


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=[User.Role.STUDENT, User.Role.RECRUITER])

    class Meta:
        model = User
        fields = ["username", "email", "password", "first_name", "last_name", "role"]

    def validate(self, attrs):
        if User.objects.filter(username__iexact=attrs["username"]).exists():
            raise serializers.ValidationError({"username": "Username already taken."})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        for field in ["first_name", "last_name", "email"]:
            validated_data.setdefault(field, "")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        if user.role == User.Role.STUDENT:
            StudentProfile.objects.create(user=user, full_name=f"{user.first_name} {user.last_name}".strip())
        elif user.role == User.Role.RECRUITER:
            RecruiterProfile.objects.create(user=user, company_name=user.username)
        return user


class StudentProfileDetailSerializer(serializers.Serializer):
    user = UserSerializer(read_only=True)
    profile = StudentProfileSerializer(required=False)

    def to_representation(self, instance):
        profile = getattr(instance, "student_profile", None)
        return {
            "user": UserSerializer(instance).data,
            "profile": StudentProfileSerializer(profile).data if profile else None,
        }

    def update(self, instance, validated_data):
        profile_data = validated_data.get("profile", {})
        profile, _ = StudentProfile.objects.get_or_create(user=instance)
        for key, value in profile_data.items():
            setattr(profile, key, value)
        profile.save()
        return instance


class RecruiterProfileDetailSerializer(serializers.Serializer):
    user = UserSerializer(read_only=True)
    profile = RecruiterProfileSerializer(required=False)

    def to_representation(self, instance):
        profile = getattr(instance, "recruiter_profile", None)
        return {
            "user": UserSerializer(instance).data,
            "profile": RecruiterProfileSerializer(profile).data if profile else None,
        }

    def update(self, instance, validated_data):
        profile_data = validated_data.get("profile", {})
        profile, _ = RecruiterProfile.objects.get_or_create(user=instance)
        for key, value in profile_data.items():
            setattr(profile, key, value)
        profile.save()
        return instance