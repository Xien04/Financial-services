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
| [0010 — Define data retention, access, and account closure](0010-define-data-retention-and-deletion.md) | Accepted 2026-10-28 |
| [0011 — Define encrypted backups and measurable recovery targets](0011-define-backup-and-recovery-targets.md) | Accepted 2026-10-28 |

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
| M1-API-DEC-05 — retention, cleanup, durable financial identities | ADR 0009, sections 6–7 | Accepted; retention/closure policy is now recorded in ADR 0010 |
| M1-API-DEC-06 — acceptance and links | Both acceptance records, Milestone 1 roadmap, and #12/#14 | Acceptance recorded; #12 closes through PR #21 |

## Issue #13 accepted policies

Brenson Go accepted ADRs 0010–0011 on 2026-10-28, explicitly confirming:
"both files are accepted." Their opening tables summarize the accepted retention
periods and recovery targets. No cleanup, deletion, backup, or recovery implementation
is claimed. The policy PR closes #13 when merged; #18 implements and measures the
accepted backup/restore policy.

| Issue #13 criterion | Decision location | Current status |
|---|---|---|
| M1-POL-01 — data classes, access, retention, owners | ADR 0010, section 1 | Accepted |
| M1-POL-02 — deletion, audit preservation, backup expiry | ADR 0010, sections 2–4; ADR 0011 recovery gate | Accepted; no automatic physical financial-history erasure |
| M1-POL-03 — RPO/RTO targets and measurements | ADR 0011, section 1 | Accepted; one hour/four hours, not demonstrated |
| M1-POL-04 — backup cadence/protection/keys/retention/responsibility | ADR 0011, sections 2–5 | Accepted; deployment destination/custodian must be supplied by its operator |
| M1-POL-05 — future upload/export requirements and delivery ownership | ADR 0010 lifecycle table and delivery boundary; ADR 0011 drill scope | Accepted; features remain with their owning milestones |
| M1-POL-06 — owner acceptance and implementation links | Both acceptance records, Milestone 1 roadmap, and #13/#18 | Acceptance recorded; #13 closes through the policy PR |
