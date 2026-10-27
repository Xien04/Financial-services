import secrets
from unittest.mock import patch

from django.conf import settings
from django.test import Client, SimpleTestCase


class AnonymousAuthenticationContractTests(SimpleTestCase):
    def setUp(self):
        self.browser = Client(enforce_csrf_checks=True)

    def test_bootstrap_sets_secure_host_only_cookie_and_is_not_cached(self):
        response = self.browser.get("/api/v1/auth/csrf")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["csrf_token"])
        self.assertTrue(response.cookies["csrftoken"]["secure"])
        self.assertEqual(response.cookies["csrftoken"]["domain"], "")
        self.assertIn("no-store", response["Cache-Control"])

    def test_all_anonymous_mutations_require_csrf(self):
        for path in ("login", "logout", "password/recover", "password/reset"):
            with self.subTest(path=path):
                response = self.browser.post(
                    f"/api/v1/auth/{path}", {}, content_type="application/json"
                )
                self.assertEqual(response.status_code, 403)

    @patch("financial_services.identity.views.authenticate", return_value=None)
    @patch("financial_services.identity.services.consume_rate_limit")
    def test_login_accepts_valid_csrf_and_normalizes_email(self, limiter, authenticate):
        token = self.browser.get("/api/v1/auth/csrf").json()["csrf_token"]
        response = self.browser.post(
            "/api/v1/auth/login",
            {"email": "  OWNER@EXAMPLE.TEST ", "password": secrets.token_urlsafe(24)},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Email or password is incorrect.")
        self.assertEqual(authenticate.call_args.kwargs["email"], "owner@example.test")
        limiter.assert_called_once_with("login", "owner@example.test", "127.0.0.1")

    @patch("financial_services.identity.services.consume_rate_limit")
    def test_cross_origin_login_is_rejected_before_authentication(self, limiter):
        token = self.browser.get("/api/v1/auth/csrf").json()["csrf_token"]
        response = self.browser.post(
            "/api/v1/auth/login",
            {},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="https://attacker.example.test",
        )
        self.assertEqual(response.status_code, 403)
        limiter.assert_not_called()

    def test_no_public_registration_and_logout_is_post_only(self):
        self.assertEqual(self.browser.post("/api/v1/auth/register").status_code, 404)
        self.assertEqual(self.browser.get("/api/v1/auth/logout").status_code, 405)
        self.assertEqual(self.browser.get("/api/v1/auth/me").status_code, 403)

    def test_session_policy_configuration(self):
        self.assertEqual(settings.SESSION_ENGINE, "django.contrib.sessions.backends.db")
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertTrue(settings.SESSION_COOKIE_SECURE)
        self.assertIsNone(settings.SESSION_COOKIE_DOMAIN)
        self.assertEqual(settings.SESSION_COOKIE_SAMESITE, "Lax")
        self.assertEqual(settings.PASSWORD_RESET_TIMEOUT, 3600)
