# Compose foundation verification — issue #11

Scope: `M1-ENV-01` through `M1-ENV-06` in
[issue #11](https://github.com/Xien04/Financial-services/issues/11), under accepted
ADRs 0001, 0003, 0004, and the existing quality-check tooling in ADR 0005.

## Execution environment and status

On 2026-10-27, Docker was unavailable on the Windows development host. The product
owner selected GitHub Actions for the complete Compose verification. The new
`compose` job runs `infra/verify_compose.py` on a fresh Linux runner checkout.
Runtime results are pending the first run; no Compose acceptance item is claimed
complete by the database-independent safety tests alone.

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
| M1-ENV-01: clean build and startup | Awaiting full Compose CI run |
| M1-ENV-02: migrations, UUIDs, application-role permissions | Awaiting full Compose CI run |
| M1-ENV-03: runtime users and network boundaries | Awaiting full Compose CI run |
| M1-ENV-04: health, forwarding, and database failure | Awaiting full Compose CI run |
| M1-ENV-05: identity persistence after restart | Awaiting full Compose CI run |
| M1-ENV-06: reproducible evidence and documentation | Procedure and automation added; runtime evidence pending |

## Limits

The selected runtime environment is hosted Linux Docker, not this Windows host.
Initial owner setup in automation calls the existing identity service with a
generated password; it does not exercise the interactive terminal prompt or a
browser login. Full authentication/browser/SMTP workflows, production proxy/TLS,
backups/restoration, historical secret scanning, and financial workflows retain
their own issues and acceptance gates. Completing this check does not complete
Milestone 1 or establish production readiness.
