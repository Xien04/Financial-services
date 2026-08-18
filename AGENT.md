# Repository Instructions for AI Agents and Contributors

## Purpose and authority

This file is the operational entry point for work in this repository. It translates the repository's current documentation into execution rules; it does not replace the source documents or turn an undecided recommendation into an accepted architecture decision.

Read these sources before proposing or changing code:

1. `docs/adr/*.md` for accepted architecture decisions.
2. `docs/FINANCIAL_SEMANTICS.md` for accepted accounting conventions and executable examples.
3. `docs/PRODUCT_ARCHITECTURE.md` for product boundaries, domain invariants, and the planned architecture.
4. `docs/ROADMAP.md` for sequencing, dependencies, acceptance criteria, and current delivery status.
5. `README.md`, `.env.example`, `requirements.txt`, and `.gitignore` for repository state and setup constraints.

If the sources conflict, an accepted ADR governs the technical decision it addresses. Otherwise, preserve the product invariants and MVP boundaries in `docs/PRODUCT_ARCHITECTURE.md`, then follow the milestone gates in `docs/ROADMAP.md`. Do not resolve a material conflict silently: document it and add or supersede an ADR.

Normative words in this file have their ordinary standards meaning: **MUST** and **MUST NOT** are mandatory; **SHOULD** requires a documented reason to deviate; **MAY** is optional.

## Decision status: do not overstate it

The repository is in **Stage 0 / Milestone 0**. It contains documentation and configuration placeholders, but no Django API, Next.js application, database, Docker Compose stack, or automated tests.

There are currently **no accepted ADRs**. `docs/adr/README.md` contains only the ADR convention and explicitly says that blueprint decisions are recommendations until implementation begins and an ADR accepts them. Financial semantics version 1.0 is accepted; the first technical ADRs and interaction wireframes remain incomplete.

Consequently:

- MUST NOT claim that the modular monolith, ledger-entry model, PostgreSQL, or another planned choice has already been accepted by ADR.
- MUST NOT silently replace the planned stack or architecture with alternatives.
- Before scaffolding depends on those choices, MUST record and obtain acceptance of ADRs for at least the modular monolith, ledger-entry model, and PostgreSQL, as required by Milestone 1.
- MUST implement debit/credit and UI signs, lifecycle transitions, financial dates, month boundaries, rounding, currency precision, and executable metric formulas according to the accepted `docs/FINANCIAL_SEMANTICS.md`. Do not change them implicitly in code or an unrelated ADR.
- MUST complete and accept the Milestone 0 definitions and examples before marking Stage 1 foundation work complete.
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

The only established physical layout is:

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
    ├── ROADMAP.md
    └── adr/
        └── README.md
```

No physical backend, frontend, test, migration, or deployment directory convention has been accepted. Do not invent one and describe it as repository policy. The Stage 1 scaffolding ADRs or accompanying foundation change MUST define the physical layout before it becomes normative.

When that layout is defined, it MUST make the logical ownership above explicit and enforce these placement rules:

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

No test runner, formatter, linter, type checker, coverage percentage, or strict Python type-hint policy has been selected yet. Do not invent commands or claim a numeric coverage target. Milestone 1 MUST establish reproducible commands for formatting/linting, type checking, backend tests, frontend tests, integration tests, dependency scanning, and secret scanning.

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

`requirements.txt` is intentionally empty during Stage 0. MUST NOT add speculative or unpinned runtime dependencies before application code imports them. When Stage 1 scaffolding begins, select dependencies from executable requirements, pin exact production and development versions, and add automated scanning.

Apply the same evidence-based, locked-dependency policy to the frontend and other runtime manifests when they are created. A new dependency needs a concrete use, fit with the planned stack and deployment model, and inclusion in the appropriate lock/scanning workflow.

## Required workflow for every change

### 1. Establish context before proposing work

- [ ] Read this file and the source documents relevant to the requested area.
- [ ] Inspect `docs/adr/` for accepted, superseded, or proposed decisions; do not rely on filename examples as actual ADRs.
- [ ] Check the current milestone, its dependencies, incomplete prerequisites, and acceptance criteria in `docs/ROADMAP.md`.
- [ ] Inspect the existing tree, configuration, tests, and working-tree state; preserve unrelated work.
- [ ] Classify the request as MVP, V2/V3, or explicitly excluded scope.
- [ ] Identify unresolved Stage 0 conventions the change would otherwise guess.

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
