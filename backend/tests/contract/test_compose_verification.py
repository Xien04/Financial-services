"""Safety checks for a harness that creates and removes real Docker resources."""

import importlib.util
import json
import os
import secrets
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase

SCRIPT = Path(__file__).resolve().parents[3] / "infra" / "verify_compose.py"
spec = importlib.util.spec_from_file_location("compose_verification", SCRIPT)
assert spec is not None and spec.loader is not None
verification = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verification)


class ComposeVerificationSafetyTests(SimpleTestCase):
    def test_embedded_database_probes_are_executable_python(self):
        compile(verification.DATABASE_PROBE, "database_probe", "exec")
        for seed in (True, False):
            compile(f"SEED = {seed}\n" + verification.IDENTITY_SNAPSHOT, "identity_probe", "exec")

    def make_verifier(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        return verification.ComposeVerification(Path(temporary.name))

    def test_operator_credentials_and_compose_overrides_are_not_inherited(self):
        operator_secret = secrets.token_hex(32)
        result = verification.isolated_environment(
            {
                "PATH": "tools",
                "DATABASE_URL": "operator-value",
                "POSTGRES_PASSWORD": operator_secret,
                "COMPOSE_FILE": "other-stack.yml",
                "COMPOSE_PROJECT_NAME": "existing",
            },
            "DATABASE_URL=\nPOSTGRES_PASSWORD=\n",
        )
        self.assertEqual(result["PATH"], "tools")
        for name in ("DATABASE_URL", "POSTGRES_PASSWORD", "COMPOSE_FILE", "COMPOSE_PROJECT_NAME"):
            self.assertNotIn(name, result)

    def test_shared_resources_and_unsafe_port_bindings_are_rejected(self):
        baseline = {
            "name": "isolated",
            "services": {name: {} for name in ("db", "api", "web")},
            "volumes": {"data": {"name": "isolated_data"}},
            "networks": {"default": {"name": "isolated_default"}},
        }
        verification.validate_project(baseline, "isolated")
        for replacement in ({"name": "operator_data"}, {"name": "isolated_data", "external": True}):
            with self.subTest(replacement=replacement):
                config = baseline | {"volumes": {"data": replacement}}
                with self.assertRaises(verification.VerificationError):
                    verification.validate_project(config, "isolated")
        with self.assertRaises(verification.VerificationError):
            verification.validate_project(baseline | {"name": "another-project"}, "isolated")
        checker = self.make_verifier()
        valid_api = {"8000/tcp": [{"HostIp": "127.0.0.1", "HostPort": "8000"}]}
        for bindings in (
            {},
            {"8000/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8000"}]},
            valid_api | {"9000/tcp": [{"HostIp": "0.0.0.0", "HostPort": "9000"}]},
        ):
            with (
                self.subTest(bindings=bindings),
                patch.object(checker, "compose", return_value="a" * 64),
                patch.object(checker, "command", return_value=json.dumps(bindings)),
                self.assertRaises(verification.VerificationError),
            ):
                checker.runtime_boundaries()

    def test_existing_project_resources_are_preserved(self):
        checker = self.make_verifier()

        def result(label, args, timeout=120):
            return "existing-container" if label == "Check project containers are absent" else ""

        with (
            patch.object(verification.shutil, "which", return_value="docker"),
            patch.object(checker, "command", side_effect=result),
            self.assertRaises(verification.VerificationError),
        ):
            checker.preflight()
        self.assertFalse(checker.cleanup_allowed)
        with patch.object(checker, "compose") as compose:
            checker.cleanup()
        compose.assert_not_called()

    def test_generated_environment_is_disposable_and_does_not_use_operator_values(self):
        operator_secret = secrets.token_hex(32)
        with patch.dict(
            os.environ, {"DATABASE_URL": "operator-value", "POSTGRES_PASSWORD": operator_secret}
        ):
            checker = self.make_verifier()
        contents = (checker.scratch / ".env").read_text()
        self.assertNotIn("operator-value", contents)
        self.assertNotIn(operator_secret, contents)
        self.assertNotIn("DATABASE_URL", checker.environment)
        self.assertTrue(checker.project.startswith("fs-m1-"))
        self.assertNotIn(".env", json.dumps(checker.report))

    def test_failure_output_redacts_generated_secrets(self):
        checker = self.make_verifier()
        secret = checker.secret_values[0]
        failed = subprocess.CompletedProcess(["docker"], 1, stdout="", stderr=f"failed {secret}")
        with patch.object(verification.subprocess, "run", return_value=failed):
            with self.assertRaises(verification.VerificationError) as failure:
                checker.command("synthetic failure", ["docker"])
        self.assertNotIn(secret, str(failure.exception))
        self.assertIn("[redacted]", str(failure.exception))

    def test_cleanup_targets_only_the_new_project_and_does_not_remove_images(self):
        checker = self.make_verifier()
        checker.cleanup_allowed = True
        with patch.object(checker, "command", return_value="") as command:
            checker.cleanup()
        arguments = command.call_args.args[1]
        self.assertEqual(arguments[:4], ["docker", "compose", "--project-name", checker.project])
        self.assertEqual(arguments[-3:], ["down", "--volumes", "--remove-orphans"])
        self.assertNotIn("--rmi", arguments)
