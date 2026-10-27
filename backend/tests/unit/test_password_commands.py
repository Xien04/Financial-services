import getpass
import warnings
from unittest.mock import patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from financial_services.identity.management.passwords import read_password


class PasswordPromptTests(SimpleTestCase):
    @patch("financial_services.identity.management.passwords.sys.stdin.isatty", return_value=False)
    @patch("financial_services.identity.management.passwords.getpass.getpass")
    def test_noninteractive_password_input_is_rejected(self, prompt, tty):
        with self.assertRaises(CommandError):
            read_password()
        prompt.assert_not_called()

    @patch("financial_services.identity.management.passwords.sys.stdin.isatty", return_value=True)
    @patch("financial_services.identity.management.passwords.getpass.getpass")
    def test_echo_fallback_is_rejected(self, prompt, tty):
        def echo_warning(message):
            warnings.warn("Echo unavailable", getpass.GetPassWarning, stacklevel=1)

        prompt.side_effect = echo_warning
        with self.assertRaisesMessage(CommandError, "hidden password"):
            read_password()
