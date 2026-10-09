"""Application-level request throttling.

These are deliberately simple, in-process rate limits for the credential and AI
endpoints. They are **not** a substitute for infrastructure protection: DRF's
cache-backed throttles are per-process when the default LocMemCache is used and
they reset on restart. For a multi-process deployment, point Django's cache at a
shared backend (e.g. Redis) and keep coarse rate limiting / DDoS protection at
the reverse proxy or edge.

Rates are read live from settings (not snapshotted at import time) so a
deployment can tune them through environment variables and a test can override
just the one setting it exercises.
"""

from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class _SettingRateThrottle(SimpleRateThrottle):
    """Base throttle whose rate comes from a named Django setting.

    Returning ``None`` disables the throttle, which is what happens when the
    setting is blank.
    """

    setting_name = ""

    def get_rate(self):
        return getattr(settings, self.setting_name, None) or None


class AuthThrottle(_SettingRateThrottle):
    """Limits login, registration and token refresh attempts per client."""

    scope = "auth"
    setting_name = "THROTTLE_AUTH_RATE"


class AiThrottle(_SettingRateThrottle):
    """Limits calls that may hit the external AI provider."""

    scope = "ai"
    setting_name = "THROTTLE_AI_RATE"
