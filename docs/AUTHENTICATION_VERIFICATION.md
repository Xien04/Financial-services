# Authentication verification — updated 2026-10-27

Scope: the authorized authentication implementation under ADRs 0006–0007.
The code includes identity/workspace models and migration, secure initial owner
provisioning, session authentication, password change/recovery/reset, persistent
rate limits, internal workspace policies, and the corresponding browser screens.
This record does not accept a production deployment or close Milestone 1.

## Verified locally — 2026-10-22

| Check | Result |
|---|---|
| Django system checks with isolated test settings | Passed |
| Backend unit/contract tests | 37 passed without database access |
| Ruff lint and formatting | Passed |
| Backend mypy | Passed for 46 files |
| Identity migration generation and model drift | Identity and membership-audit migrations generated; `makemigrations --check --dry-run` reports no changes |
| Frontend component/transport tests | 15 passed |
| Frontend ESLint and TypeScript | Passed |
| Next.js optimized production build | Passed; authentication routes render dynamically with per-request CSP nonces |
| Running frontend HTTP smoke tests | 2 passed without skips, including same-origin health forwarding and CSP nonce/HTML agreement |
| Browser preview | Sign-in and recovery navigation render; reset fragment is removed from the address; no observed browser errors |
| Mobile and keyboard spot checks | 375px viewport has no horizontal overflow; Tab moves from email to password |
| Working-tree secret scan | 0 potential secrets; no baseline/exclusion added |
| Dependency locks | No dependency or lockfile changes; uv locked offline export succeeded |

The browser/HTTP exercise used temporary loopback servers, the built frontend,
and the WSGI test API with isolated test settings. The preview enabled insecure
cookies only in its temporary local HTTP process. No real user, password, database,
SMTP message, or hosted deployment was created. Reset preview values were dummy
strings and no password change was submitted through the browser.

## Hosted CI and PR #10 follow-up — 2026-10-27

[PR #10's hosted run](https://github.com/Xien04/Financial-services/actions/runs/40542903189)
passed all three jobs for commit `b7f861b`: backend, frontend, and secrets.

| Check | Result |
|---|---|
| PostgreSQL 17 migrations and model drift | Passed against the disposable CI database |
| Full backend suite | 55 passed, including identity/session, workspace authorization, reset reuse, and concurrency tests |
| Backend lint, formatting, mypy, and Django system checks | Passed |
| Frontend component/transport tests | 15 passed |
| Frontend lint, TypeScript, optimized build, and HTTP smoke checks | Passed |
| Python and npm dependency audits | Passed |
| Working-tree secret scan | Passed |

The original authentication run failed one reset test: login persisted
`last_login` through a separate user instance, but the test generated a reset
token from its stale fixture. Django includes `last_login` in the token hash, so
the endpoint correctly rejected it. The test helper now reloads the user before
generating a token, and the scenario asserts that login succeeds first. The
reset, single-use, session-revocation, and no-automatic-login assertions remain
intact. Production authentication behavior and dependency locks are unchanged.

Local checks rerun on 2026-10-27 also passed: 37 backend unit/contract tests,
15 frontend component/transport tests, backend lint/formatting/mypy, Django
system checks, frontend lint/TypeScript, and the working-tree secret scan.
PostgreSQL evidence comes from hosted CI, not a local database or SQLite.

## Unverified or blocked

- **Local PostgreSQL and full Compose startup:** no local PostgreSQL service or
  Docker is available. Hosted migration/integration results above do not verify
  local container builds, initialization role grants, or the full Compose stack.
- **Actual email delivery:** SMTP is operator-configured and was not exercised.
  CI verifies email content and sanitized delivery failures through the in-memory
  test backend; that does not prove SMTP delivery.
- **Full browser authentication:** component and browser preview checks do not
  replace authenticated end-to-end tests, full keyboard/
  screen-reader checks, actual email recovery, or production proxy/TLS/IP tests.
- **Production operations:** trusted client-address handling, production serving,
  TLS termination, scheduled cleanup, and backup/restore verification still need
  the relevant deployment work. Compose remains local-development only.

## Completion tasks

- [x] Run the migration/check/full-suite commands in [TESTING.md](TESTING.md)
  against disposable PostgreSQL 17, including all identity concurrency tests
  (hosted CI, 2026-10-27).
- [ ] Verify a first owner can sign in, change their password, and recover through
  configured SMTP in the actual browser, with other sessions invalidated.
- [ ] Verify the production edge preserves host/origin, secure cookies, CSRF, CSP,
  and trustworthy client-IP signals; configure daily session/limiter cleanup.
- [x] Run both dependency audits with advisory-service access and observe CI
  (hosted CI, 2026-10-27).

The roadmap authentication/workspace delivery checkboxes remain open until these
acceptance checks pass. No default owner credentials or public registration exist.
