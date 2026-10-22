"""Fail-closed baseline; production hosting is separate Milestone 1 work."""

from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import (
    ALLOWED_HOSTS,
    APP_URL,
    CSRF_TRUSTED_ORIGINS,
    DATABASES,
    DEFAULT_FROM_EMAIL,
    EMAIL_HOST,
)

if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Production requires explicit DJANGO_ALLOWED_HOSTS.")
if not CSRF_TRUSTED_ORIGINS or any(
    not origin.startswith("https://") for origin in CSRF_TRUSTED_ORIGINS
):
    raise ImproperlyConfigured("Production requires explicit HTTPS CSRF origins.")

DATABASES["default"]["OPTIONS"]["sslmode"] = "verify-full"
public_url = urlsplit(APP_URL)
if (
    public_url.scheme != "https"
    or not public_url.hostname
    or public_url.username
    or public_url.password
    or public_url.path
    or public_url.query
    or public_url.fragment
):
    raise ImproperlyConfigured("Production requires APP_URL to be an HTTPS origin.")
if not EMAIL_HOST or not DEFAULT_FROM_EMAIL:
    raise ImproperlyConfigured("Production requires EMAIL_HOST and DEFAULT_FROM_EMAIL.")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
