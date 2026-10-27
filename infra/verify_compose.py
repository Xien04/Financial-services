"""Exercise the real local Compose stack using an isolated, disposable project."""

import argparse
import json
import os
import platform
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
MARKER = "M1_RESULT="

# These run inside the API image, using its application database role and services.
DATABASE_PROBE = """
import json
import django
django.setup()
from django.db import connection, DatabaseError, transaction
with connection.cursor() as cursor:
    cursor.execute('SELECT current_user, rolsuper, rolcreatedb, rolcreaterole '
                   'FROM pg_roles WHERE rolname = current_user')
    role, *privileges = cursor.fetchone()
    assert role == 'm1_app' and privileges == [False, False, False]
    for table in ('identity_user', 'identity_workspace', 'identity_membership',
                  'identity_membershipauditevent', 'identity_ratelimitbucket'):
        cursor.execute('SELECT data_type FROM information_schema.columns '
                       "WHERE table_schema = 'public' AND table_name = %s AND column_name = 'id'",
                       [table])
        assert cursor.fetchone() == ('uuid',), table
with transaction.atomic(), connection.cursor() as cursor:
    cursor.execute('CREATE TABLE m1_schema_permission_probe (id uuid PRIMARY KEY)')
    cursor.execute('DROP TABLE m1_schema_permission_probe')
for statement in ('CREATE DATABASE m1_forbidden_database', 'CREATE ROLE m1_forbidden_role'):
    try:
        with connection.cursor() as cursor:
            cursor.execute(statement)
    except DatabaseError as error:
        assert getattr(error.__cause__, 'sqlstate', None) == '42501'
    else:
        raise AssertionError('Application role unexpectedly has administrative privileges')
print('M1_RESULT=' + json.dumps({'uuid_columns': 5, 'schema_write': True,
                               'createdb_denied': True, 'createrole_denied': True,
                               'superuser': False}))
"""

IDENTITY_SNAPSHOT = """
import hashlib
import json
import secrets
import django
django.setup()
from financial_services.identity import services
from financial_services.identity.models import User, Workspace, Membership, MembershipAuditEvent
if SEED:
    assert not User.objects.exists() and not Workspace.objects.exists()
    services.provision_owner(email='owner@example.test', password=secrets.token_urlsafe(32),
                             display_name='Verification Owner', timezone_name='Asia/Manila',
                             workspace_name='Verification Workspace')
assert User.objects.count() == Workspace.objects.count() == Membership.objects.count() == 1
assert Membership.objects.get().role == 'owner'
assert MembershipAuditEvent.objects.count() == 1
data = {
    'users': sorted(str(value) for value in User.objects.values_list('id', flat=True)),
    'workspaces': sorted(str(value) for value in Workspace.objects.values_list('id', flat=True)),
    'memberships': sorted((str(m.id), str(m.user_id), str(m.workspace_id), m.role)
                          for m in Membership.objects.all()),
    'audit': sorted(str(value) for value in
                    MembershipAuditEvent.objects.values_list('id', flat=True)),
}
print('M1_RESULT=' + json.dumps({'users': 1, 'workspaces': 1, 'memberships': 1, 'audit_events': 1,
      'fingerprint': hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()}))
"""


class VerificationError(Exception):
    pass


def isolated_environment(source: dict[str, str], template: str) -> dict[str, str]:
    names = set(re.findall(r"^([A-Z][A-Z0-9_]*)=", template, re.MULTILINE))
    return {
        name: value
        for name, value in source.items()
        if name not in names and not name.startswith("COMPOSE_")
    } | {"COMPOSE_ANSI": "never", "COMPOSE_PROGRESS": "plain", "BUILDKIT_PROGRESS": "plain"}


def validate_project(config: dict[str, Any], project: str) -> None:
    """Refuse shared resources before authorizing any project cleanup."""
    if config.get("name") != project or set(config.get("services", {})) != {"db", "api", "web"}:
        raise VerificationError("Unexpected Compose project or services.")
    for kind in ("volumes", "networks"):
        for resource in config.get(kind, {}).values():
            if resource.get("external") or not resource.get("name", "").startswith(project + "_"):
                raise VerificationError(
                    "Verification must use exclusively project-owned resources."
                )
    if any(service.get("container_name") for service in config["services"].values()):
        raise VerificationError("Explicit container names are not safe for isolated verification.")


class ComposeVerification:
    def __init__(self, scratch: Path):
        self.project = "fs-m1-" + secrets.token_hex(8)
        self.scratch = scratch
        template = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.environment = isolated_environment(dict(os.environ), template)
        app_password, admin_password, django_secret = (secrets.token_hex(32) for _ in range(3))
        self.secret_values = [app_password, admin_password, django_secret]
        values = {
            "POSTGRES_DB": "m1_foundation",
            "POSTGRES_USER": "m1_admin",
            "POSTGRES_PASSWORD": admin_password,
            "APP_DB_USER": "m1_app",
            "APP_DB_PASSWORD": app_password,
            "DJANGO_SECRET_KEY": django_secret,
            "DATABASE_URL": f"postgresql://m1_app:{app_password}@db:5432/m1_foundation",
        }
        env_file = scratch / ".env"
        env_file.touch(mode=0o600)
        env_file.write_text(
            re.sub(
                r"^([A-Z][A-Z0-9_]*)=.*$",
                lambda match: f"{match[1]}={values.get(match[1], '')}",
                template,
                flags=re.MULTILINE,
            ),
            encoding="utf-8",
        )
        self.base = [
            "docker",
            "compose",
            "--project-name",
            self.project,
            "--env-file",
            str(env_file),
            "-f",
            str(ROOT / "compose.yaml"),
        ]
        self.cleanup_allowed = False
        self.report: dict[str, Any] = {
            "status": "running",
            "project": self.project,
            "started_at": datetime.now(UTC).isoformat(),
            "environment": platform.platform(),
            "tester": "Compose verification automation",
            "execution": "GitHub Actions" if os.environ.get("GITHUB_ACTIONS") else "local host",
            "commands": [],
            "acceptance": {},
        }
        if os.environ.get("GITHUB_RUN_ID"):
            self.report["run_url"] = (
                f"https://github.com/{os.environ.get('GITHUB_REPOSITORY')}/actions/runs/"
                f"{os.environ['GITHUB_RUN_ID']}"
            )

    def redact(self, value: str) -> str:
        for secret in self.secret_values:
            value = value.replace(secret, "[redacted]")
        return value

    def command(self, label: str, args: list[str], timeout: int = 120) -> str:
        print(f"RUN {label}", flush=True)
        display = args[:]
        if "-c" in display:
            display[display.index("-c") + 1] = "<embedded verification code>"
        entry: dict[str, Any] = {"label": label, "command": display, "exit_code": None}
        self.report["commands"].append(entry)
        try:
            result = subprocess.run(
                args,
                cwd=ROOT,
                env=self.environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise VerificationError(f"{label}: {type(error).__name__}") from None
        entry["exit_code"] = result.returncode
        if result.returncode:
            detail = self.redact((result.stdout + result.stderr)[-6000:])
            raise VerificationError(f"{label} exited {result.returncode}:\n{detail}")
        return result.stdout.strip()

    def compose(self, label: str, *args: str, timeout: int = 120) -> str:
        return self.command(label, self.base + list(args), timeout)

    def preflight(self) -> None:
        if not shutil.which("docker"):
            raise VerificationError("Docker CLI is unavailable; no Compose acceptance check ran.")
        self.report["docker"] = self.command(
            "Docker version", ["docker", "version", "--format", "{{.Server.Version}}"]
        )
        self.report["compose"] = self.command(
            "Compose version", ["docker", "compose", "version", "--short"]
        )
        self.report["commit"] = self.command("Tested commit", ["git", "rev-parse", "HEAD"])
        if self.command("Verify clean checkout", ["git", "status", "--porcelain"]):
            raise VerificationError("Fresh-checkout evidence requires a clean working tree.")
        self.report["clean_checkout"] = True
        for resource, listing in (
            ("containers", ["ps", "-aq"]),
            ("volumes", ["volume", "ls", "-q"]),
            ("networks", ["network", "ls", "-q"]),
        ):
            found = self.command(
                f"Check project {resource} are absent",
                [
                    "docker",
                    *listing,
                    "--filter",
                    f"label=com.docker.compose.project={self.project}",
                ],
            )
            if found:
                raise VerificationError("Project already has resources; cleanup is not authorized.")
        for port in (8000, 3000):
            try:
                with socket.socket() as listener:
                    listener.bind(("127.0.0.1", port))
            except OSError:
                raise VerificationError(
                    f"Loopback port {port} is occupied; existing services are preserved."
                ) from None
        config = json.loads(
            self.compose("Validate isolated Compose configuration", "config", "--format", "json")
        )
        validate_project(config, self.project)
        self.cleanup_allowed = True

    def probe(self, label: str, code: str) -> dict[str, Any]:
        output = self.compose(label, "exec", "-T", "api", "python", "-c", code)
        for line in output.splitlines():
            if line.startswith(MARKER):
                return json.loads(line[len(MARKER) :])
        raise VerificationError(f"{label} did not return a verification result.")

    def http(
        self, port: int, path: str, status: int, expected: dict[str, str] | None = None
    ) -> None:
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            try:
                try:
                    response = urlopen(f"http://127.0.0.1:{port}{path}", timeout=10)
                except HTTPError as error:
                    response = error
                with response:
                    body = response.read()
                    if response.status == status and (
                        expected is None or json.loads(body) == expected
                    ):
                        self.report.setdefault("http", []).append(
                            {"port": port, "path": path, "status": status, "body": expected}
                        )
                        return
            except OSError, URLError, ValueError:
                pass
            time.sleep(1)
        raise VerificationError(f"HTTP check failed: port {port}, {path}, expected {status}.")

    def runtime_boundaries(self) -> None:
        boundaries = {}
        for service, port in (("api", "8000/tcp"), ("web", "3000/tcp"), ("db", None)):
            uid = None
            identifier = self.compose(
                f"Find {service} container", "ps", "--all", "--quiet", service
            )
            if not re.fullmatch(r"[a-f0-9]{12,64}", identifier):
                raise VerificationError(f"Expected exactly one {service} container.")
            bindings = json.loads(
                self.command(
                    f"Inspect {service} port bindings",
                    [
                        "docker",
                        "inspect",
                        "--format",
                        "{{json .NetworkSettings.Ports}}",
                        identifier,
                    ],
                )
            )
            if service == "db":
                if any(bindings.values()):
                    raise VerificationError("Database unexpectedly publishes a host port.")
            else:
                assert port is not None
                if bindings != {port: [{"HostIp": "127.0.0.1", "HostPort": port.split("/")[0]}]}:
                    raise VerificationError(
                        f"{service} must bind only its documented loopback port."
                    )
                uid = self.compose(
                    f"Verify {service} non-root user", "exec", "-T", service, "id", "-u"
                )
                if not uid.isdigit() or int(uid) == 0:
                    raise VerificationError(f"{service} runs as root.")
            boundaries[service] = {"ports": bindings, "uid": uid}
        self.report["acceptance"]["M1-ENV-03"] = boundaries

    def verify(self) -> None:
        self.preflight()
        self.compose("Build README container images", "build", timeout=900)
        self.compose("Start fresh PostgreSQL", "up", "-d", "--wait", "--wait-timeout", "120", "db")
        self.compose(
            "Apply migrations using documented python command",
            "run",
            "--rm",
            "-T",
            "api",
            "python",
            "manage.py",
            "migrate",
            "--noinput",
        )
        self.compose(
            "Check model drift",
            "run",
            "--rm",
            "-T",
            "api",
            "python",
            "manage.py",
            "makemigrations",
            "--check",
            "--dry-run",
        )
        self.compose(
            "Start API and web",
            "up",
            "-d",
            "--wait",
            "--wait-timeout",
            "180",
            "api",
            "web",
            timeout=240,
        )
        self.http(3000, "/", 200)
        self.report["acceptance"]["M1-ENV-01"] = {
            "build": "passed",
            "startup": "passed",
            "fresh_project": True,
        }
        self.report["acceptance"]["M1-ENV-02"] = self.probe(
            "Verify application role and UUID schema", DATABASE_PROBE
        )
        self.runtime_boundaries()
        self.http(8000, "/api/v1/health/live", 200, {"status": "ok"})
        self.http(8000, "/api/v1/health/ready", 200, {"status": "ready"})
        self.http(3000, "/api/v1/health/ready", 200, {"status": "ready"})
        self.compose(
            "Run both frontend HTTP smoke tests",
            "exec",
            "-T",
            "-e",
            "SMOKE_TEST_URL=http://127.0.0.1:3000",
            "-e",
            "SMOKE_TEST_API=1",
            "web",
            "npm",
            "run",
            "test:smoke",
        )
        before = self.probe(
            "Provision synthetic owner through the identity service",
            "SEED = True\n" + IDENTITY_SNAPSHOT,
        )
        self.compose("Stop only the verification database", "stop", "db")
        self.http(8000, "/api/v1/health/ready", 503, {"status": "unavailable"})
        self.http(8000, "/api/v1/health/live", 200, {"status": "ok"})
        self.http(3000, "/api/v1/health/ready", 503, {"status": "unavailable"})
        self.report["acceptance"]["M1-ENV-04"] = {
            "healthy": "passed",
            "forwarding": "passed",
            "database_unavailable": "passed",
            "smoke_tests": 2,
        }
        self.compose("Stop stack without removing its volume", "down")
        self.compose(
            "Restart stack with its existing volume",
            "up",
            "-d",
            "--wait",
            "--wait-timeout",
            "180",
            timeout=240,
        )
        after = self.probe(
            "Verify persisted identities and membership audit", "SEED = False\n" + IDENTITY_SNAPSHOT
        )
        if before != after:
            raise VerificationError("Synthetic identity state changed after the stack restart.")
        self.http(8000, "/api/v1/health/ready", 200, {"status": "ready"})
        self.http(3000, "/api/v1/health/ready", 200, {"status": "ready"})
        self.report["acceptance"]["M1-ENV-05"] = after
        self.report["acceptance"]["M1-ENV-06"] = (
            "Automation evidence recorded; review with README and the dated verification record."
        )
        self.report["status"] = "passed"

    def cleanup(self) -> None:
        if self.cleanup_allowed:
            self.compose(
                "Remove only this disposable project and its volume",
                "down",
                "--volumes",
                "--remove-orphans",
            )
            self.report["cleanup"] = "passed"
        else:
            self.report["cleanup"] = "not authorized; no project resources touched"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/compose-verification.json")
    args = parser.parse_args()
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="compose-check-", dir=cache) as directory:
        scratch = Path(directory).resolve()
        if not scratch.is_relative_to(cache.resolve()):
            raise VerificationError(
                "Temporary verification directory escaped the repository cache."
            )
        verification = ComposeVerification(scratch)
        try:
            verification.verify()
        except (VerificationError, ValueError, KeyError) as error:
            verification.report["status"] = "failed"
            verification.report["failure"] = verification.redact(str(error))
            print(verification.report["failure"], file=sys.stderr)
        finally:
            try:
                verification.cleanup()
            except VerificationError as error:
                verification.report["status"] = "failed"
                verification.report["cleanup"] = verification.redact(str(error))
            verification.report["finished_at"] = datetime.now(UTC).isoformat()
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                verification.redact(json.dumps(verification.report, indent=2)) + "\n",
                encoding="utf-8",
            )
    print(f"Compose verification: {verification.report['status']}. Evidence: {args.output}")
    return 0 if verification.report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
