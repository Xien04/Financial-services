# Financial Services Delivery Roadmap

This document tracks delivery. Update a checkbox only when its acceptance criteria are met, and record intentionally postponed scope under **Deferred work** instead of leaving its status ambiguous.

Status legend: `[x]` complete, `[ ]` not complete. The milestone named **Current** is the active planning focus. Application foundation is in progress; incomplete checks and milestone gates remain open.

## Milestone 0 — Product and accounting definitions (Complete)

**Outcome:** the team shares one testable vocabulary for financial behavior before code or schema hardens assumptions.

### Features and tasks

- [x] Establish product goals, scope, phased feature matrix, and architecture blueprint.
- [x] Establish the staged roadmap and ADR convention.
- [x] Document the initial secret-handling policy and configuration variable names.
- [x] Define debit/credit and UI sign conventions for every account type.
- [x] Define opening balance, refund, transfer, credit-card payment, void, and adjustment examples.
- [x] Define transaction lifecycle and allowed state transitions.
- [x] Define financial date, timezone, month-boundary, rounding, and currency-precision rules.
- [x] Define net worth, cash flow, burn rate, savings rate, and budget-actual formulas as executable examples.
- [x] Produce wireframes for transaction entry, import preview, reconciliation, and dashboard.
- [x] Write the first ADRs when implementation decisions are accepted.

### Dependencies

None.

### Acceptance criteria

- Every financial operation above has inputs, expected ledger entries, balances, and report effects.
- Ambiguous sign, date, rounding, and lifecycle behavior is resolved in writing.
- MVP boundaries and success criteria are accepted before Stage 1 scaffolding.

Accepted and closed by Brenson Go on 2026-09-18.

## Milestone 1 — Application foundation (Current)

**Outcome:** a secure, testable Django/Next.js development environment runs locally and in CI.

### Features and tasks

- [x] Record ADRs for the modular monolith, ledger-entry model, and PostgreSQL.
- [x] Scaffold Django, Django REST Framework, Next.js, and TypeScript projects.
- [x] Lock production and development dependencies; add automated dependency scanning.
- [x] Add PostgreSQL migrations, UUID conventions, and environment-specific settings.
- [ ] Implement email/password authentication and password reset.
- [ ] Implement workspaces, membership roles, and reusable authorization policies.
- [x] Establish versioned API, OpenAPI generation, validation, errors, request IDs, and idempotency conventions.
- [x] Add formatting, linting, unit-test, integration-test, and type-check commands.
- [ ] Add CI, Docker Compose, health endpoints, structured redacted logs, backups, and a restore runbook.
- [ ] Add secret scanning and verify no credentials exist in the current tree or published history.

Authentication and initial identity/workspace code is implemented under ADRs
0006–0007. PostgreSQL migrations and integration/concurrency tests pass in hosted
CI. The related delivery checkboxes remain open pending actual mail delivery,
complete browser workflows, and production proxy verification. See
[setup](AUTHENTICATION.md) and
[verification](AUTHENTICATION_VERIFICATION.md). No financial workflow is added.

Issue #11's full Compose verification passed in hosted Linux CI on 2026-10-27:
fresh image builds/startup, application-role migrations and permissions, runtime
users/ports, database-outage health checks, and identity persistence after restart.
See [Compose verification](COMPOSE_VERIFICATION.md) for the exact environment and
evidence. Browser/SMTP, structured logs, production
operations, backup/restore, and historical secret verification remain open.

Brenson Go accepted issue #12's API and idempotency decisions on 2026-10-27 in
[ADR 0008](adr/0008-standardize-api-contracts.md) and
[ADR 0009](adr/0009-make-financial-writes-idempotent.md), explicitly confirming:
"Both documents are accepted." Merged PR #21 records that acceptance and closed
#12. Issue #14 implements applicable current API conventions, including the
OpenAPI tooling compatibility check. Its PR #24 passed all four hosted jobs on
2026-10-28: 80 backend tests, 20 frontend tests, both HTTP smoke tests, full Compose,
schema drift, lint/types/build, dependency audits, and working-tree scanning. See
[API contracts](API_CONTRACT.md) and [verification](API_VERIFICATION.md). No current
authentication/health route needs pagination or financial idempotency. The API
conventions checkbox is complete; actual financial posting/retry enforcement
remains a Milestone 2 responsibility. #15 implements structured logging against
the established request-ID context. Milestone 1 remains open.

The product owner requested issue #13's policy decisions before further feature
implementation. Brenson Go accepted the retention/closure policy in
[ADR 0010](adr/0010-define-data-retention-and-deletion.md) and backup/recovery
policy in [ADR 0011](adr/0011-define-backup-and-recovery-targets.md) on 2026-10-28,
explicitly confirming: "both files are accepted." The policy PR records these
decisions and closes #13 when merged. #18 then implements the backup/restore
procedure and measured drill, including the one-hour RPO/four-hour RTO targets.
No retention job, deletion workflow, backup, or achieved recovery target is
claimed by policy acceptance. Milestone 1 completion checkboxes remain open.

### Dependencies

- Milestone 0 financial conventions accepted.
- Local and CI deployment targets selected.

### Acceptance criteria

- A new contributor can configure and start the stack from the README.
- CI performs formatting/lint, type checks, backend tests, frontend tests, dependency scanning, and secret scanning.
- Users cannot access a workspace without the required membership and role.
- A clean database migrates successfully; backup and restore succeed in a documented drill.
- No secret is stored in source, image layers, logs, fixtures, or CI output.

## Milestone 2 — Ledger engine

**Outcome:** financial balances and classifications are correct under all MVP transaction forms.

### Features and tasks

- [ ] Implement accounts, categories, tags, transactions, and ledger entries.
- [ ] Implement opening balances, income, expenses, transfers, splits, refunds, adjustments, and credit-card payments.
- [ ] Enforce atomic posting, balanced allocations, workspace currency, and idempotency invariants.
- [ ] Implement calculated balances and paginated account ledgers.
- [ ] Implement statement reconciliation and balance snapshots.
- [ ] Add audit events and archive/void behavior for material changes.
- [ ] Add unit, integration, and property-based tests for monetary rules.

### Dependencies

- Milestone 1 database, identity, workspace, API, and test infrastructure.
- Milestone 0 executable accounting examples.

### Acceptance criteria

- All accepted accounting examples pass against the domain service and API.
- Transfers never appear as income or expense.
- Split allocations cannot post unless they balance exactly under decimal and rounding rules.
- Retrying a transaction creation request does not create another posting.
- Reconciled balances match representative statements, and unauthorized cross-workspace access fails.

## Milestone 3 — Transaction experience

**Outcome:** a user can efficiently manage and reconcile accounts from desktop or mobile layouts.

### Features and tasks

- [ ] Build account list/detail and transaction list/detail screens.
- [ ] Build keyboard-friendly manual entry for income, expense, transfer, and split transactions.
- [ ] Add filters, search, sorting, pagination, editing, and bulk categorization.
- [ ] Build the guided reconciliation experience.
- [ ] Add responsive, accessible loading, empty, error, and confirmation states.

### Dependencies

- Milestone 2 ledger and reconciliation APIs.
- Milestone 0 approved interaction wireframes.

### Acceptance criteria

- A user can complete every manual-entry success scenario without direct admin/database access.
- Filters and totals agree with the underlying ledger across a high-volume fixture.
- Reconciliation clearly identifies the difference and records an auditable completion.
- Core workflows meet the agreed keyboard, screen-reader, and responsive-layout checks.

## Milestone 4 — CSV imports

**Outcome:** users can import representative bank exports safely, reviewably, and without duplication.

### Features and tasks

- [ ] Add constrained upload and file metadata hashing.
- [ ] Add delimiter/encoding/header inspection and column mapping.
- [ ] Add normalization, validation, staging rows, and preserved source values.
- [ ] Add exact/probable duplicate detection and review controls.
- [ ] Add preview, selective confirmation, batch posting, completion reporting, and reversible batches.
- [ ] Add saved institution/file-signature mapping profiles where repeated samples justify them.
- [ ] Build sanitized fixtures for representative institution export formats.

### Dependencies

- Milestone 2 posting/idempotency services.
- Milestone 3 account and transaction interfaces.
- Object-storage choice and upload security controls from Milestone 1.

### Acceptance criteria

- Malformed rows cannot partially corrupt a ledger or obscure valid rows.
- Re-uploading or retrying an identical confirmed batch does not duplicate transactions.
- Probable duplicates require a visible user disposition; stable-ID exact matches are suppressed and reported.
- An import can be reversed without deleting its audit evidence.
- Representative CSV fixtures pass encoding, date, decimal, debit/credit, and duplicate cases.

## Milestone 5 — Dashboard, reports, and export

**Outcome:** users see explainable financial totals and can take all of their data with them.

### Features and tasks

- [ ] Implement net worth, cash flow, burn rate, savings rate, and category spending APIs.
- [ ] Build summary cards and accessible visualizations with date and account controls.
- [ ] Add drill-down from each aggregate to the underlying transactions.
- [ ] Add monthly summary reporting and complete JSON/CSV export.
- [ ] Measure report queries and add targeted indexes or aggregates only where justified.

### Dependencies

- Trusted ledger from Milestone 2.
- Transaction navigation from Milestone 3.
- Metric definitions from Milestone 0.

### Acceptance criteria

- Dashboard values match executable metric examples and direct ledger queries.
- Transfers are excluded from cash flow, burn rate, savings rate, and category spending.
- Every total exposes its range, currency, and inclusion rules and supports drill-down.
- Export contains all user-owned financial data in documented, portable formats.

## Milestone 6 — Budgets and recurring planning

**Outcome:** users can plan monthly spending and track expected bills, subscriptions, income, and transfers.

### Features and tasks

- [ ] Add monthly category budgets, actuals, rollover, and optional rollover caps.
- [ ] Add recurring items with amount tolerances and expected dates.
- [ ] Add subscription calendar and expected-versus-actual views.
- [ ] Add in-app budget and upcoming-payment alerts.

### Dependencies

- Ledger allocations from Milestone 2.
- Dashboard/reporting date and aggregate conventions from Milestone 5.

### Acceptance criteria

- Posted eligible allocations drive budget actuals; transfers do not.
- Rollover results match boundary examples for positive, negative, capped, and disabled cases.
- Recurring items never autopost without explicit opt-in; MVP keeps autopost off by default.
- Alerts are deduplicated and link to their supporting item or transaction view.

## Milestone 7 — Goals and manual wealth tracking

**Outcome:** users can track savings/debt goals and manually valued assets or investments.

### Features and tasks

- [ ] Add financial goals and links to one or more accounts.
- [ ] Add manual balance snapshots for investments, property, and other assets.
- [ ] Add deterministic progress and required-monthly-contribution calculations.
- [ ] Display assumptions and account allocation behavior in the interface.

### Dependencies

- Accounts and snapshots from Milestone 2.
- Dashboard/reporting infrastructure from Milestone 5.

### Acceptance criteria

- Snapshot history changes valuation charts without inventing income or expense transactions.
- Goal progress handles shared accounts and allocations without double-counting.
- Projection results show their calculation date, assumptions, and impossible/overdue states.

## Milestone 8 — Hardening and MVP release

**Outcome:** the MVP is secure, recoverable, operable, accessible, and documented for self-hosting.

### Features and tasks

- [ ] Complete threat modeling and an application security review.
- [ ] Complete accessibility and supported-device/browser testing.
- [ ] Add onboarding, guided CSV import, useful empty states, and optional demo data.
- [ ] Validate full export, account deletion, retention, backup, and restore procedures.
- [ ] Profile high-volume ledgers/imports and add targeted indexes.
- [ ] Publish deployment, upgrade, rollback, monitoring, and incident runbooks.
- [ ] Exercise clean install, migration, rollback, backup restore, and secret rotation.

### Dependencies

- Milestones 1–7 complete.
- Supported deployment environments and release policy defined.

### Acceptance criteria

- All eight MVP user success criteria in the product architecture pass end to end.
- High-severity security findings are resolved and lower-severity risks are explicitly accepted or scheduled.
- A fresh operator can deploy, monitor, back up, restore, upgrade, and roll back using the documentation.
- Tested accessibility, performance, recovery, and data-portability thresholds are met.

## Post-MVP milestones

### V2 candidates

- [ ] Shared households, invitations, and refined permissions
- [ ] MFA, passkeys, and OAuth
- [ ] Provider-neutral bank-feed adapter and first provider
- [ ] Categorization and recurring-pattern rules
- [ ] Investment holdings, cost basis, and price history
- [ ] Multi-currency reporting
- [ ] Email or push notifications
- [ ] PDF reports and date comparisons

### V3 candidates

- [ ] Forecasting and scenario planning
- [ ] Debt payoff optimization
- [ ] Retirement modeling
- [ ] Automated anomaly detection and explanations
- [ ] Tax lots and investment analytics
- [ ] Optional AI assistance with explicit privacy controls
- [ ] SSO, delegated/advisor access, and configurable automation

## Completed work

- 2026-10-28: Implemented issue #14's current API contracts under ADRs 0008–0009: strict JSON/field validation, safe errors, fresh request IDs, frontend field/reference handling, generated OpenAPI, and a CI drift gate. All hosted quality jobs passed, including 80 backend tests and full Compose; see [API verification](API_VERIFICATION.md). Financial posting/idempotency and real collection pagination remain with their owning workflows.
- 2026-10-27: Completed issue #11's Compose verification in GitHub Actions and corrected the API image PATH so documented `python manage.py` commands use its installed virtualenv. The full Compose job and all existing quality/security jobs passed, including 62 backend tests. See [Compose verification](COMPOSE_VERIFICATION.md). This does not close the remaining Milestone 1 gates.
- 2026-10-27: Fixed PR #10's stale-user password-reset test setup. Hosted CI passed PostgreSQL migrations, all 55 backend tests, 15 frontend tests, lint/type/build/HTTP checks, both dependency audits, and working-tree secret scanning. See [authentication verification](AUTHENTICATION_VERIFICATION.md); actual SMTP/browser workflows, local Compose, and production operations remain open.
- 2026-10-22: Implemented authentication, UUID identity/workspace schemas, initial owner provisioning, workspace policies, and rate limiting under ADRs 0006–0007. Brenson Go accepted ADR 0006 covering browser sessions, recovery lifetimes, and role permissions. Verification status is recorded in [authentication verification](AUTHENTICATION_VERIFICATION.md).
- 2026-10-22: Implemented isolated Django test settings, backend type checking, frontend component tests, fail-on-missing-target HTTP smoke checks, working-tree secret scanning, and their CI commands under ADR 0005. See the historical [testing verification](TESTING_VERIFICATION.md) and the 2026-10-27 hosted evidence above; broad milestone gates stay open.

- 2026-09-18: Brenson Go accepted the MVP boundaries and success criteria and closed Milestone 0. Milestone 1 is now current.
- 2026-09-18: Brenson Go accepted ADRs 0001–0003 (Django modular monolith and repository layout, balanced ledger-entry model, PostgreSQL).
- 2026-08-18: Drafted ADRs 0001–0003 covering the Django modular monolith and repository layout, balanced ledger-entry model, and PostgreSQL; product-owner acceptance followed on 2026-09-18 (see above).
- 2026-08-18: Brenson Go accepted responsive product wireframes version 1.0 for transaction entry, CSV import, account reconciliation, and dashboard workflows.
- 2026-08-18: Brenson Go accepted `docs/FINANCIAL_SEMANTICS.md` version 1.0, including Philippine-peso rules, ledger signs, canonical postings, lifecycle, per-entry reconciliation, date/rounding rules, metric formulas, and budget behavior.
- 2026-08-18: Created the concise repository README, comprehensive product architecture, actionable delivery roadmap, ADR convention, environment-variable template, and dependency placeholder.
- 2026-08-18: Added preventive ignore rules for local environment files, credential directories, and common service-account JSON filenames.
- 2026-08-18: Verified `Credentials/Credential-financeapp.json` does not appear in the current repository tree or reachable Git history.

## Deferred work

- Automated-testing follow-up: review historical secrets separately from working-tree scanning and add full browser and accounting/property tests with their owning workflows. Identity/tenant integration tests now pass in hosted PostgreSQL CI. See [testing guide](TESTING.md).

- The initial scaffold uses ADR 0004 tooling and committed uv/npm locks. Hosted PostgreSQL and full Compose verification now pass, including initialization grants, application-role migrations, runtime boundaries, and persistence. The Windows host remains without Docker; the recorded full-stack evidence is from Linux CI. Remaining Milestone 1 checkboxes stay open pending their full criteria.
- Actual SMTP/browser authentication, production-edge verification, historical secret review, structured logging, production serving, and backup/restore drills remain Milestone 1 work. Rate-limit thresholds and implementation are recorded in ADR 0007. Current API/OpenAPI contracts are implemented under ADRs 0008–0009; actual financial posting enforcement and signed pagination for real collections remain with their owning workflows.
- Architecture choices not covered by an accepted ADR (for example Celery and Redis, and object storage) remain recommendations in the architecture document until their own ADRs are accepted.
- Bank feeds, brokerage accounting, real-time pricing, advanced multi-currency accounting, tax preparation, money movement, credit monitoring, and AI-generated advice are outside MVP.
