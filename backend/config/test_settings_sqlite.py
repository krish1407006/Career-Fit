"""Throwaway settings used only to run the test suite on SQLite.

The local Postgres role has no CREATEDB, so `manage.py test` cannot make its
test database. Delete this file once the suite has been run.
"""

from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
