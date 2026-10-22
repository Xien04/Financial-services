"""Shared settings; identity uses the policies recorded in ADR 0006."""

import os
from typing import Any
from urllib.parse import unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} must be configured.")
    return value


def csv_setting(name: str) -> list[str]:
    return [value.strip() for value in os.environ.get(name, "").split(",") if value.strip()]


def positive_int(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, "").strip() or default)
        if value < 1:
            raise ValueError
        return value
    except ValueError:
        raise ImproperlyConfigured(f"{name} must be a positive integer.") from None


SECRET_KEY = required("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = csv_setting("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = csv_setting("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "rest_framework",
    "financial_services.identity",
    "financial_services.ledger",
    "financial_services.imports",
    "financial_services.planning",
    "financial_services.reporting",
    "financial_services.integrations",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "financial_services.identity.middleware.SessionPolicyMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

try:
    database_url = urlsplit(required("DATABASE_URL"))
    if database_url.scheme not in {"postgres", "postgresql"}:
        raise ValueError
    if not database_url.hostname or not database_url.path.lstrip("/"):
        raise ValueError
    database_port = database_url.port or 5432
except ValueError:
    raise ImproperlyConfigured("DATABASE_URL must be a valid PostgreSQL URL.") from None

DATABASES: dict[str, dict[str, Any]] = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(database_url.path.lstrip("/")),
        "USER": unquote(database_url.username or ""),
        "PASSWORD": unquote(database_url.password or ""),
        "HOST": database_url.hostname,
        "PORT": database_port,
        "OPTIONS": {"connect_timeout": 3},
    }
}
# Query-string options are deliberately rejected instead of silently ignored.
if database_url.query or database_url.fragment:
    raise ImproperlyConfigured("DATABASE_URL query options and fragments are not supported yet.")

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
# Every persisted model must declare its UUID primary key explicitly.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_DOMAIN = None
SESSION_COOKIE_PATH = "/"
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = False
AUTH_USER_MODEL = "identity.User"
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {"user_attributes": ["email", "display_name"]},
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_RESET_TIMEOUT = 3600
AUTH_SESSION_IDLE_SECONDS = 1800
AUTH_SESSION_ABSOLUTE_SECONDS = 43200
AUTH_RATE_LIMITS = {
    "login": {
        "account": (positive_int("AUTH_LOGIN_ACCOUNT_LIMIT", 5), 900),
        "ip": (positive_int("AUTH_LOGIN_IP_LIMIT", 30), 900),
    },
    "recovery": {
        "account": (positive_int("AUTH_RECOVERY_ACCOUNT_LIMIT", 3), 3600),
        "ip": (positive_int("AUTH_RECOVERY_IP_LIMIT", 10), 3600),
    },
    "reset": {
        "account": (positive_int("AUTH_RESET_ACCOUNT_LIMIT", 10), 3600),
        "ip": (positive_int("AUTH_RESET_IP_LIMIT", 30), 3600),
    },
}
APP_URL = (os.environ.get("APP_URL") or "http://localhost:3000").rstrip("/")
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = positive_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = (os.environ.get("EMAIL_USE_TLS") or "true").lower() == "true"
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "")
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {"django.server": {"handlers": [], "propagate": False}},
}
