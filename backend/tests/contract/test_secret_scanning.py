"""Exercise the actual scanner on disposable repositories, never application data."""

import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

SCANNER = Path(__file__).resolve().parents[3] / "infra" / "scan_secrets.py"


class SecretScanningTests(SimpleTestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "infra").mkdir()
        shutil.copyfile(SCANNER, self.root / "infra" / "scan_secrets.py")
        self.git("init", "--quiet")

    def git(self, *arguments):
        subprocess.run(
            ["git", *arguments], cwd=self.root, check=True, capture_output=True, text=True
        )

    def scan(self):
        return subprocess.run(
            [sys.executable, str(self.root / "infra" / "scan_secrets.py")],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def synthetic_private_key_marker(self):
        # A public, deliberately incomplete marker, not usable key material.
        return "-----BEGIN " + "RSA PRIVATE KEY-----"

    def test_clean_repository_passes(self):
        (self.root / "safe.txt").write_text("No credentials in this fixture.\n", encoding="utf-8")
        result = self.scan()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0 potential secrets", result.stdout)

    def test_untracked_secrets_fail_without_printing_the_value(self):
        marker = self.synthetic_private_key_marker()
        (self.root / "new.txt").write_text(marker, encoding="utf-8")
        result = self.scan()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("new.txt:1: Private Key (value redacted)", result.stdout)
        self.assertNotIn(marker, result.stdout + result.stderr)

    def test_unstaged_changes_to_tracked_files_are_scanned(self):
        target = self.root / "tracked.txt"
        target.write_text("Safe original content.\n", encoding="utf-8")
        self.git("add", "tracked.txt")
        target.write_text(self.synthetic_private_key_marker(), encoding="utf-8")
        result = self.scan()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("tracked.txt:1: Private Key", result.stdout)

    def test_ignored_local_configuration_is_not_read(self):
        (self.root / ".gitignore").write_text("local.env\n", encoding="utf-8")
        (self.root / "local.env").write_text(self.synthetic_private_key_marker(), encoding="utf-8")
        result = self.scan()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("0 potential secrets", result.stdout)
