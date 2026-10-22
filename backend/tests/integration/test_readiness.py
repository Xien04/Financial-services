from django.test import TestCase
from django.urls import reverse


class DatabaseReadinessTests(TestCase):
    def test_readiness_uses_postgresql(self):
        from django.db import connection

        self.assertEqual(connection.vendor, "postgresql")
        response = self.client.get(reverse("health-ready"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ready"})
