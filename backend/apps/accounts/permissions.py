from rest_framework.permissions import BasePermission


def super_email_grants_admin(user):
    """True when the signed-in account's email is on the super email list.

    Defined here rather than on the model so permissions can use it without
    importing the models module at import time.
    """
    if not user or not user.is_authenticated:
        return False
    email = (getattr(user, "email", "") or "").strip().lower()
    if not email:
        return False
    try:
        from .models import SuperAdminEmail
    except Exception:  # pragma: no cover - during initial migrations
        return False
    return SuperAdminEmail.objects.filter(email=email, is_active=True).exists()


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_student)


class IsRecruiter(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_recruiter)


class IsAdminRole(BasePermission):
    """Admin access, either by role or through the super email list.

    Checking the list here means a granted address has real admin powers for
    every endpoint that uses this permission, not just the accounts screen.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_admin_role:
            return True
        return super_email_grants_admin(user)


class IsSuperAdminManager(BasePermission):
    """Only accounts allowed to edit the super email list itself.

    A plain admin role is not enough, otherwise any admin could promote an
    arbitrary address and the list would be meaningless.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if super_email_grants_admin(user):
            return True
        return bool(getattr(user, "is_superuser", False))


class IsStudentOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and request.user.is_student)