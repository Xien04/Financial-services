# Authentication verification — 2026-10-22

Scope: the authorized authentication implementation under ADRs 0006–0007.
The code includes identity/workspace models and migration, secure initial owner
provisioning, session authentication, password change/recovery/reset, persistent
rate limits, internal workspace policies, and the corresponding browser screens.
This record does not accept a production deployment or close Milestone 1.

## Verified locally

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

## Unverified or blocked

- **PostgreSQL integration and clean migrations:** attempted the full backend
  suite; test-database creation failed because no PostgreSQL service is reachable.
  No persistence, login-success, session-revocation, or concurrency acceptance
  result is claimed. Migration generation is not migration execution.
- **Integration scenarios ready to run:** `tests.integration.test_identity`
  includes session/CSRF rotation, server logout, secure session cookies,
  deactivation, live membership changes, idle/absolute limits, password-change
  revocation, reset expiry/reuse, generic recovery, email uniqueness, rate limits,
  workspace role checks and final-owner protection. Transaction tests cover
  concurrent resets, rate-limit races, and initial-owner provisioning/rollback.
- **Actual email delivery:** SMTP is operator-configured and was not exercised.
  The email-content and sanitized-delivery-failure assertions require the
  PostgreSQL integration suite; they have been added but have not passed locally.
- **Dependency audits:** npm's advisory endpoint and Python's vulnerability
  service could not be reached from the restricted environment. The uv export
  succeeded, but neither fresh audit is reported as passing. Dependencies are
  unchanged from the earlier tested locks.
- **Hosted CI and full browser authentication:** the existing CI workflow will
  discover the new PostgreSQL tests; no hosted run has been observed. Browser
  preview checks do not replace authenticated end-to-end tests, full keyboard/
  screen-reader checks, actual email recovery, or production proxy/TLS/IP tests.
- **Production operations:** trusted client-address handling, production serving,
  TLS termination, scheduled cleanup, and backup/restore verification still need
  the relevant deployment work. Compose remains local-development only.

## Completion tasks

- [ ] Supply disposable PostgreSQL 17 through `TEST_DATABASE_URL` and run the
  migration/check/full-suite commands in [TESTING.md](TESTING.md), including all
  identity concurrency tests. Fix any failure before enabling authentication.
- [ ] Verify a first owner can sign in, change their password, and recover through
  configured SMTP in the actual browser, with other sessions invalidated.
- [ ] Verify the production edge preserves host/origin, secure cookies, CSRF, CSP,
  and trustworthy client-IP signals; configure daily session/limiter cleanup.
- [ ] Run both dependency audits with advisory-service access and observe CI.

The roadmap authentication/workspace delivery checkboxes remain open until these
acceptance checks pass. No default owner credentials or public registration exist.
