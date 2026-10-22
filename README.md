# Financial Services

Financial Services is a privacy-first, self-hostable personal-finance application
for Philippine-peso accounts, transactions, imports, budgets, goals, and reports.
The accepted accounting model uses immutable balanced ledger entries behind a
familiar transaction interface.

## Status

**Milestone 1 — application foundation.** The Django/REST API and Next.js/TypeScript
scaffold, six module packages, local Compose configuration, and startup checks are
present. Authentication, UUID identity models, ledger models, and workflows are not
implemented. This scaffold is for local development. See the
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
- `DATABASE_URL`: `postgresql://APP_USER:APP_PASSWORD@db:5432/DATABASE_NAME`,
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

Migrations are explicit. No application models or migrations exist yet. Identity
work must establish a UUID user model before Django auth migrations are introduced.
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
uv run ruff check backend
uv run ruff format --check backend
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Backend commands require `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and
`DATABASE_URL` in the process environment, or `uv run --env-file .env`.
Use `localhost,127.0.0.1,testserver` for local/test allowed hosts. Host commands
need a reachable PostgreSQL host in `DATABASE_URL`; Compose's `db` hostname works
only inside Compose. SQLite is not a supported substitute.

```powershell
uv run python backend/manage.py check
uv run python backend/manage.py test tests.contract --verbosity 2
uv run python backend/manage.py test tests.integration --verbosity 2
```

Contract tests do not access a database. Integration tests require PostgreSQL 17
and a dedicated test role allowed to create a test database; the Compose
application role intentionally lacks that privilege. Use disposable test data.

Run the frontend startup test against the running application:

```powershell
$env:SMOKE_TEST_URL = 'http://localhost:3000'
npm --prefix frontend test
```

The test explicitly skips when `SMOKE_TEST_URL` is absent. It checks served page
semantics; browser accessibility and workflow coverage remain separate work.
For client-only development, `npm --prefix frontend run dev` serves the starter
page; `API_INTERNAL_URL` defaults to `http://127.0.0.1:8000`.

## Dependency checks and remaining gates

The scaffold CI workflow defines formatting/linting, PostgreSQL migrations and
backend tests, frontend lint/type/build/startup checks, and dependency audits.
Its first hosted run still needs verification. Run audits locally with:

```powershell
New-Item -ItemType Directory -Force .cache | Out-Null
uv export --locked --no-emit-project --format requirements-txt --output-file .cache/audit-requirements.txt
uv run pip-audit --require-hashes --disable-pip -r .cache/audit-requirements.txt
npm --prefix frontend run audit
```

`pip-audit` is a vulnerability scanner invoked through uv, not the dependency
installation workflow. Exported requirements are ignored tool output.

Milestone 1 still needs authentication/session decisions, UUID identity and
workspace permissions, detailed API/OpenAPI/idempotency conventions, backend type
checks, frontend workflow tests, secret scanning, structured logging, production
hosting, and documented backup/restore drills. Scaffold checks alone do not
complete the milestone.

## Documentation

- [Product architecture](docs/PRODUCT_ARCHITECTURE.md)
- [Financial semantics](docs/FINANCIAL_SEMANTICS.md)
- [Accepted wireframes](docs/PRODUCT_WIREFRAMES.md)
- [Delivery roadmap](docs/ROADMAP.md)
- [Architecture decision records](docs/adr/README.md)
