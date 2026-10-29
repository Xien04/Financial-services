# Shared API verification — issue #14

Scope: `M1-API-01` through `M1-API-06` in
[issue #14](https://github.com/Xien04/Financial-services/issues/14), under accepted
ADRs [0008](adr/0008-standardize-api-contracts.md) and
[0009](adr/0009-make-financial-writes-idempotent.md).
The implementation and scope exceptions are described in [API contracts](API_CONTRACT.md).

## Tested source and environment

On 2026-10-28, [PR #24](https://github.com/Xien04/Financial-services/pull/24)
passed all four quality jobs in
[the pull-request run](https://github.com/Xien04/Financial-services/actions/runs/40775517528)
and [the source-branch run](https://github.com/Xien04/Financial-services/actions/runs/40775507684).
The implementation source is `df8c92fd2b42782ea4bdcde7370240699ecaa22c`.
The PR run checked out merge commit `0dcc6123431e5753e55c818eea855b2550b024db`
against base `a3b961d8c8b8fed21f4d0e2f44ed9af5463971c7`.

Local checks ran on Windows without Docker or a running PostgreSQL instance.
Following the product owner's earlier authorization, disposable PostgreSQL and
complete container verification ran in GitHub Actions on Linux. No existing
operator database, volume, or credentials were used.

Before adding the dependency, an isolated Python 3.14.8 environment with pinned
Django 5.2.18, DRF 3.18.3, and psycopg 3.3.6 tested drf-spectacular 0.30.0.
Schema generation, OpenAPI 3.0.3 validation, and an explicitly annotated APIView
HTTP request passed. The repository then passed its actual generation, route,
PostgreSQL, and container checks with those same framework pins. No framework
downgrade or schema-tool substitution was needed.

## Actual checks and results

All commands below exited zero in the linked hosted run. Python commands run at
the repository root; frontend commands run in `frontend/`, as configured in
`.github/workflows/scaffold.yml`.

| Command | Recorded result |
|---|---|
| `uv sync --locked` | Installed the committed dependency graph |
| `uv run ruff check backend infra` | All checks passed |
| `uv run ruff format --check backend infra` | 56 files already formatted |
| `uv run mypy` | No issues in 56 source files |
| `uv run python backend/manage.py check --settings=config.settings.test` | No issues |
| `uv run python infra/check_api_schema.py` | Validates without warnings and matches committed contract |
| `uv run python backend/manage.py makemigrations --check --dry-run --settings=config.settings.test` | No changes detected |
| `uv run python backend/manage.py migrate --noinput --settings=config.settings.test` | Migrations succeeded against PostgreSQL 17.11 |
| `uv run python backend/manage.py test tests financial_services --settings=config.settings.test --noinput --verbosity 2` | 80 tests passed in 2.697 seconds, including authentication, authorization, concurrency, and API contracts |
| `uv export --locked --no-emit-project --format requirements-txt --output-file .cache/audit-requirements.txt` and `uv run pip-audit --require-hashes --disable-pip -r .cache/audit-requirements.txt` | No known vulnerabilities |
| `npm ci`, `npm run lint`, `npm run typecheck` | Passed |
| `npm test` | 20 tests passed across three files |
| `npm run build` | Production build passed |
| `npm run audit` | Zero vulnerabilities |
| `npm run test:smoke` with the running frontend/API and required smoke-test settings | Both HTTP tests passed |
| `uv run --no-sync python infra/verify_compose.py` after runtime-only dependency sync | All 29 recorded commands and final cleanup passed |
| `uv run python infra/scan_secrets.py` | 121 files, zero potential secrets |

Locally, the equivalent installed virtualenv executables passed Python
lint/format/types, Django configuration, schema validation, and all 61
database-independent unit/contract tests. Frontend lint/types, all 20 tests, and
the production build passed. Both dependency audits and working-tree scanning
passed; the npm audit required network access after a sandbox network failure.
The five scanner annotations mark fixed password-validation text, not credentials;
the scanner itself and its positive/negative detection tests are unchanged.

The Compose report records Docker 29.4.2, Compose 2.40.3, Linux x86_64/glibc 2.43,
and tester `Compose verification automation`. Its checks ran from 21:52:47 to
21:54:46 UTC on 2026-10-28. Fresh image build/startup, application-role migrations,
runtime/network boundaries, exact probe bodies during a database outage,
frontend forwarding, identity persistence after restart, and final cleanup passed.
The sanitized JSON report is in the linked run's Compose job logs and summary.
These are regression checks; this issue claims only its own API acceptance IDs.

## Acceptance evidence

| Criterion | Evidence |
|---|---|
| M1-API-01: validation and safe errors | Strict declared-field/object validation, malformed/duplicate/nonfinite JSON and unsupported media rejection; safe framework/CSRF/404/500/503/429 handling; unknown names and synthetic sensitive markers never echoed; at most 100 field errors |
| M1-API-02: request IDs | Fresh UUIDv4 per attempt; caller IDs discarded; header/body equality; unchanged success/204/probe bodies; synchronous concurrency, asynchronous requests, and failure cleanup tests |
| M1-API-03: executable OpenAPI | Ten actual operations, separate inputs/outputs, strict input schemas, session cookie authentication, anonymous CSRF header/cookie requirements, response status/header schemas, actual anonymous/authenticated response validation including UUID/email formats |
| M1-API-04: contract drift | Warning-failing deterministic generation and committed artifact comparison in CI; negative tests reject a missing or changed artifact; local generation/update commands documented |
| M1-API-05: applicable pagination/idempotency | Current singleton authentication/health routes require neither; no financial placeholders or password/session response replay added; future signed cursor and durable financial operation requirements documented with owning milestones |
| M1-API-06: reproducible evidence | Source/merge commits, dated job links, actual commands/results, compatibility evidence, contributor documentation, passing existing PostgreSQL/authentication suite, and explicit exceptions recorded here |

`backend/tests/contract/test_api_contract.py` contains 17 new contract scenarios.
`backend/tests/integration/test_identity.py` additionally validates authenticated
and recovery responses against the generated schemas using actual PostgreSQL.
Frontend tests cover field errors, matching support references, safe transport
fallbacks, and removal of client-only password confirmation from requests.

## Intentional exceptions and remaining gates

- Health probes retain their exact small success/readiness-failure bodies;
  other API errors use the shared envelope. Successful 204s remain empty.
- Schema JSON is served only with local development settings; production/test
  defaults disable the route. No interactive docs, remote scripts, or client SDK
  are introduced.
- No current route needs pagination or a financial operation key. Signed cursor
  tests begin with a real collection; financial posting, canonical command
  identity, receipts, and actual posting concurrency/rollback belong to Milestone 2.
- Request IDs are available in request context. Structured/redacted logging is
  #15; production proxy/header verification is #16. Full browser/SMTP evidence,
  backup/restore, and published-history secret verification remain separate gates.
- This change adds no database migration or monetary behavior. Rollout requires
  the updated locked dependency install and frontend/backend together because
  unknown request fields are now rejected. It does not complete Milestone 1.

The verification commits following the tested implementation update documentation
only. The PR's current-head checks remain the authoritative merge gate.
