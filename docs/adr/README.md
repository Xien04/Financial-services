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
| [0008 — Standardize API errors, request IDs, documentation, and pagination](0008-standardize-api-contracts.md) | Accepted 2026-10-27 |
| [0009 — Make financial writes idempotent through durable PostgreSQL identities](0009-make-financial-writes-idempotent.md) | Accepted 2026-10-27 |

Brenson Go accepted ADRs 0008–0009 on 2026-10-27 for
[issue #12](https://github.com/Xien04/Financial-services/issues/12), explicitly
confirming: "Both documents are accepted." Their opening tables summarize the
decisions. [PR #21](https://github.com/Xien04/Financial-services/pull/21) records
the acceptance; merging it closes #12. Implementation remains in #14 and the
owning financial milestones.

| Issue #12 criterion | Decision location | Current status |
|---|---|---|
| M1-API-DEC-01 — validation, errors, request IDs | ADR 0008, sections 1–3 | Accepted |
| M1-API-DEC-02 — generated OpenAPI and drift checks | ADR 0008, section 4 | Accepted; package compatibility must be verified in #14 |
| M1-API-DEC-03 — pagination and current route applicability | ADR 0008, section 5 | Accepted; no current collection route needs pagination |
| M1-API-DEC-04 — idempotency matching, replay, conflicts, concurrency, failures | ADR 0009, sections 1–5 and examples | Accepted |
| M1-API-DEC-05 — retention, cleanup, durable financial identities | ADR 0009, sections 6–7 | Accepted; deletion policy remains #13 |
| M1-API-DEC-06 — acceptance and links | Both acceptance records, Milestone 1 roadmap, and #12/#14 | Acceptance recorded; #12 closes through PR #21 |
