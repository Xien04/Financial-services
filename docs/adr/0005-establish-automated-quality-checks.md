# ADR 0005: Establish automated quality checks

| Field | Value |
|---|---|
| Status | Accepted for implementation |
| Date | 2026-10-22 |
| Decision owners | Engineering, within the product owner's authorized automated-testing task |
| Related documents | [Toolchain ADR](0004-use-uv-and-foundation-tooling.md), [testing guide](../TESTING.md), [roadmap](../ROADMAP.md) |

## Context

ADR 0004 already selects Django's test runner, Ruff, ESLint, TypeScript, and
dependency audits. The scaffold has backend health/configuration tests and an
HTTP frontend smoke check, but its default frontend command can skip every test
without a running server. Backend type checks and automated secret scanning are
still missing. Identity, ledger, and other core workflows do not exist yet.

## Decision

- Retain Django's test runner. Use `SimpleTestCase` for database-independent
  unit/contract tests and Django database test cases against PostgreSQL 17 for
  integration tests. Do not introduce pytest or SQLite.
- Add `config.settings.test`. Generate an ephemeral Django secret and consume
  only `TEST_DATABASE_URL` for test connectivity, independently of application
  credentials. Django creates/destroys `test_financial_services`; use a dedicated
  disposable PostgreSQL instance/role with database-creation privileges.
- Use Vitest, React Testing Library, jest-dom, and jsdom for synchronous React
  component tests. The default `npm test` executes these tests once and fails if
  none are found. Keep HTTP smoke checks under explicit `test:smoke`; missing
  `SMOKE_TEST_URL` is an error. CI checks the frontend's same-origin health API
  forwarding as well as its HTML response.
- Use mypy with Django and DRF stubs for backend type checks, including bodies of
  untyped functions. Do not impose a strict, repository-wide annotation policy or
  an arbitrary coverage percentage. Add types where needed for useful checking.
- Use the pinned detect-secrets scanner on tracked working-tree content and
  non-ignored new files. Fail on findings and scanner errors, print only
  file/line/detector information, and disable network credential verification.
  No baseline, blanket file exclusions, or credential submission to providers is
  introduced. This scan does not inspect Git history or ignored local secrets.
- Extend the existing CI workflow with these checks and keep dependency audits.
  Lock all new development dependencies through uv and npm.

## Consequences

Contributors can run unit/contract and frontend component tests without creating
local application secrets or starting the complete stack. Integration tests
continue to require real PostgreSQL. CI runs the same commands as local use.
The smoke API uses a loopback WSGI test server solely for HTTP routing evidence;
PostgreSQL readiness and migrations are checked separately in the backend job.

jsdom component tests and HTTP smoke checks do not prove browser layout, keyboard
interaction, screen-reader behavior, or asynchronous server-component behavior.
Browser workflow tests should be added when those workflows exist. Accounting
and property-based tests must accompany the ledger, and tenant-isolation tests
must accompany identity. These requirements are not satisfied by scaffold tests.

A clean scan is heuristic evidence, not proof that no credentials ever existed.
Historical scanning and a verified hosted CI run remain explicit follow-up gates.

## References

- [Django test isolation](https://docs.djangoproject.com/en/5.2/topics/testing/overview/)
- [Next.js Vitest setup and server-component limitations](https://nextjs.org/docs/app/guides/testing/vitest)
- [Django type checking](https://github.com/typeddjango/django-stubs)
- [detect-secrets CLI and verification controls](https://github.com/Yelp/detect-secrets)
