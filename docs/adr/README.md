# Architecture Decision Records

Add a short ADR here whenever an important technical decision is made. Use sequential, zero-padded filenames and an imperative description, for example:

- `0001-use-django-modular-monolith.md`
- `0002-use-ledger-entry-model.md`
- `0003-use-postgresql.md`

Each ADR should record the status, context, decision, consequences, and date. Decisions described in the product blueprint are recommendations until implementation begins and an ADR accepts them.

## Current records

| ADR | Status |
|---|---|
| [0001 — Use a Django modular monolith](0001-use-django-modular-monolith.md) | Accepted 2026-09-18 |
| [0002 — Use a balanced ledger-entry model](0002-use-ledger-entry-model.md) | Accepted 2026-09-18 |
| [0003 — Use PostgreSQL as the authoritative database](0003-use-postgresql.md) | Accepted 2026-09-18 |
| [0004 — Use uv and the foundation toolchain](0004-use-uv-and-foundation-tooling.md) | Accepted 2026-10-22 |
| [0005 — Establish automated quality checks](0005-establish-automated-quality-checks.md) | Accepted for implementation 2026-10-22 |
| [0006 — Use Django sessions for browser authentication](0006-use-django-sessions-for-browser-authentication.md) | Accepted 2026-10-22 |
| [0007 — Implement shared authentication rate limits and browser protections](0007-implement-authentication-rate-limits.md) | Accepted for implementation 2026-10-22 |
| [0008 — Standardize API errors, request IDs, documentation, and pagination](0008-standardize-api-contracts.md) | Proposed 2026-10-27 — awaiting review |
| [0009 — Make financial writes idempotent through durable PostgreSQL identities](0009-make-financial-writes-idempotent.md) | Proposed 2026-10-27 — awaiting review |

ADRs 0008–0009 are the proposal for
[issue #12](https://github.com/Xien04/Financial-services/issues/12). Their opening
tables summarize the choices for product-owner review. They do not change the
accepted architecture or authorize implementation before acceptance is recorded.

| Issue #12 criterion | Proposal location | Current status |
|---|---|---|
| M1-API-DEC-01 — validation, errors, request IDs | ADR 0008, sections 1–3 | Proposed |
| M1-API-DEC-02 — generated OpenAPI and drift checks | ADR 0008, section 4 | Proposed; package compatibility must be verified in #14 |
| M1-API-DEC-03 — pagination and current route applicability | ADR 0008, section 5 | Proposed; no current collection route needs pagination |
| M1-API-DEC-04 — idempotency matching, replay, conflicts, concurrency, failures | ADR 0009, sections 1–5 and examples | Proposed |
| M1-API-DEC-05 — retention, cleanup, durable financial identities | ADR 0009, sections 6–7 | Proposed; deletion policy remains #13 |
| M1-API-DEC-06 — acceptance and links | Both acceptance records and the Milestone 1 roadmap | Pending explicit owner acceptance; update #12/#14 after acceptance |
