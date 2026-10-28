"""Local HTTP development only; never use for public deployments."""

from .base import *  # noqa: F403

# Debug tracebacks can expose configuration; opt in only on a trusted machine.
DEBUG = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
API_SCHEMA_ENABLED = True
