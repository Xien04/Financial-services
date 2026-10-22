"""Shared settings. Financial and identity schemas arrive in later work."""

import os
from urllib.parse import unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} must be configured.")
    return value


def csv_setting(name: str) -> list[str]:
    return [value.strip() for value in os.environ.get(name, "").split(",") if value.strip()]


SECRET_KEY = required("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = csv_setting("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = csv_setting("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
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
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
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

DATABASES = {
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
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {"django.server": {"handlers": [], "propagate": False}},
}
