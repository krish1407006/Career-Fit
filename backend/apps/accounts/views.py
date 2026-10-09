from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    AdminUserSerializer,
    LoginSerializer,
    MyAccountEmailSerializer,
    PasswordChangeSerializer,
    RecruiterProfileDetailSerializer,
    RegisterSerializer,
    StudentProfileDetailSerializer,
    SuperAdminEmailSerializer,
    UserAdminUpdateSerializer,
    UserSerializer,
)

from .permissions import IsAdminRole, IsSuperAdminManager, super_email_grants_admin

from .models import SuperAdminEmail, User
from .tokens import blacklist_outstanding_tokens
from config.throttling import AuthThrottle


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
                # An address on the super email list is promoted on sign-in, so a
                # granted person gets a real admin role and token, not just
                # access to one screen.
                if not user.is_admin_role and super_email_grants_admin(user):
                    user.role = User.Role.ADMIN
                    user.is_staff = True
                    user.save(update_fields=["role", "is_staff"])
                response.data["user"] = UserSerializer(user).data
            except (User.DoesNotExist, KeyError):
                pass
        return response


class LoginView(TokenObtainPairWithRoleView):
    """POST /api/auth/login/ with {username, password}.

    Returns access + refresh tokens plus a serialized copy of the user
    (including role) so the frontend can redirect by role immediately.
    """

    throttle_classes = [AuthThrottle]


class ThrottledTokenRefreshView(TokenRefreshView):
    """Token refresh, rate limited alongside the other credential endpoints."""

    throttle_classes = [AuthThrottle]


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
    throttle_classes = [AuthThrottle]

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
        if self.request.user.is_student:
            return StudentProfileDetailSerializer
        if self.request.user.is_recruiter:
            return RecruiterProfileDetailSerializer
        return UserSerializer

    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        # is_student is checked before is_admin_role because it is also true for
        # admins, who hold a student profile of their own. The payload keeps the
        # "user" key, so the client keeps its role flags either way.
        if instance.is_student:
            return Response(StudentProfileDetailSerializer(instance).data)
        if instance.is_recruiter:
            return Response(RecruiterProfileDetailSerializer(instance).data)
        return Response({"user": UserSerializer(instance).data})

    def put(self, request, *args, **kwargs):
        instance = self.get_object()
        # is_student is checked first because it is also true for admins, who now
        # hold a student profile of their own. Without this an admin editing
        # /profile would be told they have no editable profile at all.
        if instance.is_student:
            serializer = StudentProfileDetailSerializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.update(instance, serializer.validated_data)
        elif instance.is_recruiter:
            serializer = RecruiterProfileDetailSerializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.update(instance, serializer.validated_data)
        else:
            return Response({"detail": "This account has no editable profile."},
                            status=status.HTTP_400_BAD_REQUEST)
        return self.get(request, *args, **kwargs)


class AdminUserListView(generics.ListAPIView):
    """Admin-only listing of all platform users, with what they own."""

    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminRole]
    # The accounts screen is a management table, not a feed: it has no pager, it
    # filters by role in the browser, and it decides "at least one active admin
    # must remain" from the rows it holds. Left on DRF's default 20-per-page
    # pagination, every account past the twentieth was unreachable -- it could
    # not be searched, selected or deleted, and the last-admin guard counted
    # admins from a truncated list. Return the whole list, as the admin resume,
    # interview and attempt screens already do.
    pagination_class = None
    filterset_fields = ["role", "is_active"]

    def get_queryset(self):
        return User.objects.select_related("student_profile", "recruiter_profile")\
            .all().order_by("-created_at")


def ensure_manager_on_list(user):
    """Make sure the person managing the list is themselves on it.

    Without this the list can be empty, which makes the "cannot remove the last
    entry" rule block the very first revoke, and the owner's own admin access
    would rest on a flag the list knows nothing about.
    """
    email = (getattr(user, "email", "") or "").strip().lower()
    if not email:
        return None
    existing = SuperAdminEmail.objects.filter(email=email).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.save(update_fields=["is_active"])
        return existing
    return SuperAdminEmail.objects.create(
        email=email, added_by=user, note="List owner", is_active=True
    )


def revoke_super_email_access(email):
    """Demote accounts that were promoted purely because of this address.

    Without this, removing an address would leave the person who signed in while
    it was active as a full admin forever, which defeats the point of removing
    it. Superusers are never demoted.
    """
    if not email:
        return 0
    return User.objects.filter(
        email__iexact=email, role=User.Role.ADMIN, is_superuser=False
    ).update(role=User.Role.STUDENT, is_staff=False)


class SuperAdminEmailListView(APIView):
    """List and grant the super email addresses."""

    permission_classes = [IsSuperAdminManager]

    def get(self, request):
        rows = SuperAdminEmail.objects.select_related("added_by").all()
        return Response({"results": SuperAdminEmailSerializer(
            rows, many=True, context={"request": request}
        ).data})

    def post(self, request):
        serializer = SuperAdminEmailSerializer(data=request.data,
                                                context={"request": request})
        serializer.is_valid(raise_exception=True)
        entry = serializer.save(added_by=request.user)
        ensure_manager_on_list(request.user)
        return Response(SuperAdminEmailSerializer(
            entry, context={"request": request}
        ).data, status=status.HTTP_201_CREATED)


class SuperAdminEmailDetailView(APIView):
    """Activate, deactivate or delete one super email."""

    permission_classes = [IsSuperAdminManager]

    def patch(self, request, pk):
        entry = get_object_or_404(SuperAdminEmail, pk=pk)
        serializer = SuperAdminEmailSerializer(
            entry, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        was_active = entry.is_active
        entry = serializer.save()
        if was_active and not entry.is_active:
            revoke_super_email_access(entry.email)
        return Response(serializer.data)

    def delete(self, request, pk):
        entry = get_object_or_404(SuperAdminEmail, pk=pk)
        if entry.is_active and not SuperAdminEmail.objects.filter(
            is_active=True
        ).exclude(pk=entry.pk).exists():
            return Response(
                {"detail": "This is the last active super email. Add another one "
                           "before removing this."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        email = entry.email
        entry.delete()
        revoke_super_email_access(email)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyEmailView(APIView):
    """Read or change the signed-in admin's own email address."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MyAccountEmailSerializer(request.user).data)

    def patch(self, request):
        serializer = MyAccountEmailSerializer(request.user, data=request.data,
                                              partial=True)
        serializer.is_valid(raise_exception=True)

        # Decide authorisation BEFORE the address changes. Doing it afterwards
        # would let any signed-in user grant themselves admin simply by calling
        # this endpoint with their own address.
        was_manager = super_email_grants_admin(request.user) or request.user.is_superuser
        old_email = (request.user.email or "").strip().lower()

        user = serializer.save()
        new_email = (user.email or "").strip().lower()

        # The list is matched on email, so a manager who corrects their own
        # address has to take their entry with them or they immediately lose the
        # ability to manage the list.
        if was_manager and old_email and new_email and old_email != new_email:
            moved = SuperAdminEmail.objects.filter(email=old_email).first()
            clash = SuperAdminEmail.objects.filter(email=new_email).first()
            if moved and not clash:
                moved.email = new_email
                moved.save(update_fields=["email"])
            elif moved and clash:
                # New address is already a super email, so the old row is
                # redundant; retire it rather than leaving a stale grant.
                moved.delete()
        if was_manager:
            ensure_manager_on_list(user)

        return Response(
            {"email": user.email,
             "detail": "Email updated. If this address is on the super email list, "
                       "your admin access follows it."}
        )


class MyPasswordView(APIView):
    """POST /api/auth/me/password/ — change the signed-in user's password.

    Any authenticated role (student, recruiter, admin) can change their own
    password. The admin reset endpoint remains for resetting *other* accounts.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password updated. Please sign in again."})


class AdminUserResetPasswordView(APIView):
    """Admin sets a new password for an account.

    Exists because a locked-out account otherwise has no way back in without a
    shell, and the accounts screen is where an admin already is.
    """

    permission_classes = [IsAdminRole]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        new_password = request.data.get("password") or ""
        if len(new_password) < 8:
            return Response(
                {"detail": "Password must be at least 8 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(new_password)
        user.is_active = True
        user.save(update_fields=["password", "is_active"])
        # Force a fresh login so the old tokens stop working.
        blacklist_outstanding_tokens(user)
        return Response({"detail": f"Password updated for {user.username}."})


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
        if self.get_object() == request.user:
            return Response({"detail": "You cannot edit your own admin account."},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().put(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        # Must not delegate to put(): that drops partial=True, so a PATCH that
        # only toggles is_active would demand role as well.
        if self.get_object() == request.user:
            return Response({"detail": "You cannot edit your own admin account."},
                            status=status.HTTP_400_BAD_REQUEST)
        return super().partial_update(request, *args, **kwargs)

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