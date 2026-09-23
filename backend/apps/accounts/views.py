from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    RecruiterProfileDetailSerializer,
    RegisterSerializer,
    StudentProfileDetailSerializer,
    UserAdminUpdateSerializer,
    UserSerializer,
)

from .permissions import IsAdminRole

from .models import User


class TokenObtainPairWithRoleView(TokenObtainPairView):
    """JWT login that also returns the user's role and id.

    Role/permissions checks then read from the token payload or /auth/me.
    """

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            try:
                user = User.objects.get(username=request.data["username"])
                response.data["user"] = UserSerializer(user).data
            except (User.DoesNotExist, KeyError):
                pass
        return response


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"user": UserSerializer(user).data,
             "detail": "Account created. Use /auth/token/ to log in."},
            status=status.HTTP_201_CREATED,
        )


class MeView(generics.RetrieveUpdateAPIView):
    """Authenticated view returning the caller's user + profile."""

    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.user.role == User.Role.STUDENT:
            return StudentProfileDetailSerializer
        if self.request.user.role == User.Role.RECRUITER:
            return RecruiterProfileDetailSerializer
        return UserSerializer

    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.role == User.Role.STUDENT:
            data = StudentProfileDetailSerializer(instance).data
        elif instance.role == User.Role.RECRUITER:
            data = RecruiterProfileDetailSerializer(instance).data
        else:
            data = {"user": UserSerializer(instance).data}
        return Response(data)

    def put(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.role == User.Role.STUDENT:
            serializer = StudentProfileDetailSerializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.update(instance, serializer.validated_data)
        elif instance.role == User.Role.RECRUITER:
            serializer = RecruiterProfileDetailSerializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.update(instance, serializer.validated_data)
        else:
            return Response({"detail": "Admin accounts have no editable profile."},
                            status=status.HTTP_400_BAD_REQUEST)
        return self.get(request, *args, **kwargs)


class AdminUserListView(generics.ListAPIView):
    """Admin-only listing of all platform users."""

    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]
    filterset_fields = ["role", "is_active"]

    def get_queryset(self):
        return User.objects.select_related("student_profile", "recruiter_profile").all()


class AdminUserUpdateView(generics.RetrieveUpdateDestroyAPIView):
    """Admin can update role/is_active or remove a user account."""

    queryset = User.objects.all()
    serializer_class = UserAdminUpdateSerializer
    permission_classes = [IsAdminRole]

    def put(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance == request.user:
            return Response({"detail": "You cannot edit your own admin account."},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().put(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.put(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance == request.user:
            return Response({"detail": "You cannot delete your own admin account."},
                            status=status.HTTP_400_BAD_REQUEST)
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)