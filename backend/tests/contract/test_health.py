from unittest.mock import patch

from django.db import OperationalError
from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView


class HealthContractTests(SimpleTestCase):
    def test_liveness_does_not_need_a_database(self):
        response = self.client.get(reverse("health-live"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    @patch("config.health.connection")
    def test_readiness_hides_database_failure_details(self, database):
        database.cursor.side_effect = OperationalError("private database detail")
        response = self.client.get(reverse("health-ready"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})

    def test_undeclared_api_permissions_deny_anonymous_access(self):
        class ProtectedView(APIView):
            def get(self, request):
                raise AssertionError("Anonymous requests must never reach the handler.")

        response = ProtectedView.as_view()(APIRequestFactory().get("/private"))
        self.assertEqual(response.status_code, 403)

    def test_unknown_routes_return_not_found(self):
        self.assertEqual(self.client.get("/api/v1/accounts").status_code, 404)
