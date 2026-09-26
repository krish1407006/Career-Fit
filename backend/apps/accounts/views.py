from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    AdminUserSerializer,
    LoginSerializer,
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

    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            try:
                user = User.objects.get(username=request.data["username"])
                response.data["user"] = UserSerializer(user).data
            except (User.DoesNotExist, KeyError):
                pass
        return response


class LoginView(TokenObtainPairWithRoleView):
    """POST /api/auth/login/ with {username, password}.

    Returns access + refresh tokens plus a serialized copy of the user
    (including role) so the frontend can redirect by role immediately.
    """


class LogoutView(APIView):
    """POST /api/auth/logout/ with {refresh}.

    Blacklists the presented refresh token. Access tokens are short-lived
    and simply expire. The endpoint requires an authenticated caller so
    anonymous clients cannot spam token blacklisting.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {"detail": "refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh)
            token.blacklist()
        except TokenError:
            return Response(
                {"detail": "Invalid or expired refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"detail": "Logged out successfully."},
            status=status.HTTP_205_RESET_CONTENT,
        )


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
        if self.request.user.is_admin_role:
            return UserSerializer
        if self.request.user.is_student:
            return StudentProfileDetailSerializer
        if self.request.user.is_recruiter:
            return RecruiterProfileDetailSerializer
        return UserSerializer

    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_admin_role:
            data = {"user": UserSerializer(instance).data}
        elif instance.is_student:
            data = StudentProfileDetailSerializer(instance).data
        elif instance.is_recruiter:
            data = RecruiterProfileDetailSerializer(instance).data
        else:
            data = {"user": UserSerializer(instance).data}
        return Response(data)

    def put(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_student:
            serializer = StudentProfileDetailSerializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.update(instance, serializer.validated_data)
        elif instance.is_recruiter:
            serializer = RecruiterProfileDetailSerializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.update(instance, serializer.validated_data)
        else:
            return Response({"detail": "Admin accounts have no editable profile."},
                            status=status.HTTP_400_BAD_REQUEST)
        return self.get(request, *args, **kwargs)


class AdminUserListView(generics.ListAPIView):
    """Admin-only listing of all platform users, with what they own."""

    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminRole]
    filterset_fields = ["role", "is_active"]

    def get_queryset(self):
        return User.objects.select_related("student_profile", "recruiter_profile")\
            .all().order_by("-created_at")


class AdminUserBulkDeleteView(APIView):
    """Delete several accounts in one request from the admin accounts screen."""

    permission_classes = [IsAdminRole]

    def post(self, request):
        ids = request.data.get("ids")
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "Select at least one account to delete."},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            ids = [int(value) for value in ids]
        except (TypeError, ValueError):
            return Response({"detail": "Account ids must be numbers."},
                            status=status.HTTP_400_BAD_REQUEST)

        targets = list(User.objects.filter(pk__in=ids))
        found = {user.pk for user in targets}
        missing = sorted(set(ids) - found)
        if missing:
            return Response({"detail": f"No account with id {missing[0]}."},
                            status=status.HTTP_404_NOT_FOUND)
        if any(user == request.user for user in targets):
            return Response({"detail": "You cannot delete your own admin account."},
                            status=status.HTTP_400_BAD_REQUEST)

        remaining_admins = User.objects.filter(role=User.Role.ADMIN, is_active=True)\
            .exclude(pk__in=[user.pk for user in targets]).count()
        if remaining_admins == 0:
            return Response(
                {"detail": "At least one active admin account must remain."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted = len(targets)
        for user in targets:
            user.delete()
        return Response({"deleted": deleted}, status=status.HTTP_200_OK)


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
        # Deleting the final admin would lock everyone out of account management.
        if (instance.role == User.Role.ADMIN
                and User.objects.filter(role=User.Role.ADMIN, is_active=True).count() <= 1):
            return Response(
                {"detail": "At least one active admin account must remain."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)