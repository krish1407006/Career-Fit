from rest_framework import serializers

from .models import RecruiterProfile, StudentProfile, User


class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = [
            "full_name", "college", "branch", "graduation_year",
            "cgpa", "phone", "location", "preferred_roles",
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