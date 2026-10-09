import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


def env(key, default=""):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    return os.environ.get(key, str(default)).lower() in ("1", "true", "yes", "on")


def env_list(key, default=""):
    return [item.strip() for item in env(key, default).split(",") if item.strip()]


# A placeholder secret is only ever acceptable while developing locally. In
# production it would sign sessions and JWTs for every user with a value that is
# published in this repository, so refuse to start rather than quietly serving an
# app protected by a known key.
INSECURE_DEV_SECRET = "django-insecure-dev-only"
SECRET_KEY = env("DJANGO_SECRET_KEY", INSECURE_DEV_SECRET)
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

if not DEBUG and SECRET_KEY == INSECURE_DEV_SECRET:
    raise RuntimeError(
        "DJANGO_SECRET_KEY is still the development placeholder while "
        "DJANGO_DEBUG is off. Generate a real key, for example:\n"
        "  python -c \"from django.core.management.utils import "
        "get_random_secret_key as k; print(k())\"\n"
        "and put it in backend/.env before deploying."
    )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "apps.accounts",
    "apps.jobs",
    "apps.resumes",
    "apps.profiles",
    "apps.assessments",
    "apps.interviews",
    "apps.dashboard",
    "apps.ai",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "careerai"),
        "USER": env("DB_USER", "careerai"),
        "PASSWORD": env("DB_PASSWORD", ""),
        "HOST": env("DB_HOST", "localhost"),
        "PORT": env("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    # The browsable API is a development convenience. Left on in production it
    # publishes a full, browsable index of every endpoint, including which
    # filters and actions each one accepts, to anyone who reaches the API root.
    "DEFAULT_RENDERER_CLASSES_DEBUG": (
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
}
if DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = REST_FRAMEWORK.pop(
        "DEFAULT_RENDERER_CLASSES_DEBUG"
    )

# ---------------------------------------------------------------------------
# Request throttling (enforced by config/throttling.py)
# ---------------------------------------------------------------------------
# App-level rate limits for credential and AI endpoints. Best-effort and
# per-process: put a shared cache (Redis) and edge rate limiting in front for
# real protection. Blank a value to disable that throttle. Override via env.
THROTTLE_AUTH_RATE = env("THROTTLE_AUTH_RATE", "30/min")
THROTTLE_AI_RATE = env("THROTTLE_AI_RATE", "120/hour")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

if DEBUG:
    # The dev server runs the SPA on a different port, so any origin is allowed
    # while developing. With DEBUG off this is never reached and the explicit
    # allow-list below is used instead.
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = env_list("DJANGO_CORS_ALLOWED_ORIGINS")

CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Upload limits
# ---------------------------------------------------------------------------
# The resume endpoint enforces its own 10 MB cap and PDF check, but Django's
# defaults are far larger and would let a request body buffer gigabytes in
# memory before that code ever runs. This is the outer bound.
MAX_RESUME_UPLOAD_BYTES = 10 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_RESUME_UPLOAD_BYTES
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# ---------------------------------------------------------------------------
# Security hardening (only meaningful once DEBUG is off)
# ---------------------------------------------------------------------------
# Always on: cheap, and they cost nothing in development.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

# On by default when DEBUG is off so a deployment is not silently left without
# them. Turn DJANGO_SECURE_SSL off only when TLS terminates in front of Django
# and forwarding headers are configured as below.
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(env("DJANGO_SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Behind a TLS-terminating proxy (nginx, a load balancer) Django must trust
    # the proxy's X-Forwarded-* headers to see the real scheme and build correct
    # absolute URIs.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# External AI service configuration (consumed by apps.ai.providers)
# Provider is inferred from AI_PROVIDER; a provider function per name lives
# in apps/ai/providers.py so the rest of the system never talks to a vendor
# SDK directly. Keep keys in .env, never in code.
# ---------------------------------------------------------------------------
AI_PROVIDER = env("AI_PROVIDER", "")            # e.g. "openai", "gemini", "groq"
AI_API_KEY = env("AI_API_KEY", "")
AI_BASE_URL = env("AI_BASE_URL", "")            # OpenAI-compatible chat completion endpoint
AI_MODEL = env("AI_MODEL", "gpt-4o-mini")

# Alert loudly in development if AI is enabled but unconfigured so failures
# are obvious instead of silent.
AI_REQUIRED = env_bool("AI_REQUIRED", False)