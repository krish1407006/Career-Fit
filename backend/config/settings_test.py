"""Test settings: run the suite against SQLite so it works without
Postgres superuser rights or an existing test database.

Usage:
    python manage.py test --settings=config.settings_test
"""

from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable throttling for the bulk of the suite: the in-process cache is shared
# across tests, so the default credential limit would otherwise be consumed by
# unrelated login calls. The throttle tests opt in with override_settings.
THROTTLE_AUTH_RATE = "100000/min"
THROTTLE_AI_RATE = "100000/hour"