"""Token utilities shared by the accounts views and serializers."""


def blacklist_outstanding_tokens(user):
    """Invalidate every refresh token issued to ``user``.

    Called after a password change (self-service or admin reset) so sessions
    that were authenticated with the old password cannot keep refreshing. Access
    tokens are short-lived and simply expire. Best-effort: the token blacklist
    app may not be installed in every deployment.
    """
    try:
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        for token in OutstandingToken.objects.filter(user=user).exclude(
            blacklistedtoken__isnull=False
        ):
            # ``BlacklistedToken.token`` is a OneToOneField, so the reverse
            # accessor is ``token.blacklistedtoken`` (no ``_set`` suffix). The
            # manager form is used here because it works regardless of the
            # related name.
            BlacklistedToken.objects.get_or_create(token=token)
    except Exception:  # pragma: no cover - blacklist app not installed
        pass
