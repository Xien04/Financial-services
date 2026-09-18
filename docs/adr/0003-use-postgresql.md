# ADR 0003: Use PostgreSQL as the authoritative database

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-08-18 |
| Accepted by | Brenson Go on 2026-09-18 |
| Decision owners | Product owner and engineering |
| Related documents | [Product architecture](../PRODUCT_ARCHITECTURE.md), [financial semantics](../FINANCIAL_SEMANTICS.md), [ADR 0001](0001-use-django-modular-monolith.md), [ADR 0002](0002-use-ledger-entry-model.md) |

## Context

Financial Services requires exact decimal storage, relational integrity, atomic multi-row postings, uniqueness/idempotency constraints, concurrent imports, migrations, audit history, and dependable backup/restore operations. Its central data is highly relational and must remain authoritative across API and background-worker processes.

Using a different lightweight database in development or integration tests would allow behavior to diverge in decimal handling, constraints, locking, SQL, and transactions.

## Decision

Use PostgreSQL as the sole authoritative durable relational database for local development, CI integration tests, self-hosted deployments, and future managed deployments.

Unit tests that do not access persistence remain database-independent. Any test claiming database, migration, posting, authorization-query, concurrency, or integration evidence must run against PostgreSQL rather than SQLite.

### Data conventions

- Use native UUID primary keys generated through the application/database-supported PostgreSQL path.
- Use `NUMERIC(19,4)` for stored ledger and monetary values, with PHP quantization enforced by the domain before posting.
- Use `DATE` for financial dates and timezone-aware timestamps stored in UTC for system events.
- Use foreign keys, unique constraints, check constraints, and database transactions to reinforce domain invariants where PostgreSQL can express them safely.
- Store core financial relationships in normalized relational columns. JSON/JSONB is limited to variable source metadata, mappings, or provider payloads and is not the authoritative representation of accounts, entries, categories, reconciliation, or budget values.
- Use Django migrations as the only supported schema-change mechanism.

### Transaction and concurrency behavior

- A financial transaction and its ledger entries commit in one PostgreSQL transaction.
- Idempotency identities use database-enforced uniqueness in addition to service checks.
- Posting, import confirmation, reconciliation, and correction use explicit locking or conflict handling where concurrent writes could violate invariants.
- Implementation tests must cover retry races and concurrent operations against PostgreSQL.
- Redis may coordinate Celery work and caches but never becomes an authoritative financial store.

### Environments and operations

- Local development starts PostgreSQL through the root Docker Compose stack; direct host installation may be documented as optional.
- CI provisions PostgreSQL using the same supported major version as local/deployment defaults.
- Stage 1 selects and pins an actively supported PostgreSQL major version; this ADR intentionally does not pin a version before the environment is scaffolded.
- PostgreSQL is private to the application network, authenticated, and reached through environment-provided credentials.
- Production/self-hosted documentation must include automated backups, retention, encryption/access controls, and a tested restore runbook.
- Successful backup jobs are not sufficient evidence; restore drills are required before MVP release.

Workspace authorization remains mandatory in application services and query layers. PostgreSQL constraints supplement but do not replace object/workspace authorization. Row-level security is not required for MVP unless a later ADR introduces it with a complete operational and testing model.

## Alternatives considered

### SQLite

Rejected as the application/integration database because its concurrency, type behavior, constraint behavior, and migration/runtime characteristics differ materially from PostgreSQL. It may not be used to claim persistence correctness.

### MySQL or MariaDB

Not selected because PostgreSQL aligns with the existing architecture recommendation and provides the needed exact numeric, constraint, indexing, transactional, and JSON metadata capabilities without a demonstrated benefit from changing direction.

### Document database

Rejected because workspace membership, accounts, entries, categories, imports, reconciliation, budgets, and audit relationships require strong relational integrity and multi-row transactions.

### Event store as the primary database

Not selected for MVP because the immutable ledger already preserves financial history inside a relational model. A separate event-store architecture would add operational and projection complexity without a proven requirement.

## Consequences

### Positive

- Development, CI, and deployment exercise the same database semantics.
- Exact numeric types and constraints support ledger correctness.
- Atomic transactions and concurrency controls support posting and imports.
- Django migrations and PostgreSQL tooling provide a mature operational path.
- Relational queries support explainable report drill-down and tenant filtering.

### Costs and constraints

- Contributors need Docker or a compatible PostgreSQL installation.
- CI and local test startup are heavier than SQLite.
- Backup, restore, upgrade, monitoring, connection management, and version support require operational ownership.
- PostgreSQL-specific features must be used intentionally and covered by migrations/tests.

## Acceptance criteria

- [x] Product owner accepts PostgreSQL as the sole authoritative relational database.
- [x] Product owner accepts PostgreSQL for persistence and integration tests rather than SQLite.
- [x] Product owner accepts `NUMERIC(19,4)`, UUID, date/timestamp, constraint, and normalized-data conventions.
- [x] Product owner accepts Docker Compose PostgreSQL for the default local environment.
- [x] Product owner accepts database backup and restore drills as release requirements.
- [x] Product owner accepts deferring the exact PostgreSQL major-version pin to Stage 1 scaffolding.

Accepted on 2026-09-18. Database scaffolding follows this decision; changing it requires a superseding ADR.
