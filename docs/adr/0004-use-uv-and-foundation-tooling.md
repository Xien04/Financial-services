# ADR 0004: Use uv and the foundation toolchain

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-10-22 |
| Accepted by | Brenson Go in the scaffold conversation on 2026-10-22, selecting uv instead of pip |
| Related documents | [ADR 0001](0001-use-django-modular-monolith.md), [ADR 0003](0003-use-postgresql.md), [roadmap](../ROADMAP.md) |

## Context

The accepted application layout needs reproducible dependency installation and a
local startup path. The product owner selected uv for the Python workflow.

## Decision

- Use Python 3.14 and Django 5.2 LTS with Django REST Framework.
- Manage the backend from root `pyproject.toml` and `uv.lock` using uv 0.13.2.
  Pin direct dependencies exactly and commit uv's transitive lock. Use
  `uv sync --locked` for reproducible installs. Root `requirements.txt` is retired;
  export requirements from uv only when a consuming tool needs that format.
- Use Node.js 24, npm 11, Next.js 16, React, and TypeScript. Commit exact direct
  versions and `frontend/package-lock.json`; use `npm ci` for repeatable installs.
- Use PostgreSQL 17 consistently in Compose and future integration CI.
- Use Django's test runner for backend tests, Ruff for Python formatting/linting,
  ESLint for the client, and TypeScript for client type checking. These are the
  initial checks, not a claim that all Milestone 1 quality gates are complete.
  Use the ESLint JavaScript and typescript-eslint recommended configurations;
  the current Next.js lint preset pulls in a dependency with an unpatched audit
  finding and is excluded from this scaffold.
- Use Docker Compose for the local development environment. Containers run as
  non-root users; only web/API ports bind to the host loopback interface.
- Keep this scaffold local-development only. Production Django settings fail
  closed on missing configuration. Production serving, TLS, authentication,
  background jobs, uploads, and detailed API conventions need their own work.

## Consequences

Contributors use uv and npm rather than maintaining parallel Python dependency
manifests. Runtime major versions are explicit; dependency patches are reviewed
through lock updates. A Django LTS favors stability over new framework features.
Health checks are the only public API views; future API views deny access by
default until identity and authorization are implemented. No default Django user
tables are migrated before the UUID identity model is established.

Dependency scanning runs in scaffold CI. Complete backend type checking, frontend
workflow tests, secret scanning, production deployment, backup/restore drills,
and application authorization remain Milestone 1 work.

## References

- [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)
- [uv Docker integration](https://docs.astral.sh/uv/guides/integration/docker/)
- [Django supported versions](https://www.djangoproject.com/download/)
- [Next.js 16 upgrade requirements](https://nextjs.org/docs/app/guides/upgrading/version-16)
- [PostgreSQL support policy](https://www.postgresql.org/support/versioning/)
