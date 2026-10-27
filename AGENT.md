# Repository Instructions for AI Agents and Contributors

## Purpose and authority

This file is the operational entry point for work in this repository. It translates the repository's current documentation into execution rules; it does not replace the source documents or turn an undecided recommendation into an accepted architecture decision.

Read these sources before proposing or changing code:

1. `docs/adr/*.md` for accepted architecture decisions.
2. `docs/FINANCIAL_SEMANTICS.md` for accepted accounting conventions and executable examples.
3. `docs/PRODUCT_WIREFRAMES.md` and `docs/wireframes/*.md` for accepted core workflow behavior.
4. `docs/PRODUCT_ARCHITECTURE.md` for product boundaries, domain invariants, and the planned architecture.
5. `docs/ROADMAP.md` for sequencing, dependencies, acceptance criteria, and current delivery status.
6. `README.md`, `.env.example`, `pyproject.toml`, `uv.lock`, frontend manifests, and `.gitignore` for repository state and setup constraints.

If the sources conflict, an accepted ADR governs the technical decision it addresses. Otherwise, preserve the product invariants and MVP boundaries in `docs/PRODUCT_ARCHITECTURE.md`, then follow the milestone gates in `docs/ROADMAP.md`. Do not resolve a material conflict silently: document it and add or supersede an ADR.

Normative words in this file have their ordinary standards meaning: **MUST** and **MUST NOT** are mandatory; **SHOULD** requires a documented reason to deviate; **MAY** is optional.

## Decision status: do not overstate it

The repository is in **Milestone 1 (application foundation)**. Milestone 0 was accepted and closed on 2026-09-18. A Django/DRF and Next.js scaffold, PostgreSQL Compose configuration, and checks exist. Authentication, UUID identity/workspace schemas, initial owner provisioning, and internal workspace policies are implemented. PostgreSQL migrations/integration tests and the complete Compose setup pass in hosted Linux CI; Docker remains unavailable on the Windows host. Browser/SMTP verification, shared API implementation, structured logs, production operations, backup/restore, and historical secret verification remain open. Ledger schemas and financial workflows remain unimplemented. See the roadmap, `docs/AUTHENTICATION_VERIFICATION.md`, and `docs/COMPOSE_VERIFICATION.md`; implementation does not complete Milestone 1.

ADRs 0001–0003 were accepted by the product owner on 2026-09-18: the Django modular monolith (including the Next.js client, module ownership, and physical repository layout), the balanced ledger-entry model, and PostgreSQL. Financial semantics and product wireframes version 1.0 are also accepted. ADR 0004 records the 2026-10-22 scaffold tooling decision, including uv selected by the product owner. ADR 0005 records the automated quality-check tooling implemented in the authorized testing task. ADR 0006 was accepted by Brenson Go on 2026-10-22 and governs Django/PostgreSQL browser sessions, authentication lifecycle, initial owner provisioning, and workspace role permissions. ADR 0007 records the implementation's PostgreSQL rate limiter, thresholds, and browser protections.

Brenson Go accepted ADRs [0008](docs/adr/0008-standardize-api-contracts.md) and [0009](docs/adr/0009-make-financial-writes-idempotent.md) on 2026-10-27. They govern shared validation/errors, server-generated request IDs, implementation-generated OpenAPI, cursor pagination, and durable financial idempotency. Issue #14 implements applicable current API contracts, including the schema-tool compatibility gate. Real financial posting enforcement and concurrency evidence remain Milestone 2 work; acceptance does not claim implementation is complete.

Consequently:

- The modular monolith, ledger-entry model, and PostgreSQL are binding. Changing any of them requires a superseding ADR.
- Choices in `docs/PRODUCT_ARCHITECTURE.md` not covered by an accepted ADR (for example Celery and Redis, and object storage) remain recommendations until their own ADRs are accepted. Authentication/session strategy and role permissions follow [ADR 0006](docs/adr/0006-use-django-sessions-for-browser-authentication.md); API and financial retry contracts follow ADRs 0008–0009. MUST NOT describe unresolved choices as accepted.
- MUST NOT silently replace the planned stack or architecture with alternatives.
- MUST add an ADR before making a material technical decision that the accepted ADRs do not already cover.
- MUST implement debit/credit and UI signs, lifecycle transitions, financial dates, month boundaries, rounding, currency precision, and executable metric formulas according to the accepted `docs/FINANCIAL_SEMANTICS.md`. Do not change them implicitly in code or an unrelated ADR.
- MUST treat the Milestone 0 definitions, MVP boundaries, and success criteria as accepted inputs. Changing them requires an explicit, recorded revision, not an implicit code or roadmap change.
- MUST update a roadmap checkbox only after its stated acceptance criteria are met. Intentionally postponed work belongs under `Deferred work`.

## Product and compliance boundaries

Financial Services is a privacy-first, self-hostable personal-finance application. It tracks and explains financial information; it does not move money and does not provide regulated or AI-generated financial advice.

MVP work MUST remain within the documented feature matrix and implementation sequence. The following are explicitly outside MVP:

- brokerage trade accounting and tax-lot calculations;
- real-time market pricing;
- automated tax preparation;
- complex multi-currency gain/loss accounting;
- money movement or bill payment;
- credit-score monitoring; and
- AI-generated financial advice.

Live bank synchronization is also deferred until reconciliation, idempotency, and duplicate handling are demonstrably reliable. Do not let later dashboard, budget, import, goal, bank-feed, or investment work bypass or precede the trustworthy ledger foundation on which it depends.

## Planned technical direction

Until accepted or changed by ADR, preserve this documented implementation direction:

- **Client:** responsive Next.js, React, and TypeScript web application using TanStack Query, React Hook Form, Zod, and a charting library. Recharts is an example, not a selected requirement.
- **API and financial engine:** Django plus Django REST Framework in a modular monolith.
- **Database:** PostgreSQL.
- **Background jobs:** Celery with Redis.
- **File storage:** local filesystem for basic self-hosting, with an S3-compatible backend as an option.
- **Deployment:** Docker Compose first. Managed containers or Kubernetes are future options only when measured scale or operational needs justify them.
- **Transport:** versioned REST/JSON over HTTPS, with implementation-generated OpenAPI documentation.
- **Observability:** structured redacted logs, health endpoints, error tracking, metrics, request/job correlation, and audit records.

Do not introduce microservices, another database, another primary web/API framework, or provider-specific logic in the financial domain without an accepted ADR. Keep modules within one application boundary unless independent scaling or operation has measured value.

## Architecture and ownership rules

The modular monolith has these logical owners:

| Module | Owns |
|---|---|
| Identity and workspaces | Users, memberships, roles, tenant authorization |
| Ledger and accounts | Accounts, transactions, immutable posted entries, categories, tags, balances, reconciliation |
| Imports | Uploads, mappings, normalized staging rows, duplicate review, and posting orchestration |
| Planning | Budgets, recurring items, subscriptions, and goals |
| Reporting | Net worth, cash flow, burn rate, savings rate, and exports |
| Integrations | Provider-neutral bank-feed and object-storage adapters |

Every module MUST own its domain behavior and hide its persistence details behind service interfaces. Cross-module writes MUST go through application services and explicit database transactions. API handlers, serializers, UI components, background tasks, reports, and provider adapters MUST NOT reimplement ledger rules or write around the owning service.

Provider-specific payloads MUST enter normalized staging data and pass through the same validation, deduplication, review, and posting services as CSV data. Provider adapters MUST remain outside the ledger domain.

Background tasks MUST receive identifiers rather than stale object snapshots, reload authoritative state, and be safe to retry. Polling, webhooks, import posting, and other retried operations MUST be idempotent.

## Repository and directory structure

The original physical layout (Stage 0, before scaffolding) was:

```text
/
├── AGENT.md
├── README.md
├── .env.example
├── .gitignore
├── requirements.txt
└── docs/
    ├── PRODUCT_ARCHITECTURE.md
    ├── FINANCIAL_SEMANTICS.md
    ├── PRODUCT_WIREFRAMES.md
    ├── ROADMAP.md
    ├── wireframes/
    │   ├── 01_TRANSACTION_ENTRY.md
    │   ├── 02_CSV_IMPORT.md
    │   ├── 03_RECONCILIATION.md
    │   └── 04_DASHBOARD.md
    └── adr/
        ├── README.md
        ├── 0001-use-django-modular-monolith.md
        ├── 0002-use-ledger-entry-model.md
        └── 0003-use-postgresql.md
```

The implemented Stage 1 layout follows [ADR 0001](docs/adr/0001-use-django-modular-monolith.md): `backend/` (Django project, `config/`, one package per owning module, `tests/integration` and `tests/contract`), `frontend/` (Next.js `src/app`, `src/features`, `src/lib`), `infra/`, and root `compose.yaml`. Follow it. [ADR 0004](docs/adr/0004-use-uv-and-foundation-tooling.md) records uv, npm, runtime versions, and initial tooling. Additional unresolved material decisions still require an ADR.

That layout makes the logical ownership above explicit and MUST enforce these placement rules:

- Financial calculations, sign conversion, posting, balance, reconciliation, and invariant enforcement belong to the ledger/accounts domain, not API views or UI code.
- Authentication, membership checks, and reusable tenant policies belong to identity/workspaces; every owning service and query still applies the workspace boundary.
- HTTP validation and representation belong at the API boundary; cross-module mutations delegate to application services.
- Database persistence stays encapsulated by its owning module; another module does not reach into those persistence details.
- Import parsing and normalized staging belong to imports; only the ledger posting service creates financial postings.
- Budget, recurring-item, subscription, and goal behavior belongs to planning and consumes posted ledger allocations through defined interfaces.
- Aggregation and export behavior belongs to reporting and remains explainable and drillable to ledger transactions.
- External provider and object-storage implementations belong behind integration adapters.
- React presentation and interaction logic stay in the client; the client MUST NOT become an alternate accounting engine.

## Ledger and monetary invariants

The user-facing model is a `Transaction`; balances derive from immutable, posted `LedgerEntry` records. These are mandatory correctness rules:

- A posted transaction MUST have at least one entry that affects an account.
- Entries for a posted transaction MUST sum to zero under the centrally documented ledger convention.
- A transfer MUST affect exactly two accounts and MUST NOT use an income or expense category.
- Transfers MUST NOT contribute to income, expense, cash-flow, burn-rate, savings-rate, category-spending, or budget-actual totals.
- Income and expense split allocations MUST exactly equal the corresponding account-side amount under the documented sign convention.
- A transaction and all of its entries MUST commit or fail atomically.
- Posted entries MUST NOT be edited in place. A correction creates a new version or an atomic, audited void-and-repost sequence.
- A user-facing delete of posted financial history MUST be an audited void/archive transition, never physical erasure.
- Retrying transaction creation or an import batch MUST NOT create a second posting.
- Idempotency keys are required for imports, transaction creation, and posting operations.
- MVP entries MUST use Philippine peso (`PHP`) as the workspace base currency. Multi-currency and foreign-exchange accounting remain deferred.
- Transaction posting status is `pending`, `posted`, or `void`; reconciliation MUST be linked per account-side ledger entry and MUST NOT be transaction-wide status.
- Opening balances and non-operating adjustments MUST use explicit system-equity entry roles, never fake income or expense categories.
- Every workspace MUST have visible, non-deletable uncategorized income and expense categories that remain included in operating reports.
- Asset balances add to net worth and liability balances subtract. Sign conversion belongs in the domain layer, never ad hoc in the client.
- Manual balance snapshots change valuation history without inventing income or expense transactions.
- Goal progress and account allocations MUST NOT double-count shared values.

### Numeric, date, and identifier rules

- MUST use exact decimal monetary arithmetic and PostgreSQL `NUMERIC(19,4)` or an accepted currency-aware decimal type. Never use binary floating point for money.
- MUST use UUID primary identifiers.
- MUST define rounding behavior and currency precision centrally before implementing calculations that depend on them.
- MUST store financial dates separately from event timestamps.
- MUST store timestamps in UTC and display them in the workspace timezone.
- MUST use the accepted financial-date, timezone-boundary, calendar-month, round-half-to-even, and sign behavior in `docs/FINANCIAL_SEMANTICS.md`.

The blueprint gives high-level metric definitions, and accepted `docs/FINANCIAL_SEMANTICS.md` defines their executable examples and boundary behavior, including zero-income savings rate and burn-rate boundaries. Those rules are mandatory inputs to domain and report tests.

## Tenant isolation and authorization

The workspace is both the tenant and authorization boundary.

- Every workspace-owned read and mutation MUST filter by a membership and role the current user may exercise.
- Workspace filtering MUST exist at both the service and query layers.
- Every request MUST enforce workspace-level and object-level authorization; possession of an object identifier is never authorization.
- Cross-workspace access MUST fail in service, API, and background-job paths and MUST have automated coverage.
- Membership roles are `owner`, `editor`, and `viewer`; `(workspace_id, user_id)` MUST be unique.

## API contract

- Follow accepted [ADR 0008](docs/adr/0008-standardize-api-contracts.md) for HTTP validation/errors, request IDs, OpenAPI, and pagination, and [ADR 0009](docs/adr/0009-make-financial-writes-idempotent.md) for financial operation identities, replay, concurrency, failure, and retention. These are binding decisions; implementation status remains in the roadmap.
- APIs MUST be versioned under `/api/v1` unless an accepted ADR changes the convention.
- OpenAPI documentation MUST be generated from the implementation and updated with contract changes.
- Use consistent error envelopes, request IDs, cursor pagination for large ledgers, and idempotency keys for posting operations.
- A transaction-creation request MUST describe and post the entire transaction atomically.
- Aggregate responses MUST expose date range, currency, and inclusion rules and allow drill-down to supporting transactions.
- Large ledger filters must support the documented dimensions: date range, account, category, tag, amount range, payee, status, source, and free text.

Do not add categorization-rule endpoints in MVP unless import testing demonstrates that they are necessary.

## Import rules

An uploaded row MUST never write directly to the ledger. Preserve this staged flow:

```text
upload -> inspect -> map -> normalize -> validate
       -> detect duplicates -> preview -> confirm -> post
```

- Enforce file-size and content-type limits and compute a SHA-256 content hash.
- Preserve source values and source-row numbers alongside normalized values and validation results.
- Normalize dates, decimal separators, debit/credit formats, whitespace, and payees before fingerprinting.
- Detect exact and probable duplicates before posting. Stable external IDs may suppress exact matches; probable duplicates require visible user review and disposition.
- Post accepted rows in bounded database transactions.
- Re-uploading or retrying an identical confirmed batch MUST NOT duplicate transactions.
- Reversal MUST use compensating or audited state changes and retain the import evidence.
- Parsing MUST be isolated and governed by upload and retention policies. Malformed rows MUST NOT partially corrupt the ledger or obscure valid rows.

## Security, privacy, and audit rules

- MUST NOT commit secrets, credentials, tokens, service-account JSON, database passwords, or encryption keys.
- `.env.example` documents names only. Real values belong in the process environment, deployment secret store, or ignored local `.env`/secret files.
- MUST NOT place environment-specific secrets in source, fixtures, image layers, logs, error reports, or CI output.
- Use framework-hardened password hashing; password-reset tokens MUST expire and be single-use.
- Require CSRF protection, appropriately scoped secure cookies, rate limiting, strict content security policy, TLS in production, and explicit allowed hosts/origins.
- Encrypt application secrets and provider tokens at rest with a dedicated, rotatable key. Never log credentials, raw tokens, full account numbers, or raw financial records.
- Record audit events for material financial changes, imports, account changes, reconciliation, membership changes, exports, and deletions without sensitive payloads.
- Archive or soft-delete financial records and avoid irreversible deletion.
- Use least-privilege credentials for database, storage, workers, integrations, and deployment.
- Lock dependency versions, scan dependencies and secrets in CI, and patch routinely.
- Provide full user-data export and account-deletion workflows with explicit retention behavior.

If a real credential is discovered, do not merely delete the file: stop exposure, rotate or revoke the credential, assess repository history and build caches, coordinate any required history cleanup, review access logs, and reduce the replacement credential to least privilege.

## Testing and quality gates

ADR 0004 selects Django's test runner, Ruff, ESLint, TypeScript checks, and dependency audits.
ADR 0005 extends that toolchain with mypy and Django/DRF stubs, Vitest and React
Testing Library component tests, isolated test settings, and working-tree secret
scanning. Use [docs/TESTING.md](docs/TESTING.md) for the current commands and
scope. Backend type checking and current-tree scanning are now implemented;
full browser workflow coverage and historical scanning remain outstanding.
Hosted PostgreSQL/CI checks passed on 2026-10-27; see
`docs/AUTHENTICATION_VERIFICATION.md`. No numeric coverage target or strict Python
type-hint policy is selected. Never claim a missing or unrun gate passes.

Once commands exist, every change MUST run all relevant checks. In addition:

- Every monetary calculation and sign convention requires unit tests.
- Splits, transfers, and ledger invariants require property-based tests.
- Domain services and their API contracts require integration coverage against accepted accounting examples.
- Opening balances, income, expenses, refunds, transfers, credit-card payments, splits, voids, adjustments, reconciliation, rounding boundaries, and retry behavior require explicit examples.
- Authorization tests MUST prove unauthorized cross-workspace access fails.
- Import fixtures MUST cover encoding, date, decimal, debit/credit, malformed-row, and duplicate cases without real sensitive data.
- Report tests MUST compare aggregates with executable metric examples and direct ledger queries.
- Budget rollover tests MUST cover positive, negative, capped, and disabled cases.
- Frontend core flows MUST cover agreed keyboard, screen-reader, responsive, loading, empty, error, and confirmation behavior.
- Backup success alone is insufficient: documented restore drills MUST pass.
- Capacity tests MUST cover large ledgers and imports before release; add indexes or aggregates only in response to measured queries.

A test that only mirrors implementation logic is not evidence of financial correctness. Expected ledger entries, balances, report effects, and authorization outcomes must come from accepted examples and invariants.

## Deployment and operations

The planned Docker Compose topology has separately configurable web, API, Celery worker, PostgreSQL, Redis, and optional S3-compatible storage containers. Add a scheduler only when scheduled jobs exist.

- Expose only the web/API edge. PostgreSQL and Redis stay on an authenticated private network.
- Configuration enters through environment variables or mounted secrets.
- Separate liveness from dependency-readiness checks.
- Run migrations as a controlled release step, not concurrently from every web process.
- Maintain rollback support and backward-compatible migrations throughout the rollout window.
- Document backup and restore paths for persistent database and object-storage volumes.
- Correlate structured, redacted logs by request or job ID.
- Exercise clean install, migration, rollback, backup restore, and secret rotation before MVP release.

## Dependency policy

Root `pyproject.toml` and `uv.lock` own Python dependencies under ADR 0004; do not restore a parallel requirements manifest. MUST NOT add speculative or unpinned runtime dependencies before application code imports them. Pin exact direct production and development versions, commit transitive locks, and keep automated dependency scanning current.

Apply the same evidence-based, locked-dependency policy to the frontend and other runtime manifests when they are created. A new dependency needs a concrete use, fit with the planned stack and deployment model, and inclusion in the appropriate lock/scanning workflow.

## Required workflow for every change

### 1. Establish context before proposing work

- [ ] Read this file and the source documents relevant to the requested area.
- [ ] Inspect `docs/adr/` for accepted, superseded, or proposed decisions; do not rely on filename examples as actual ADRs.
- [ ] Check the current milestone, its dependencies, incomplete prerequisites, and acceptance criteria in `docs/ROADMAP.md`.
- [ ] Inspect the existing tree, configuration, tests, and working-tree state; preserve unrelated work.
- [ ] Classify the request as MVP, V2/V3, or explicitly excluded scope.
- [ ] Identify unresolved conventions, not covered by accepted documents or ADRs, that the change would otherwise guess.

### 2. Design within the boundaries

- [ ] Assign each behavior and persistence concern to its owning module.
- [ ] Route cross-module mutations through services and explicit transactions.
- [ ] State affected ledger, tenant, idempotency, privacy, audit, and recovery invariants.
- [ ] For a material new or changed technical decision, add an ADR with a sequential zero-padded filename and record status, context, decision, consequences, and date.
- [ ] If a necessary convention is unresolved, document accepted examples or obtain the decision before implementation.

### 3. Implement the smallest complete change

- [ ] Keep financial rules in the domain layer and presentation/transport concerns at their boundaries.
- [ ] Use exact decimals, UUIDs, atomic transactions, idempotency, workspace scoping, immutable posting, and audit-safe state changes where applicable.
- [ ] Preserve import provenance and avoid provider-specific leakage into the ledger.
- [ ] Add no speculative dependencies, features, directories, services, or abstractions.
- [ ] Keep logs, fixtures, errors, screenshots, and generated artifacts free of secrets and raw financial data.

### 4. Verify before presenting or committing

- [ ] Add or update tests at the required unit, property, integration, authorization, contract, import, UI, or operational level.
- [ ] Run every relevant repository-defined format, lint, type-check, test, dependency-scan, and secret-scan command. If a command does not exist yet, say so explicitly; do not fabricate a passing result.
- [ ] Verify transaction balance, transfer exclusion, split equality, atomicity, retry safety, tenant isolation, audit behavior, and date/currency handling wherever touched.
- [ ] Review migrations for safe rollout and rollback and avoid destructive financial-data changes.
- [ ] Review API/OpenAPI, configuration templates, runbooks, and user-facing states for required updates.
- [ ] Review the diff for unintended files, secrets, credentials, environment values, sensitive fixtures, and unrelated edits.

### 5. Report accurately

- [ ] Summarize behavior changed, evidence checked, tests run, and any tests that could not run.
- [ ] Name unresolved assumptions, risks, migration/recovery implications, and deferred follow-up work.
- [ ] Update roadmap checkboxes only when their full acceptance criteria are satisfied.
- [ ] Never report a recommendation as an ADR, an unrun check as passing, a backup as restorable without a restore drill, or partial milestone work as complete.

## Definition of done

A change is done only when it respects accepted decisions and milestone order, preserves all affected financial and tenant invariants, contains proportionate automated evidence, passes every available relevant quality/security check, updates contracts and operational documentation, introduces no secrets or sensitive logs, and accurately records any remaining work. Financial correctness, authorization, idempotency, auditability, exportability, and recoverability are release properties, not optional follow-up polish.
