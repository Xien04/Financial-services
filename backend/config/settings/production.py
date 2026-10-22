"""Fail-closed baseline; production hosting is separate Milestone 1 work."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, DATABASES

if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Production requires explicit DJANGO_ALLOWED_HOSTS.")
if not CSRF_TRUSTED_ORIGINS or any(
    not origin.startswith("https://") for origin in CSRF_TRUSTED_ORIGINS
):
    raise ImproperlyConfigured("Production requires explicit HTTPS CSRF origins.")

DATABASES["default"]["OPTIONS"]["sslmode"] = "verify-full"
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
