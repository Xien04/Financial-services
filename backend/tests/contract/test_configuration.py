import os
import secrets
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


class ConfigurationTests(SimpleTestCase):
    def load_settings(self, module, **overrides):
        environment = os.environ.copy()
        environment.update(
            DJANGO_SECRET_KEY=secrets.token_hex(32),
            DATABASE_URL="postgresql://127.0.0.1/financial_services",
            DJANGO_ALLOWED_HOSTS="localhost",
            DJANGO_CSRF_TRUSTED_ORIGINS="https://localhost",
        )
        environment.update(overrides)
        return subprocess.run(
            [sys.executable, "-c", f"import {module}"],
            env=environment,
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_secret_is_required(self):
        result = self.load_settings("config.settings.local", DJANGO_SECRET_KEY="")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY must be configured", result.stderr)

    def test_sqlite_cannot_replace_postgresql(self):
        result = self.load_settings("config.settings.local", DATABASE_URL="sqlite:///db.sqlite3")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("valid PostgreSQL URL", result.stderr)

    def test_production_rejects_wildcard_hosts(self):
        result = self.load_settings("config.settings.production", DJANGO_ALLOWED_HOSTS="*")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("explicit DJANGO_ALLOWED_HOSTS", result.stderr)

    def test_production_rejects_http_csrf_origins(self):
        result = self.load_settings(
            "config.settings.production", DJANGO_CSRF_TRUSTED_ORIGINS="http://localhost"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("explicit HTTPS CSRF origins", result.stderr)
