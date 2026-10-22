# Automated-testing verification — 2026-10-22

Scope: the Milestone 1 testing/quality-check task under ADRs 0001–0005. This
extends [the initial scaffold verification](SCAFFOLD_VERIFICATION.md); it does not
complete application foundation, prove financial correctness, or accept an MVP release.

## Verified locally

| Check | Evidence |
|---|---|
| uv lock consistency and locked install | Passed using uv 0.13.2 and the repository cache |
| npm clean locked install | Passed; 206 packages installed from the lockfile |
| Backend unit/contract tests | 21 passed, with no database setup |
| Test configuration isolation | Passed with deliberately invalid application settings and a separate test database URL |
| Backend mypy | Passed for 28 source files, with Django and DRF plugins |
| Ruff lint and formatting | Passed for backend code and the secret scanner |
| Django system checks with test settings | Passed |
| Frontend component tests | 3 passed in Vitest/jsdom; no running application required |
| Frontend ESLint and TypeScript | Passed |
| Next.js production build | Passed |
| Running frontend HTTP smoke checks | 2 passed; no skips, including same-origin forwarding to Django |
| Missing-target smoke behavior | Missing `SMOKE_TEST_URL` fails explicitly |
| Secret-scan behavior | Clean files pass; synthetic markers in new/modified files fail and remain redacted; ignored local files are excluded |
| Working-tree secret scan | No potential secrets detected; no baseline or broad exclusions |
| Python dependency audit | No known vulnerabilities in exported locked production/development dependencies |
| npm dependency audit | No known vulnerabilities |
| CI workflow structure | YAML parsed; backend, frontend, and secrets jobs present |

The HTTP exercise used temporary loopback servers and the built frontend. Django
ran through Python's WSGI test server with test settings; this tests HTTP routing,
not PostgreSQL availability or production deployment. The temporary processes
were stopped after the checks.

The scanner initially flagged the README's generic connection-URL placeholder.
It was replaced with prose instead of creating a scanner exception. No actual
credential was found by that check.

## Blocked or unverified

- **Local PostgreSQL integration:** attempted the dedicated integration command;
  database creation failed with a connection timeout because no PostgreSQL test
  service is reachable on this machine. No integration test passed and no
  migration evidence is claimed. Docker/PostgreSQL remain unavailable locally.
- **Clean database migrations:** configured in CI, not verified locally without
  PostgreSQL. No identity or ledger schema exists yet.
- **Hosted CI:** workflow checks are implemented and YAML was parsed, but a
  successful GitHub Actions run has not been observed. Review the first run
  after publishing this branch before calling the CI gate complete.
- **Historical secrets:** the new scanner covers current tracked/non-ignored
  working-tree files, not Git history or remote-only refs. The roadmap's combined
  tree/history requirement remains open.
- **Future workflows:** browser accessibility, identity/tenant isolation,
  accounting/property tests, imports, reports, planning, and backup/restore
  verification must accompany their respective implementations. Scaffold tests
  are not substitutes for those requirements.

The remaining environment input is a disposable PostgreSQL 17 service with a
test role allowed to create databases, supplied through `TEST_DATABASE_URL`, or
an observed successful hosted CI run using the configured PostgreSQL service.
Never paste real credentials into issues, documentation, or chat.
