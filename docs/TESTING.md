# Testing and quality checks

The application foundation uses the tooling in ADRs [0004](adr/0004-use-uv-and-foundation-tooling.md)
and [0005](adr/0005-establish-automated-quality-checks.md). Run commands from the
repository root using Python 3.14, uv 0.13.2, Node.js 24, and npm 11.

## Install the locked tools

```powershell
uv sync --locked
npm --prefix frontend ci
```

Do not maintain a second Python dependency manifest. Both transitive lockfiles
are committed; new direct dependencies must have exact versions and a concrete use.

## Fast checks: no running application or database required

```powershell
uv run ruff check backend infra/scan_secrets.py
uv run ruff format --check backend infra/scan_secrets.py
uv run mypy
uv run python backend/manage.py check --settings=config.settings.test
uv run python backend/manage.py test tests.unit tests.contract --settings=config.settings.test --verbosity 2
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend test
uv run python infra/scan_secrets.py
```

`config.settings.test` temporarily supplies an ephemeral secret and explicit test
hosts without changing the calling process's application environment. It never
uses `DATABASE_URL` or reads `.env`. mypy uses this settings module too; it checks
backend code and tests, including untyped function bodies, using Django/DRF stubs.
It does not enforce strict annotations on every function.

`npm test` runs synchronous React component tests once in jsdom. It needs no
server and fails when no tests exist. Use `npm --prefix frontend run test:watch`
for interactive development. HTTP startup tests are deliberately separate.

## PostgreSQL integration and migrations

Authentication scenarios in `tests.integration.test_identity` include concurrent
reset reuse, owner provisioning, shared rate counters, session lifecycle, and
workspace policy checks. They require PostgreSQL; component tests and mocked
database-free CSRF tests do not prove these persistence guarantees. See
[authentication operation](AUTHENTICATION.md) and
[verification](AUTHENTICATION_VERIFICATION.md).

Use PostgreSQL 17, matching Compose and CI. Supply `TEST_DATABASE_URL` in your
process environment, pointing to a **dedicated disposable test instance** with a
role allowed to create databases. Use a separate test database and credentials;
the normal Compose application role has no database-creation privileges.
URL-encode any special characters in credentials. Do not commit the URL or put
real values in fixtures, reports, or shell scripts.

```powershell
uv run python backend/manage.py makemigrations --check --dry-run --settings=config.settings.test
uv run python backend/manage.py migrate --noinput --settings=config.settings.test
uv run python backend/manage.py test tests financial_services --settings=config.settings.test --verbosity 2
```

Migration commands operate on the disposable source database in
`TEST_DATABASE_URL`. The test runner creates/destroys **`test_financial_services`**
on that server; never point it at a server where that name contains valuable data.
Without a URL, the test settings use an uncredentialed loopback test database,
allowing unit/contract tests to start; integration tests fail if PostgreSQL is
unavailable. They are not silently skipped or replaced with SQLite.

The current database integration test exercises the readiness endpoint with a
real PostgreSQL connection. No identity or ledger migrations exist yet. Adding
schema or domain behavior must add the corresponding tests rather than treating
the readiness test as evidence of accounting or tenant correctness.

## HTTP startup checks

With the frontend and API already running:

```powershell
$env:SMOKE_TEST_URL = 'http://localhost:3000'
$env:SMOKE_TEST_API = '1'
npm --prefix frontend run test:smoke
```

Missing `SMOKE_TEST_URL` is an error. `SMOKE_TEST_API=1` additionally requires the
frontend's same-origin `/api/v1/health/live` route to reach Django. Leave the API
flag unset only for an intentional frontend-only smoke check; that API test then
reports a skip. CI sets both variables and requires both tests to pass.

CI's loopback WSGI test server exercises only public health routing without a
database. The backend job separately provisions PostgreSQL for migration and
readiness evidence. These are testing tools, not production serving instructions.

## Dependency and secret scans

```powershell
New-Item -ItemType Directory -Force .cache | Out-Null
uv export --locked --no-emit-project --format requirements-txt --output-file .cache/audit-requirements.txt
uv run pip-audit --require-hashes --disable-pip -r .cache/audit-requirements.txt
npm --prefix frontend run audit
uv run python infra/scan_secrets.py
```

Dependency audits require access to public vulnerability data. A network failure
is not a successful audit. Python audits include runtime and development groups;
npm audits fail for high/critical findings under the existing scaffold policy.

The secret scan uses pinned detect-secrets rules with credential verification
over the network disabled. It scans current contents of tracked files and
non-ignored new files, so it works before staging. It exits nonzero on findings
or scanner errors and prints locations/detector types without secret values.
Ignored local `.env`, caches, and dependency directories are not read. Tracked
files remain included even if an ignore rule later matches them. No baseline or
blanket exclusion is used. The scanner has positive/negative/redaction tests in
disposable repositories using an incomplete synthetic key marker.

The scan does not inspect Git history, remote-only refs, container layers, or
ignored files. Do not mark the roadmap's combined current-tree/history credential
gate complete based on this scan. If a real credential is found, follow the
rotation and exposure procedure in AGENT.md; do not simply baseline it away.

## Test placement and future coverage

| Area | Location and requirement |
|---|---|
| Owning domain | Module-level tests beside each backend module; keep domain rules out of API/UI tests |
| Shared unit tests | `backend/tests/unit/`; no database access |
| API/configuration/tool contracts | `backend/tests/contract/`; use `SimpleTestCase` when persistence is unnecessary |
| Persistence and cross-module behavior | `backend/tests/integration/`; real PostgreSQL and isolated Django test cases |
| React components | `*.test.tsx` beside components or under `frontend/tests/`; user-facing role/name assertions |
| Running HTTP application | `frontend/tests/startup.test.mjs` via `test:smoke` |

CI discovers `tests` and `financial_services` so future module-level tests are
included. Monetary expectations must come from accepted financial semantics, not
copies of implementation calculations. Add property-based tests for splits,
transfers, and invariants with the ledger; add cross-workspace authorization tests
with identity. Imports, reports, budgets, and goals need their documented examples
as those modules are implemented.

jsdom and HTML checks do not establish actual keyboard navigation, responsive
layout, screen-reader behavior, or async server-component workflows. Add browser
tests when those flows exist. No numeric coverage target has been adopted.

## CI and verification status

`.github/workflows/scaffold.yml` contains backend, frontend, and secret-scan jobs.
Jobs use locked installs, pinned Actions, read-only repository access, and bounded
timeouts. Backend CI provisions PostgreSQL 17; the frontend job runs component
tests and a production build before both HTTP smoke checks. The separate secret
job scans the checked-out working tree.

Local evidence and outstanding verification are recorded in
[TESTING_VERIFICATION.md](TESTING_VERIFICATION.md). A parsed workflow is not a
successful hosted run; PostgreSQL integration checks remain unverified locally
on a machine without PostgreSQL/Docker. Authentication, accounting, browser flows,
historical secret review, and backup/restore remain separate milestone work.
