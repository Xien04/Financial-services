# Scaffold verification — 2026-10-22

Scope: the initial Milestone 1 scaffold under ADRs 0001–0004. This is not
acceptance of the complete application foundation or a production deployment.
The subsequent automated-testing task is recorded separately in
[testing verification](TESTING_VERIFICATION.md), including the new type checks,
component tests, and working-tree secret scan. Statements below describe the
initial scaffold snapshot rather than superseding that later evidence.

## Verified locally

| Check | Result |
|---|---|
| uv locked sync and lock consistency | Passed using downloaded packages |
| npm clean install from the final lockfile | Passed; no audit findings |
| Ruff lint and formatting | Passed |
| Django system checks | Passed |
| Backend contract tests | 8 passed; no database access |
| Frontend ESLint | Passed |
| Frontend TypeScript | Passed |
| Next.js production build | Passed |
| Served frontend and same-origin API startup tests | 2 passed |
| Real HTTP readiness with unavailable database | Sanitized HTTP 503 |
| Python production and development dependency audit | No known vulnerabilities |
| npm dependency audit | No known vulnerabilities |
| Compose and workflow YAML parsing | Passed |
| Configuration assertions | Private database, loopback ports, pinned Actions |
| PostgreSQL initialization script shell syntax | Passed |

The local API HTTP exercise used Python's WSGI test server to exercise Django's
real request handling without a database. Django's normal development server
checks migrations at startup and therefore still requires reachable PostgreSQL.
No database correctness or migration evidence is claimed by those HTTP checks.

The Next.js ESLint preset was removed after its transitive `braces` dependency
failed the audit with no compatible fixed release. The scaffold uses the
JavaScript and TypeScript ESLint recommended configurations; both linting and
the full dependency audit pass with that configuration.

## Still required

Docker and PostgreSQL are unavailable on the current machine. Consequently,
container image builds, full Compose startup, the real database readiness test,
clean-database migrations, and the database initialization role grants have not
been exercised. The workflow defines PostgreSQL integration checks, but its first
hosted run has not occurred. A successful restore drill remains separate work.

Complete the README startup procedure on a Docker-equipped machine and record
those results before marking scaffold delivery complete. The initial configuration
does not add identity or financial models; UUID identity/authentication must be
established before auth migrations are added. Milestone 1 roadmap boxes remain
open. Automated secret scanning and full backend type/workflow checks remain
explicit follow-up work; manual review is not a substitute for those gates.
