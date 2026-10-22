import getpass
import sys
import warnings

from django.core.management.base import CommandError


def read_password() -> str:
    if not sys.stdin.isatty():
        raise CommandError(
            "Run interactively in a terminal; passwords cannot be piped or passed as arguments."
        )
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            password = getpass.getpass("New password: ")
            if password != getpass.getpass("Confirm password: "):
                raise CommandError("Passwords do not match.")
        except getpass.GetPassWarning:
            raise CommandError("A terminal with hidden password input is required.") from None
    return password
