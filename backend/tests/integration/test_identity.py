"""Acceptance scenarios from ADR 0006. Run against disposable PostgreSQL only."""

import json
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sessions.models import Session
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.db import IntegrityError, close_old_connections, transaction
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from jsonschema import Draft4Validator, FormatChecker
from rest_framework.exceptions import Throttled

from financial_services.identity import services
from financial_services.identity.models import (
    Membership,
    MembershipAuditEvent,
    RateLimitBucket,
    User,
    Workspace,
)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AuthenticationIntegrationTests(TestCase):
    def setUp(self):
        self.password = secrets.token_urlsafe(32)
        self.user = User.objects.create_user(
            "owner@example.test", self.password, display_name="Owner"
        )
        self.workspace = Workspace.objects.create(name="Personal")
        Membership.objects.create(user=self.user, workspace=self.workspace, role="owner")
        self.browser = Client(enforce_csrf_checks=True)

    def post(self, browser, path, values):
        token = browser.get("/api/v1/auth/csrf").json()["csrf_token"]
        return browser.post(
            f"/api/v1/auth/{path}", values, content_type="application/json", HTTP_X_CSRFTOKEN=token
        )

    def login(self, browser=None):
        return self.post(
            browser or self.browser,
            "login",
            {"email": " OWNER@EXAMPLE.TEST ", "password": self.password},
        )

    def reset_values(self):
        # Login updates last_login through a separate user instance.
        self.user.refresh_from_db()
        return {
            "uid": urlsafe_base64_encode(force_bytes(self.user.pk)),
            "token": default_token_generator.make_token(self.user),
            "new_password": secrets.token_urlsafe(32),
        }

    def test_authenticated_and_recovery_responses_match_the_generated_contract(self):
        schema = json.loads(
            (Path(__file__).resolve().parents[3] / "docs/api/openapi.json").read_text(
                encoding="utf-8"
            )
        )

        def check(route, method, response):
            documented = schema["paths"][f"/api/v1/auth/{route}"][method]["responses"][
                str(response.status_code)
            ]
            self.assertTrue(response["X-Request-ID"])
            if response.status_code == 204:
                self.assertEqual(response.content, b"")
                self.assertNotIn("content", documented)
            else:
                definition = documented["content"]["application/json"]["schema"]
                Draft4Validator(
                    {**definition, "components": schema["components"]},
                    format_checker=FormatChecker(),
                ).validate(response.json())

        check("login", "post", self.login())
        check("me", "get", self.browser.get("/api/v1/auth/me"))
        check("activity", "post", self.post(self.browser, "activity", {}))
        check(
            "password/recover",
            "post",
            self.post(self.browser, "password/recover", {"email": "unknown@example.test"}),
        )
        check(
            "password/change",
            "post",
            self.post(
                self.browser,
                "password/change",
                {
                    "current_password": secrets.token_urlsafe(32),
                    "new_password": secrets.token_urlsafe(32),
                },
            ),
        )
        check(
            "password/reset",
            "post",
            self.post(
                self.browser,
                "password/reset",
                {
                    "uid": "invalid",
                    "token": "invalid",
                    "new_password": secrets.token_urlsafe(32),
                },
            ),
        )
        check("logout", "post", self.post(self.browser, "logout", {}))

    def test_login_rotates_session_and_csrf_then_logout_revokes_server_session(self):
        previous = self.browser.session
        previous["anonymous"] = True
        previous.save()
        assert previous.session_key is not None
        self.browser.cookies[settings.SESSION_COOKIE_NAME] = previous.session_key
        old_csrf = self.browser.get("/api/v1/auth/csrf").cookies["csrftoken"].value
        response = self.login()
        self.assertEqual(response.status_code, 200)
        key = self.browser.cookies[settings.SESSION_COOKIE_NAME].value
        self.assertNotEqual(key, previous.session_key)
        self.assertFalse(Session.objects.filter(session_key=previous.session_key).exists())
        self.assertNotEqual(response.cookies["csrftoken"].value, old_csrf)
        self.assertTrue(response.cookies[settings.SESSION_COOKIE_NAME]["secure"])
        self.assertTrue(response.cookies[settings.SESSION_COOKIE_NAME]["httponly"])
        self.assertEqual(
            self.browser.get("/api/v1/auth/me").json()["user"]["workspaces"][0]["name"], "Personal"
        )
        self.assertEqual(self.post(self.browser, "logout", {}).status_code, 204)
        self.assertFalse(Session.objects.filter(session_key=key).exists())
        self.assertEqual(self.browser.get("/api/v1/auth/me").status_code, 403)

    def test_inactive_accounts_cannot_login_or_reuse_existing_session(self):
        self.assertEqual(self.login().status_code, 200)
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.assertEqual(self.browser.get("/api/v1/auth/me").status_code, 403)
        self.assertEqual(self.login().status_code, 400)

    def test_reauthentication_as_the_same_user_rotates_the_session(self):
        self.assertEqual(self.login().status_code, 200)
        old_key = self.browser.cookies[settings.SESSION_COOKIE_NAME].value
        self.assertEqual(self.login().status_code, 200)
        self.assertNotEqual(self.browser.cookies[settings.SESSION_COOKIE_NAME].value, old_key)
        self.assertFalse(Session.objects.filter(session_key=old_key).exists())

    def test_membership_removal_and_role_change_take_effect_on_next_request(self):
        self.login()
        membership = Membership.objects.get(user=self.user)
        membership.role = "viewer"
        membership.save()
        self.assertEqual(
            self.browser.get("/api/v1/auth/me").json()["user"]["workspaces"][0]["role"], "viewer"
        )
        membership.delete()
        self.assertEqual(self.browser.get("/api/v1/auth/me").json()["user"]["workspaces"], [])

    def test_idle_and_absolute_timeouts_and_passive_polling(self):
        for absolute in (False, True):
            self.login()
            session = self.browser.session
            original = session["auth_active"]
            self.browser.get("/api/v1/auth/me")
            self.assertEqual(self.browser.session["auth_active"], original)
            session["auth_started" if absolute else "auth_active"] = time.time() - (
                43200 if absolute else 1800
            )
            session.save()
            self.assertEqual(self.browser.get("/api/v1/auth/me").status_code, 403)

    def test_password_change_revokes_every_session_and_requires_fresh_login(self):
        second = Client(enforce_csrf_checks=True)
        self.login()
        self.login(second)
        response = self.post(
            self.browser,
            "password/change",
            {"current_password": self.password, "new_password": secrets.token_urlsafe(32)},
        )
        self.assertEqual(response.status_code, 200)
        for browser in (self.browser, second):
            self.assertEqual(browser.get("/api/v1/auth/me").status_code, 403)

    def test_reset_is_single_use_revokes_sessions_and_does_not_login(self):
        self.assertEqual(self.login().status_code, 200)
        values = self.reset_values()
        other = Client(enforce_csrf_checks=True)
        self.assertEqual(self.post(other, "password/reset", values).status_code, 200)
        self.assertEqual(self.post(other, "password/reset", values).status_code, 400)
        self.assertEqual(other.get("/api/v1/auth/me").status_code, 403)
        self.assertEqual(self.browser.get("/api/v1/auth/me").status_code, 403)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(values["new_password"]))

    def test_expired_reset_and_weak_password_are_rejected(self):
        values = self.reset_values()
        with patch.object(
            default_token_generator, "_now", return_value=datetime.now() + timedelta(seconds=3601)
        ):
            self.assertEqual(self.post(self.browser, "password/reset", values).status_code, 400)
        values["new_password"] = secrets.token_hex(2)
        self.assertEqual(self.post(self.browser, "password/reset", values).status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.password))

    def test_recovery_is_generic_and_links_use_configured_origin_and_fragment(self):
        known = self.post(self.browser, "password/recover", {"email": self.user.email})
        unknown = self.post(self.browser, "password/recover", {"email": "missing@example.test"})
        self.assertEqual(known.status_code, 200)
        self.assertEqual(known.json(), unknown.json())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("https://finance.example.test/reset-password#uid=", mail.outbox[0].body)
        self.assertNotIn("?token=", mail.outbox[0].body)
        with patch(
            "financial_services.identity.services.send_mail",
            side_effect=RuntimeError("private token"),
        ):
            with self.assertLogs("financial_services.identity.views", "ERROR") as logs:
                failure = self.post(self.browser, "password/recover", {"email": self.user.email})
        self.assertEqual(known.json(), failure.json())
        self.assertNotIn("private token", " ".join(logs.output))

    def test_rate_limits_cover_account_and_ip_and_do_not_store_raw_identifiers(self):
        limits = {"login": {"account": (1, 900), "ip": (2, 900)}}
        with override_settings(AUTH_RATE_LIMITS=limits):
            services.consume_rate_limit("login", "owner@example.test", "192.0.2.1")
            with self.assertRaises(Throttled):
                services.consume_rate_limit("login", "owner@example.test", "192.0.2.2")
            services.consume_rate_limit("login", "another@example.test", "192.0.2.1")
            with self.assertRaises(Throttled):
                services.consume_rate_limit("login", "third@example.test", "192.0.2.1")
        for key in RateLimitBucket.objects.values_list("key", flat=True):
            self.assertNotIn("@", key)
            self.assertNotIn("192.0.2", key)
        RateLimitBucket.objects.update(started_at=timezone.now() - timedelta(days=2))
        call_command("clear_auth_limits", verbosity=0)
        self.assertFalse(RateLimitBucket.objects.exists())

    def test_login_endpoint_returns_retry_after(self):
        limits = {"login": {"account": (1, 900), "ip": (30, 900)}}
        with override_settings(AUTH_RATE_LIMITS=limits):
            self.login()
            response = self.login()
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response["Retry-After"]), 0)

    def test_database_rejects_case_insensitive_email_collision(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create(email="OWNER@EXAMPLE.TEST", display_name="Duplicate")

    def test_no_staff_or_superuser_workspace_bypass_and_final_owner_protection(self):
        outsider = User.objects.create_superuser(
            "other@example.test", self.password, display_name="Other"
        )
        with self.assertRaises(PermissionDenied):
            services.require_workspace(outsider, self.workspace.pk)
        for role in ("editor", None):
            with self.assertRaises(ValidationError):
                services.change_membership(
                    actor=self.user, workspace_id=self.workspace.pk, user_id=self.user.pk, role=role
                )
        Membership.objects.create(workspace=self.workspace, user=outsider, role="viewer")
        self.assertEqual(services.require_workspace(outsider, self.workspace.pk), self.workspace)
        for capability in ("write", "import", "reconcile", "export", "manage", "delete"):
            with self.assertRaises(PermissionDenied):
                services.require_workspace(outsider, self.workspace.pk, capability)
        services.change_membership(
            actor=self.user, workspace_id=self.workspace.pk, user_id=outsider.pk, role="editor"
        )
        audit = MembershipAuditEvent.objects.get()
        self.assertEqual((audit.previous_role, audit.new_role), ("viewer", "editor"))
        self.assertEqual(audit.subject_user_id, outsider.pk)
        self.assertEqual(audit.actor_id, self.user.pk)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class IdentityConcurrencyTests(TransactionTestCase):
    def run_concurrently(self, action):
        barrier = Barrier(2)

        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    action()
                    return "ok"
                except ValidationError, Throttled:
                    return "rejected"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: worker(), range(2)))
        self.assertCountEqual(results, ["ok", "rejected"])

    def test_simultaneous_reset_link_reuse_has_one_winner(self):
        user = User.objects.create_user(
            "owner@example.test", secrets.token_urlsafe(32), display_name="Owner"
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        self.run_concurrently(
            lambda: services.reset_password(uid, token, secrets.token_urlsafe(32))
        )

    def test_simultaneous_attempts_cannot_bypass_shared_rate_limit(self):
        with override_settings(AUTH_RATE_LIMITS={"login": {"account": (1, 900), "ip": (30, 900)}}):
            self.run_concurrently(
                lambda: services.consume_rate_limit("login", "owner@example.test", "192.0.2.1")
            )

    def test_provisioning_creates_exactly_one_owner_workspace_atomically(self):
        def provision():
            services.provision_owner(
                email="owner@example.test",
                password=secrets.token_urlsafe(32),
                display_name="Owner",
                timezone_name="Asia/Manila",
                workspace_name="Personal",
            )

        self.run_concurrently(provision)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Workspace.objects.count(), 1)
        self.assertEqual(Membership.objects.get().role, "owner")

    def test_invalid_provisioning_does_not_leave_partial_identity_records(self):
        with self.assertRaises(ValidationError):
            services.provision_owner(
                email="owner@example.test",
                password=secrets.token_urlsafe(32),
                display_name="Owner",
                timezone_name="Invalid/Zone",
                workspace_name="Personal",
            )
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Workspace.objects.count(), 0)
