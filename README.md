# Financial Services

Financial Services is a privacy-first, self-hostable personal-finance application
for Philippine-peso accounts, transactions, imports, budgets, goals, and reports.
The accepted accounting model uses immutable balanced ledger entries behind a
familiar transaction interface.

## Status

**Milestone 1 — application foundation.** The Django/REST API and Next.js/TypeScript
scaffold, six module packages, local Compose configuration, and startup checks are
present. Email/password authentication, recovery, UUID identity models, initial
owner provisioning, and workspace policy services are implemented. PostgreSQL
migrations and integration tests pass in hosted CI; local Compose startup,
complete browser workflows, and SMTP delivery remain unverified. Ledger models and
financial workflows are not implemented. This environment is for local development. See the
[roadmap](docs/ROADMAP.md) and [tooling ADR](docs/adr/0004-use-uv-and-foundation-tooling.md).
Local check results and remaining verification are recorded in
[scaffold verification](docs/SCAFFOLD_VERIFICATION.md).

## Toolchain and layout

- Python 3.14, uv 0.13.2, Django 5.2 LTS, Django REST Framework, Psycopg
- Node.js 24, npm 11, Next.js 16, React, TypeScript
- PostgreSQL 17.11 for local development and integration CI
- `backend/config/`: settings, API routes, ASGI/WSGI, health checks
- `backend/financial_services/`: identity, ledger, imports, planning, reporting, integrations
- `backend/tests/`: contract and PostgreSQL integration tests
- `frontend/src/app/`, `src/features/`, `src/lib/`: routes, workflow UI, shared utilities
- `infra/` and root `compose.yaml`: local container definitions

Exact application dependencies live in `pyproject.toml`, `uv.lock`,
`frontend/package.json`, and `frontend/package-lock.json`. Use uv rather than
maintaining a separate requirements file. Celery, Redis, and object storage remain
planned; no scaffold jobs or uploads need them yet.

## Start locally with Docker Compose

Install Docker with Compose v2. From the repository root in PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit the ignored `.env` and supply these values:

- `POSTGRES_DB`: your local database name.
- `POSTGRES_USER`: a local database administrator name.
- `POSTGRES_PASSWORD`: a randomly generated administrator password.
- `APP_DB_USER`: a different application role name.
- `APP_DB_PASSWORD`: a different randomly generated application password.
- `DJANGO_SECRET_KEY`: a separate random secret, at least 50 characters.
- `DATABASE_URL`: a PostgreSQL connection URL using your application role,
  substituting the application credentials and database name above. URL-encode
  special characters in credentials. Hexadecimal passwords avoid URL escaping.

With Python available, `python -c "import secrets; print(secrets.token_hex(32))"`
generates one random value. Generate a separate value for each secret. Never
commit `.env`. Other template variables describe future configuration and are
not consumed by this scaffold unless noted in the code.

```powershell
docker compose build
docker compose up -d db
docker compose run --rm api python manage.py migrate --noinput
docker compose up -d api web
docker compose ps
```

Open [the application](http://localhost:3000). The API exposes
[liveness](http://localhost:8000/api/v1/health/live) and
[readiness](http://localhost:8000/api/v1/health/ready). Liveness needs no database;
readiness returns HTTP 503 while the database is unavailable, without exception
details. Next.js forwards `/api/*` to Django on the private Compose network.

Migrations are explicit. The initial identity migration establishes the UUID user
model before sessions/authentication are used. After migrating, run
`docker compose run --rm api python manage.py provision_owner` in an interactive
terminal to create the first account and personal workspace. Public registration
is disabled. See [authentication setup](docs/AUTHENTICATION.md) for password
recovery, SMTP configuration, session maintenance, and operator recovery.
The application role can create schema objects but cannot administer PostgreSQL.
Initialization runs only when the data volume is empty; changing `.env` does not
rotate credentials on an existing database. Use a database role-management
procedure to change credentials on an existing volume.

Only web/API ports bind to host loopback. PostgreSQL has no published host port.
Rebuild changes with `docker compose up -d --build`. Stop with
`docker compose down`; this preserves the database volume. The containers use
development servers and are not a production deployment.

## Host development tools

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) 0.13.2 and
Node.js 24 with npm 11. Restart the terminal after installing uv if it cannot find
the executable. From the repository root:

```powershell
uv sync --locked
npm --prefix frontend ci
uv run ruff check backend infra/scan_secrets.py
uv run ruff format --check backend infra/scan_secrets.py
uv run mypy
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Application commands require `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and
`DATABASE_URL` in the process environment, or `uv run --env-file .env`.
Use `localhost,127.0.0.1,testserver` for local/test allowed hosts. Host commands
need a reachable PostgreSQL host in `DATABASE_URL`; Compose's `db` hostname works
only inside Compose. SQLite is not a supported substitute.

```powershell
uv run python backend/manage.py check
uv run python backend/manage.py test tests.unit tests.contract --settings=config.settings.test --verbosity 2
uv run python infra/scan_secrets.py
```

The test settings generate an ephemeral secret and do not read application
database credentials. Unit/contract tests and component tests run without a
database or running application. Integration tests require PostgreSQL 17 and
`TEST_DATABASE_URL` pointing to a dedicated disposable test instance/role with
database-creation privileges. Django creates/destroys `test_financial_services`
on that server. The Compose application role intentionally lacks that privilege.
See [the testing guide](docs/TESTING.md) for commands, isolation, and test placement.

Run the frontend startup test against the running application:

```powershell
$env:SMOKE_TEST_URL = 'http://localhost:3000'
npm --prefix frontend run test:smoke
```

The smoke command fails if `SMOKE_TEST_URL` is absent. Set `SMOKE_TEST_API=1`
to also check same-origin forwarding to Django. CI requires both smoke tests.
These check served HTML/API responses; browser accessibility and workflow
coverage remain separate work. The default `npm test` runs component tests.
For client-only development, `npm --prefix frontend run dev` serves the starter
page; `API_INTERNAL_URL` defaults to `http://127.0.0.1:8000`.

## Dependency checks and remaining gates

The quality CI workflow defines formatting/linting, backend and frontend type
checks, PostgreSQL migrations and backend tests, frontend component/build/startup
checks, dependency audits, and working-tree secret scanning.
Hosted checks passed on 2026-10-27; see
[authentication verification](docs/AUTHENTICATION_VERIFICATION.md) for evidence
and remaining limits. Run audits locally with:

```powershell
New-Item -ItemType Directory -Force .cache | Out-Null
uv export --locked --no-emit-project --format requirements-txt --output-file .cache/audit-requirements.txt
uv run pip-audit --require-hashes --disable-pip -r .cache/audit-requirements.txt
npm --prefix frontend run audit
```

`pip-audit` is a vulnerability scanner invoked through uv, not the dependency
installation workflow. Exported requirements are ignored tool output.

Authentication/session strategy and role permissions are accepted in
[ADR 0006](docs/adr/0006-use-django-sessions-for-browser-authentication.md),
with implementation details in [ADR 0007](docs/adr/0007-implement-authentication-rate-limits.md).
Identity and authentication code now exists, with verification limitations in
[authentication verification](docs/AUTHENTICATION_VERIFICATION.md).
Milestone 1 still needs full local Compose verification,
detailed API/OpenAPI/idempotency conventions, complete browser and SMTP
workflow tests, historical secret scanning, structured logging, production
hosting, and documented backup/restore drills. Foundation checks alone do not
complete the milestone.

## Documentation

- [Product architecture](docs/PRODUCT_ARCHITECTURE.md)
- [Financial semantics](docs/FINANCIAL_SEMANTICS.md)
- [Accepted wireframes](docs/PRODUCT_WIREFRAMES.md)
- [Delivery roadmap](docs/ROADMAP.md)
- [Architecture decision records](docs/adr/README.md)
- [Testing and quality checks](docs/TESTING.md)
- [Authentication setup and operation](docs/AUTHENTICATION.md)
