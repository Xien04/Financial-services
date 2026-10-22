"""Disposable test configuration; never imports local .env or application credentials."""

import os
import secrets
from unittest.mock import patch

# Temporarily supply base settings without inheriting the development database.
# The environment is restored immediately so subprocess configuration tests stay isolated.
with patch.dict(
    os.environ,
    {
        "DJANGO_SECRET_KEY": secrets.token_hex(32),
        "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1,testserver",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "",
        "DATABASE_URL": os.environ.get("TEST_DATABASE_URL")
        or "postgresql://127.0.0.1:5432/financial_services_tests",
    },
):
    from .base import *  # noqa: F403

from .base import DATABASES

# Django creates/destroys this separate database, not the source database in the URL.
DATABASES["default"]["TEST"] = {"NAME": "test_financial_services"}
