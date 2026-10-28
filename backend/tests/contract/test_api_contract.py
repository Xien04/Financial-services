import asyncio
import importlib
import importlib.util
import io
import json
import secrets
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from django.db import OperationalError
from django.http import HttpResponse
from django.test import AsyncClient, Client, RequestFactory, SimpleTestCase, override_settings
from django.urls import clear_url_caches, path
from drf_spectacular.generators import SchemaGenerator
from drf_spectacular.validation import validate_schema
from jsonschema import Draft4Validator, FormatChecker
from rest_framework.exceptions import ErrorDetail, Throttled, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from config.api.errors import field_errors
from config.api.middleware import RequestIdMiddleware, request_id_context
from config.api.views import ContractAPIView
from config.urls import urlpatterns as application_patterns
from financial_services.identity.serializers import EmailInput

ROOT = Path(__file__).resolve().parents[3]


class FailureFixture(ContractAPIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    marker = ""

    def get(self, request, kind):
        if kind == "returned":
            return Response({"detail": self.marker}, status=400)
        if kind == "unexpected":
            raise RuntimeError(self.marker)
        if kind == "database":
            raise OperationalError(self.marker)
        if kind == "validation":
            raise ValidationError({self.marker: [ErrorDetail(self.marker, code="invalid")]})
        if kind == "rate":
            raise Throttled(wait=7, detail=self.marker)
        raise AssertionError("Unknown fixture")


urlpatterns = [*application_patterns, path("api/v1/test/<str:kind>", FailureFixture.as_view())]


class ApiContractTests(SimpleTestCase):
    def setUp(self):
        self.browser = Client(enforce_csrf_checks=True)
        self.csrf = self.browser.get("/api/v1/auth/csrf").json()["csrf_token"]

    def post(self, body, *, path="login", content_type="application/json"):
        return self.browser.post(
            f"/api/v1/auth/{path}", body, content_type=content_type, HTTP_X_CSRFTOKEN=self.csrf
        )

    def assert_envelope(self, response, status, code):
        self.assertEqual(response.status_code, status)
        self.assertEqual(response["Content-Type"], "application/json")
        data = response.json()
        self.assertEqual(set(data), {"code", "detail", "errors", "request_id"})
        self.assertEqual(data["code"], code)
        self.assertIsInstance(data["errors"], list)
        self.assertEqual(data["request_id"], response["X-Request-ID"])
        self.assertEqual(uuid.UUID(data["request_id"]).version, 4)
        return data

    def test_validation_identifies_declared_fields_and_matches_id(self):
        data = self.assert_envelope(self.post({}), 400, "validation_error")
        self.assertEqual(
            data["errors"],
            [
                {"path": "/email", "code": "required", "message": "This field is required."},
                {"path": "/password", "code": "required", "message": "This field is required."},
            ],
        )

    def test_unknown_fields_reject_without_echoing_names_or_values(self):
        marker = secrets.token_urlsafe(24)
        response = self.post({"email": "synthetic@example.test", marker: marker})
        data = self.assert_envelope(response, 400, "validation_error")
        self.assertEqual(data["errors"][0]["code"], "unknown_field")
        self.assertNotIn(marker, response.content.decode())

    def test_ambiguous_malformed_and_nonfinite_json_is_rejected(self):
        for body in (
            '{"email":1,"email":2}',
            '{"outer":{"a":1,"a":2}}',
            '{"email":NaN}',
            '{"email":Infinity}',
            "{",
            b"\xff",
            "[" * 2000,
        ):
            with self.subTest(body_type=type(body).__name__):
                self.assert_envelope(self.post(body), 400, "parse_error")
        self.assert_envelope(
            self.post("synthetic", content_type="text/plain"), 415, "unsupported_media_type"
        )

    def test_nonobject_input_is_a_safe_validation_failure(self):
        for body in ("[]", '"synthetic"', "false", "null"):
            with self.subTest(body=body):
                self.assert_envelope(self.post(body), 400, "validation_error")

    def test_empty_mutation_validates_and_keeps_success_body_empty(self):
        self.assert_envelope(self.post({"extra": True}, path="logout"), 400, "validation_error")
        response = self.post({}, path="logout")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(uuid.UUID(response["X-Request-ID"]).version, 4)

    def test_framework_security_routing_and_negotiation_errors(self):
        response = Client(enforce_csrf_checks=True).post(
            "/api/v1/auth/login", {}, content_type="application/json"
        )
        self.assert_envelope(response, 403, "csrf_failed")
        self.assertNotIn("CSRF cookie not set", response.content.decode())
        self.assert_envelope(self.browser.get("/api/v1/auth/me"), 403, "authentication_required")
        self.assert_envelope(self.browser.get("/api/v1/unknown-contract-route"), 404, "not_found")
        response = self.browser.get("/api/v1/auth/logout")
        self.assert_envelope(response, 405, "method_not_allowed")
        self.assertIn("POST", response["Allow"])
        self.assert_envelope(
            self.browser.get("/api/v1/health/live", HTTP_ACCEPT="text/html"), 406, "not_acceptable"
        )

    @patch("financial_services.identity.views.authenticate", return_value=None)
    @patch("financial_services.identity.services.consume_rate_limit")
    def test_invalid_credentials_remain_generic(self, limiter, authenticate):
        response = self.post(
            {"email": "synthetic@example.test", "password": secrets.token_urlsafe(24)}
        )
        data = self.assert_envelope(response, 400, "invalid_credentials")
        self.assertEqual(data["detail"], "Email or password is incorrect.")

    def test_caller_ids_are_replaced_and_retries_get_fresh_ids(self):
        previous: set[str] = set()
        for incoming in (str(uuid.uuid4()), "untrusted\tinput", "x" * 6000, "a,b", ""):
            response = self.browser.get("/api/v1/health/live", HTTP_X_REQUEST_ID=incoming)
            identifier = response["X-Request-ID"]
            self.assertEqual(uuid.UUID(identifier).version, 4)
            self.assertNotEqual(identifier, incoming)
            self.assertNotIn(identifier, previous)
            self.assertEqual(response.json(), {"status": "ok"})
            previous.add(identifier)
        self.assertIsNone(request_id_context.get())

    @override_settings(ROOT_URLCONF=__name__)
    def test_returned_and_raised_errors_do_not_echo_sensitive_values(self):
        marker = secrets.token_urlsafe(24)
        with patch.object(FailureFixture, "marker", marker):
            for kind, status, code in (
                ("returned", 400, "validation_error"),
                ("unexpected", 500, "internal_error"),
                ("database", 503, "service_unavailable"),
                ("validation", 400, "validation_error"),
                ("rate", 429, "rate_limited"),
            ):
                with self.subTest(kind=kind):
                    response = self.browser.get(f"/api/v1/test/{kind}")
                    self.assert_envelope(response, status, code)
                    self.assertNotIn(marker, response.content.decode())
                    if kind == "rate":
                        self.assertEqual(response["Retry-After"], "7")

    def test_field_errors_are_allowlisted_and_bounded(self):
        marker = secrets.token_urlsafe(24)
        result = field_errors({"email": [ErrorDetail(marker, code="invalid")] * 200}, EmailInput())
        self.assertEqual(len(result), 100)
        self.assertEqual(
            result[0], {"path": "/email", "code": "invalid", "message": "Enter a valid value."}
        )
        self.assertNotIn(marker, json.dumps(result))

    def test_parallel_context_and_exception_cleanup(self):
        barrier = threading.Barrier(2)

        def handler(request):
            identifier = request_id_context.get()
            barrier.wait(timeout=5)
            self.assertEqual(identifier, request_id_context.get())
            return HttpResponse(identifier)

        def invoke():
            response = RequestIdMiddleware(handler)(RequestFactory().get("/api/v1/health/live"))
            self.assertIsNone(request_id_context.get())
            return response["X-Request-ID"]

        with ThreadPoolExecutor(max_workers=2) as executor:
            self.assertEqual(len(set(executor.map(lambda _: invoke(), range(2)))), 2)

        def fail(request):
            raise RuntimeError()

        with self.assertRaises(RuntimeError):
            RequestIdMiddleware(fail)(RequestFactory().get("/api/v1/health/live"))
        self.assertIsNone(request_id_context.get())

    async def test_async_ids_are_distinct_without_context_leak(self):
        responses = await asyncio.gather(
            *[AsyncClient().get("/api/v1/health/live") for _ in range(2)]
        )
        self.assertNotEqual(responses[0]["X-Request-ID"], responses[1]["X-Request-ID"])
        self.assertIsNone(request_id_context.get())


class OpenApiContractTests(SimpleTestCase):
    schema: dict

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.schema = SchemaGenerator().get_schema(public=True)

    def assert_documented(self, path, method, response):
        documented = self.schema["paths"][path][method]["responses"][str(response.status_code)]
        self.assertIn("X-Request-ID", documented["headers"])
        if response.status_code == 204:
            self.assertNotIn("content", documented)
            self.assertEqual(response.content, b"")
        else:
            definition = documented["content"]["application/json"]["schema"]
            Draft4Validator(
                {**definition, "components": self.schema["components"]},
                format_checker=FormatChecker(),
            ).validate(response.json())

    def test_valid_generated_contract_matches_snapshot(self):
        validate_schema(self.schema)
        committed = json.loads((ROOT / "docs/api/openapi.json").read_text(encoding="utf-8"))
        self.assertEqual(self.schema, committed)
        self.assertEqual(self.schema["openapi"], "3.0.3")
        self.assertEqual(len(self.schema["paths"]), 10)
        self.assertNotIn("/api/v1/schema", self.schema["paths"])

    def test_security_strict_input_and_deferred_scope_are_documented(self):
        paths = self.schema["paths"]
        self.assertEqual(paths["/api/v1/auth/me"]["get"]["security"], [{"cookieAuth": []}])
        self.assertFalse(paths["/api/v1/auth/login"]["post"].get("security"))
        self.assertEqual(
            self.schema["components"]["securitySchemes"]["cookieAuth"],
            {"type": "apiKey", "in": "cookie", "name": "sessionid"},
        )
        for operations in paths.values():
            for method, operation in operations.items():
                parameters = operation.get("parameters", [])
                self.assertNotIn("Idempotency-Key", [item["name"] for item in parameters])
                if method == "post":
                    for name in ("X-CSRFToken", "csrftoken"):
                        self.assertTrue(
                            next(p for p in parameters if p["name"] == name)["required"]
                        )
                    ref = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
                    component = self.schema["components"]["schemas"][ref.split("/")[-1]]
                    self.assertFalse(component["additionalProperties"])

    def test_real_responses_follow_documented_shapes(self):
        browser = Client(enforce_csrf_checks=True)
        response = browser.get("/api/v1/auth/csrf")
        self.assert_documented("/api/v1/auth/csrf", "get", response)
        csrf = response.json()["csrf_token"]
        for route_path, method in (
            ("/api/v1/health/live", "get"),
            ("/api/v1/auth/me", "get"),
            ("/api/v1/auth/login", "post"),
        ):
            response = getattr(browser, method)(route_path, {}, content_type="application/json")
            self.assert_documented(route_path, method, response)
        response = browser.post(
            "/api/v1/auth/login", {}, content_type="application/json", HTTP_X_CSRFTOKEN=csrf
        )
        self.assert_documented("/api/v1/auth/login", "post", response)
        response = browser.post(
            "/api/v1/auth/logout", {}, content_type="application/json", HTTP_X_CSRFTOKEN=csrf
        )
        self.assert_documented("/api/v1/auth/logout", "post", response)
        with patch("config.health.connection") as connection:
            connection.cursor.side_effect = OperationalError("synthetic")
            response = browser.get("/api/v1/health/ready")
        self.assert_documented("/api/v1/health/ready", "get", response)
        self.assertEqual(response.json(), {"status": "unavailable"})

    def test_development_schema_endpoint_is_opt_in(self):
        import config.urls

        self.assertEqual(self.client.get("/api/v1/schema").status_code, 404)
        try:
            with override_settings(API_SCHEMA_ENABLED=True):
                importlib.reload(config.urls)
                clear_url_caches()
                response = self.client.get("/api/v1/schema")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["openapi"], "3.0.3")
        finally:
            importlib.reload(config.urls)
            clear_url_caches()
        self.assertEqual(self.client.get("/api/v1/schema").status_code, 404)

    def test_drift_gate_rejects_missing_and_changed_contracts(self):
        spec = importlib.util.spec_from_file_location(
            "api_schema_check", ROOT / "infra/check_api_schema.py"
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            with patch.object(module, "SCHEMA_PATH", Path(directory) / "schema.json"):
                self.assertEqual(module.main([]), 1)
                self.assertEqual(module.main(["--update"]), 0)
                self.assertEqual(module.main([]), 0)
                module.SCHEMA_PATH.write_text("{}", encoding="utf-8")
                self.assertEqual(module.main([]), 1)
