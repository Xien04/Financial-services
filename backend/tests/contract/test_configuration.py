import os
import secrets
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


class ConfigurationTests(SimpleTestCase):
    def load_settings(self, module, assertion="", **overrides):
        environment = os.environ.copy()
        environment.update(
            DJANGO_SECRET_KEY=secrets.token_hex(32),
            DATABASE_URL="postgresql://127.0.0.1/financial_services",
            DJANGO_ALLOWED_HOSTS="localhost",
            DJANGO_CSRF_TRUSTED_ORIGINS="https://localhost",
        )
        environment.update(overrides)
        return subprocess.run(
            [sys.executable, "-c", f"import {module} as settings\n{assertion}"],
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

    def test_invalid_database_urls_are_rejected(self):
        for url in (
            "postgresql:///missing-host",
            "postgresql://localhost/",
            "postgresql://localhost:invalid/test",
            "postgresql://localhost:70000/test",
        ):
            with self.subTest(url=url):
                result = self.load_settings("config.settings.local", DATABASE_URL=url)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("valid PostgreSQL URL", result.stderr)

    def test_database_query_options_cannot_be_silently_ignored(self):
        for suffix in ("?sslmode=disable", "#fragment"):
            with self.subTest(suffix=suffix):
                result = self.load_settings(
                    "config.settings.local",
                    DATABASE_URL=f"postgresql://localhost/test{suffix}",
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("query options and fragments are not supported", result.stderr)

    def test_production_requires_explicit_hosts(self):
        result = self.load_settings("config.settings.production", DJANGO_ALLOWED_HOSTS="")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("explicit DJANGO_ALLOWED_HOSTS", result.stderr)

    def test_valid_production_configuration_keeps_security_defaults(self):
        result = self.load_settings(
            "config.settings.production",
            "assert not settings.DEBUG\n"
            "assert settings.SECURE_SSL_REDIRECT\n"
            "assert settings.SESSION_COOKIE_SECURE\n"
            "assert settings.CSRF_COOKIE_SECURE\n"
            "assert settings.DATABASES['default']['OPTIONS']['sslmode'] == 'verify-full'",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_test_settings_use_only_the_test_database_configuration(self):
        result = self.load_settings(
            "config.settings.test",
            "import os\n"
            "assert settings.DATABASES['default']['NAME'] == 'isolated_tests'\n"
            "assert settings.DATABASES['default']['TEST']['NAME'] == 'test_financial_services'\n"
            "assert settings.ALLOWED_HOSTS == ['localhost', '127.0.0.1', 'testserver']\n"
            "assert os.environ['DATABASE_URL'] == 'not-an-application-database'",
            DATABASE_URL="not-an-application-database",
            DJANGO_SECRET_KEY="",
            DJANGO_ALLOWED_HOSTS="*",
            TEST_DATABASE_URL="postgresql://127.0.0.1/isolated_tests",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

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
