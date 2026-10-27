# Compose foundation verification — issue #11

Scope: `M1-ENV-01` through `M1-ENV-06` in
[issue #11](https://github.com/Xien04/Financial-services/issues/11), under accepted
ADRs 0001, 0003, 0004, and the existing quality-check tooling in ADR 0005.

## Execution environment and status

On 2026-10-27, Docker was unavailable on the Windows development host. The product
owner selected GitHub Actions for the complete Compose verification. The new
`compose` job runs `infra/verify_compose.py` on a fresh Linux runner checkout.

[The first complete run](https://github.com/Xien04/Financial-services/actions/runs/40569801429)
passed all four jobs on 2026-10-27 for source commit `91d2191`: Compose, backend,
frontend, and secrets. The Compose job ran from 19:31:00 to 19:33:02 UTC. Its
sanitized JSON report records the actual checked-out commit, Docker/Compose
versions, OS, UTC timestamps, tester (`Compose verification automation`), command
exit codes, HTTP results, acceptance evidence, and final cleanup. The report is
published in the run summary; subsequent runs also expose it in the job logs.

[The report-publication run](https://github.com/Xien04/Financial-services/actions/runs/40570416177)
also passed all 29 recorded commands and final cleanup from a clean checkout.
It used Docker 29.4.2 and Compose 5.1.3 on Linux x86_64 with glibc 2.43; API/web
user IDs were 10001/1000, and PostgreSQL had no published port. The checked-out
merge commit was `f803bf5`, for source `b95d4d1`. Because the issue names a Compose
v2 baseline, CI now explicitly selects Compose v2.40.3 through the official,
commit-pinned Docker setup action. Verification of that baseline is pending its
first run; the results above describe the newer runner-default plugin.

The same run passed all 62 backend tests (including seven harness safety/syntax
checks), 15 frontend component/transport tests, both existing HTTP smoke tests,
lint/formatting/type checks, both dependency audits, and working-tree secret
scanning. Locally, all 44 database-independent backend unit/contract tests,
lint/formatting/mypy, workflow/pinned-Action assertions, and the secret scan
passed. Docker execution was performed on hosted Linux, not the Windows host.

## Startup correction

The API image installed Django and other dependencies into `/app/.venv`, but did
not put its executables on `PATH`. Its default server command used the explicit
virtualenv path, while the README migration/provisioning commands invoked
`python` and therefore selected the base interpreter. The image now adds
`/app/.venv/bin` to `PATH`. The Compose check runs the documented `python
manage.py migrate --noinput` command against the actual image.

## Repeat the check

Prerequisites: a clean checkout, the repository's Python/uv toolchain, Docker
with Compose v2 (`up --wait` and JSON config support), and free loopback ports
3000 and 8000.

```powershell
uv run --locked python infra/verify_compose.py
```

The script follows the README startup sequence using a newly named project,
temporary generated credentials, and a fresh PostgreSQL volume. It checks that
no resources already use that project, rejects shared/external resources and
explicit container names, and removes inherited application/Compose settings.
It does not load the operator's `.env`. Temporary configuration lives under the
ignored `.cache` directory, outside the Docker build context.

The recorded sequence builds both images, starts PostgreSQL, runs migrations and
model-drift checks as the application role, starts API/web, and then checks:

- Five identity UUID columns; successful application-schema writes; denied
  `CREATE DATABASE` and `CREATE ROLE` operations; no superuser privileges.
- Actual API/web user IDs and loopback port bindings; no published database port.
- Direct and frontend-forwarded readiness, two existing frontend HTTP smoke
  tests, and sanitized HTTP 503 readiness with continuing liveness during a
  database outage.
- A synthetic owner/workspace/membership/audit snapshot created through the
  existing identity service, retained unchanged across `compose down` and `up`
  without removing its volume.

The final cleanup removes only the newly created verification project and its
disposable volume. The script does not remove images, existing operator volumes,
or another Compose project. `.cache/compose-verification.json` records sanitized
commands/results, tool versions, UTC timestamps, tester, environment, commit,
HTTP outcomes, cleanup, and acceptance evidence. CI publishes the same JSON in
its run summary. Credential values and raw identity snapshots are not published.

## Acceptance evidence

| Criterion | Current evidence |
|---|---|
| M1-ENV-01: clean build and startup | Passed: fresh project/volume, both images built, README migration command succeeded, API/web started, frontend returned HTTP 200 |
| M1-ENV-02: migrations, UUIDs, application-role permissions | Passed: migrations/model drift, five UUID columns, schema create/drop, no superuser flag, actual database/role creation denied |
| M1-ENV-03: runtime users and network boundaries | Passed: API/web UID nonzero, documented loopback bindings, no published PostgreSQL port |
| M1-ENV-04: health, forwarding, and database failure | Passed: direct/forwarded readiness HTTP 200; readiness HTTP 503 with exact sanitized JSON during outage; liveness HTTP 200; two frontend HTTP smoke tests |
| M1-ENV-05: identity persistence after restart | Passed: identical synthetic user/workspace/membership/audit fingerprint after down/up retaining the volume; readiness restored |
| M1-ENV-06: reproducible evidence and documentation | Passed: repeatable script, corrected README startup, dated record, actual CI report and tool/environment/commit metadata; final disposable-project cleanup passed |

## Limits

The selected runtime environment is hosted Linux Docker, not this Windows host.
Initial owner setup in automation calls the existing identity service with a
generated password; it does not exercise the interactive terminal prompt or a
browser login. Full authentication/browser/SMTP workflows, production proxy/TLS,
backups/restoration, historical secret scanning, and financial workflows retain
their own issues and acceptance gates. Completing this check does not complete
Milestone 1 or establish production readiness.
