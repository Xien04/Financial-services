import os
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.settings.base import csv_setting, required


class EnvironmentConfigurationTests(SimpleTestCase):
    def test_required_values_reject_missing_and_whitespace_only_input(self):
        for value in (None, "", " \t "):
            with self.subTest(value=value), patch.dict(os.environ, {}, clear=True):
                if value is not None:
                    os.environ["SETTING_UNDER_TEST"] = value
                with self.assertRaisesMessage(ImproperlyConfigured, "must be configured"):
                    required("SETTING_UNDER_TEST")

    def test_required_values_trim_surrounding_whitespace(self):
        with patch.dict(os.environ, {"SETTING_UNDER_TEST": " localhost \t"}):
            self.assertEqual(required("SETTING_UNDER_TEST"), "localhost")

    def test_allowed_host_lists_ignore_empty_items_and_trim_whitespace(self):
        with patch.dict(os.environ, {"SETTING_UNDER_TEST": " localhost, ,127.0.0.1, "}):
            self.assertEqual(csv_setting("SETTING_UNDER_TEST"), ["localhost", "127.0.0.1"])

    def test_absent_optional_lists_are_empty(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(csv_setting("SETTING_UNDER_TEST"), [])
