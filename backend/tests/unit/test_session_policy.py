from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from financial_services.identity.middleware import SessionPolicyMiddleware
from financial_services.identity.models import normalize_email, validate_timezone


class MemorySession(dict):
    def set_expiry(self, seconds):
        self.expiry = seconds


class SessionPolicyTests(SimpleTestCase):
    def request(self, path="/api/v1/auth/me", method="get", started=99_900, active=99_900):
        request = getattr(RequestFactory(), method)(path)
        request.user = SimpleNamespace(is_authenticated=True)
        request.session = MemorySession(auth_started=started, auth_active=active)
        return request

    @patch("financial_services.identity.middleware.time.time", return_value=100_000)
    @patch("financial_services.identity.middleware.logout")
    def test_expiry_boundaries_are_enforced_before_the_handler(self, logout, clock):
        def clear(request):
            request.user = AnonymousUser()

        logout.side_effect = clear
        for started, active in ((99_900, 98_200), (56_800, 99_900), (0, 0)):
            with self.subTest(started=started, active=active):
                request = self.request(started=started, active=active)
                response = SessionPolicyMiddleware(
                    lambda r: HttpResponse(str(r.user.is_authenticated))
                )(request)
                self.assertEqual(response.content, b"False")
                self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(logout.call_count, 3)

    @patch("financial_services.identity.middleware.time.time", return_value=100_000)
    def test_passive_polling_does_not_renew_idle_expiry(self, clock):
        request = self.request()
        SessionPolicyMiddleware(lambda r: HttpResponse())(request)
        self.assertEqual(request.session["auth_active"], 99_900)

    @patch("financial_services.identity.middleware.time.time", return_value=100_000)
    def test_successful_activity_renews_idle_but_never_absolute_lifetime(self, clock):
        request = self.request(method="post", started=56_900)
        SessionPolicyMiddleware(lambda r: HttpResponse())(request)
        self.assertEqual(request.session["auth_active"], 100_000)
        self.assertEqual(request.session.expiry, 100)

    @patch("financial_services.identity.middleware.time.time", return_value=100_000)
    def test_failed_mutation_does_not_renew_expiry(self, clock):
        request = self.request(method="post")
        SessionPolicyMiddleware(lambda r: HttpResponse(status=400))(request)
        self.assertEqual(request.session["auth_active"], 99_900)

    def test_health_probe_never_reads_identity_or_session(self):
        request = RequestFactory().get("/api/v1/health/live")
        self.assertEqual(
            SessionPolicyMiddleware(lambda r: HttpResponse())(request).status_code, 200
        )

    def test_email_preserves_provider_specific_dots_and_plus_suffixes(self):
        self.assertEqual(normalize_email(" A.B+tag@Example.TEST "), "a.b+tag@example.test")
        validate_timezone("Asia/Manila")
