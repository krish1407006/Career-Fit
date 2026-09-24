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