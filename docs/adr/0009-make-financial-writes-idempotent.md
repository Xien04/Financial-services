# ADR 0009: Make financial writes idempotent through durable PostgreSQL identities

| Field | Value |
|---|---|
| Status | Proposed — awaiting product-owner review |
| Date | 2026-10-27 |
| Decision owners | Brenson Go (product owner) and engineering |
| Accepted by | Not yet accepted |
| Related work | [Decision issue #12](https://github.com/Xien04/Financial-services/issues/12), [API foundation #14](https://github.com/Xien04/Financial-services/issues/14), Milestones 2 and 4 |
| Related records | [ADR 0002](0002-use-ledger-entry-model.md), [ADR 0003](0003-use-postgresql.md), [proposed ADR 0008](0008-standardize-api-contracts.md), [financial semantics](../FINANCIAL_SEMANTICS.md) |

## Proposal in plain language

If you save a PHP 100.00 expense and lose your connection, trying that same save
again must return its original result. It must never create a second expense.
Each intended action has one operation key. A new expense gets a new key; a retry
keeps the old key. A tracking/request ID identifies each individual attempt.

| Choice to review | Recommendation |
|---|---|
| Same key and same intended action | Return the original successful receipt |
| Same key with a changed amount or other meaningful input | Reject the conflict; do not silently overwrite |
| Two attempts arrive together | One proceeds; the other retries using the same key |
| Failure before anything commits | Roll back everything; retry may safely try again |
| A retry months later | Retained financial operation identity still prevents another posting |
| Retention | Keep a small operation record with the financial history; do not store a second full financial response |

This is a proposed contract. It adds no ledger table, endpoint, dependency, or
runtime behavior and does not complete issue #12 before owner acceptance.

## Context

Accepted ADRs 0002–0003 and financial semantics already require atomic postings,
immutable history, PostgreSQL uniqueness, and safe retries across APIs, imports,
and workers. A disabled Save button alone cannot enforce those requirements.
Requests can overlap, responses can be lost after a commit, and workers can run
again after restarting. Expiring a response cache must not allow a second posting.

## Proposed decision

### 1. Identify an intended operation separately from an HTTP request

Require `Idempotency-Key` on future transaction creation, posting, correction,
voiding, import confirmation, and other financial write operations with the same
retry risk. Clients create a random UUIDv4 before first submission and reuse it
for every retry of that intended action. Accept one canonical UUIDv4 string;
missing, malformed, or repeated keys give 400 `idempotency_key_required` or
`invalid_idempotency_key` before any domain mutation.

Scope the durable identity by **workspace UUID + initiating user UUID + stable
operation name/version + key digest**. Use SHA-256 of the canonical key; the
digest is not a credential. Freeze operation names/versions for retained
identities; a deployment or route rename must not silently reset the namespace.
The same key in another scope is independent. Store the initiating actor so a
different user cannot obtain another user's receipt by knowing its key.

Authenticate and check current workspace/object permissions before returning
either a fresh result or a replay. A key is never authorization. A revoked member
cannot retrieve retained financial information through replay. Workers retain
the operation's actor/workspace identity, reload current state, and invoke the
owning service with their documented authorization policy; they cannot bypass
it merely because work was queued earlier.

Financial services must require this identity for internal callers as well as
HTTP. Authentication, CSRF bootstrap, activity, and health routes do not acquire
idempotency keys or replay password/session responses. #14 creates no financial
endpoint just to exercise this convention.

### 2. Compare the validated command, not the raw HTTP bytes

Reject malformed/ambiguous input first, including duplicate JSON keys, unknown
fields, invalid UUIDs, and unsupported money precision. Convert valid input into
an operation-versioned canonical command using the owning service's existing
validation rules:

- Sort JSON object keys; preserve the order of arrays unless the operation
  explicitly defines them as unordered. Keep absent and null distinct except
  where the documented serializer applies a default.
- Normalize UUIDs, dates, and exact decimal strings to their accepted domain
  representations. PHP 100.0 and 100.00 may match after valid normalization;
  unsupported precision must fail rather than be rounded into a match.
- Include target resource IDs, all meaningful fields, and explicit defaults.
  Do not silently trim or case-fold user text unless that field's domain permits it.
- Exclude cookies, CSRF tokens, request IDs, the operation key, and transport-only
  headers. Use a versioned deterministic UTF-8 JSON serialization with no floats
  and SHA-256 to produce the command digest. Keep the canonicalization version
  with the retained identity and continue to understand old versions on replay.

Financial dates and other time-dependent choices must be explicit in the
submitted command. Resolve "today" once before the first submission; do not
recompute it on a retry. Canonical defaults must be deterministic for the
operation version. Check a retained identity before rerunning state-dependent
business validation: a later void, changed balance, or archived account must not
turn the same authorized replay into a different operation or validation failure.

The retained record stores the digest and result references, not the raw submitted
body. A different digest for an existing scoped key returns 409
`idempotency_conflict` without modifying anything or revealing the original input.
Formatting changes to JSON object order alone do not create a conflict.

### 3. Commit the identity and financial result atomically

Use PostgreSQL database-enforced uniqueness for the scoped identity. The owning
service acquires a transaction-scoped advisory lock derived from that scope,
checks any existing identity, validates the current operation, and commits the
operation record, all financial changes, and required audit records in one
explicit transaction. A lock is an additional concurrency control; the unique
constraint remains mandatory. Hash collisions may delay unrelated work but must
never make one operation replay another's result.

Use a non-blocking lock attempt for this idempotency scope. If another attempt
holds it, return 409 `idempotency_in_progress` with `Retry-After: 1`; the caller
keeps the same key and retries with bounded backoff. No second posting begins.
After commit the waiting caller can retrieve the retained result. After process
death/rollback the transaction lock releases and no separate stale lock record
requires time-based deletion. Other domain locks still enforce ledger invariants.

Do not hold this transaction open for email, network calls, or an entire import
file. Future imports commit a durable confirmation/job identity and then post
bounded groups, each with durable row identities. Do not describe a partially
completed file as one atomic transaction.

### 4. Replay a stable receipt without performing the operation again

After success, replay the original HTTP status and a stable operation receipt
containing the original operation/result UUIDs and immutable outcome fields.
Each real operation defines that receipt in its OpenAPI contract. A future create
can return 201 on first success and replay; asynchronous confirmation can return
202 with the same job reference. Current mutable resource state belongs to its
normal read API and is not re-executed or mistaken for a new creation.

An illustrative future creation receipt is:

```json
{
  "operation_id": "b74574bc-2f49-4f3d-9391-c42b44552183",
  "transaction_id": "dcb11437-6ffd-4469-a061-f5d4534c9f2f",
  "outcome": "created"
}
```

Both the first 201 response and a successful retry return this same receipt.
`created` describes the original operation, not the transaction's current posting
status. Actual endpoint fields are implemented with their owning domain later.

Set `Idempotency-Replayed: false` on the first successful response and `true` on
a successful replay. Replay safe headers such as the original relative `Location`
when present. Generate a fresh `X-Request-ID` for the retry. Never replay cookies,
CSRF tokens, credentials, old request IDs, or arbitrary stored headers. Responses
containing financial/user data remain private with `Cache-Control: no-store`.

Rebuild the original receipt from retained operation metadata and immutable
result/version references, including after a later void/correction. It describes
the original operation's outcome and must not assert that its transaction is
still active. Do not substitute a replacement transaction. If required result
evidence is unexpectedly missing, fail closed with generic 503
`idempotency_result_unavailable`; do not run the write again.

### 5. Define failures and uncertain outcomes

| Situation | Rule |
|---|---|
| Invalid request, failed authorization, rate limit, or business validation rejection | No financial mutation or successful identity; return the appropriate safe error |
| Same scoped key and changed command after success | 409 `idempotency_conflict`; original operation unchanged |
| Another attempt holds the scope lock | 409 `idempotency_in_progress`, `Retry-After: 1`; keep the key |
| Exception before commit | Roll back operation, entries, identity, and audit changes together |
| Commit succeeds but the HTTP response is lost | Retry with the same key discovers and replays the committed result |
| Commit outcome is unknown because the connection failed | Do not assume rollback or generate a new key; retry the same identity once the database is reachable |
| Application cannot inspect authoritative identity state | 503; never fall back to an unprotected write or a cache-only decision |

Do not cache failed requests as successful operations. If no operation committed,
a corrected request may use that uncommitted key. After a success the key is bound
to its original command forever within its scope while history is retained.
Generic clients must not automatically retry every POST with a fresh key.

### 6. Retain the durable identity with the financial history

Do not introduce a full-response cache or an expiration timer for successful
financial identities in MVP. Retain the compact key/command digests, versioned
scope, actor/workspace references, original status, and immutable receipt/result
references as long as their financial history is retained. No key-reuse window
opens after 24 hours, session expiry, audit-log rotation, archival, or a void.

Bound record growth by writing identities only for successful authorized
operations, applying existing/operation-specific admission limits, and storing
minimal metadata. Do not make raw keys, digests, request bodies, or complete
financial results operational log fields. Current session/rate-limit cleanup
continues under its own policy and must not delete these identities.

Cleanup may remove transient request context after the transaction; PostgreSQL
releases transaction locks automatically. Archive/void retains the identity.
Future erasure of a workspace and its financial records must follow the accepted
retention/deletion policy from [#13](https://github.com/Xien04/Financial-services/issues/13).
This ADR chooses no statutory retention period and authorizes no deletion.
Until that policy is accepted, do not purge successful financial identities.

Back up and restore identities with their financial results in the same
consistent PostgreSQL recovery point. This prevents replay of operations present
in a restored database. It cannot recover operations lost after an older backup:
after such a restore, pause financial writes/import workers and reconcile the
recovery gap before accepting outstanding retries. #13/#18 must specify that
operational recovery gate; never claim idempotency alone eliminates recovery loss.

### 7. Keep transport retries distinct from business duplicate detection

A new key means a new intended action; two equal manual expenses may be legitimate.
Do not suppress them merely because their dates and amounts match. Imports also
need database-enforced workspace/batch/row or stable-source identities so that a
different HTTP key or worker attempt cannot repost the same confirmed row.
Probable duplicates still require the accepted visible review flow.

An import's changed selection/mapping creates a new confirmed revision; it cannot
reuse an already committed command identity to overwrite history. Resumption
reuses committed row identities and posts only remaining authorized rows. An
atomic void-and-repost correction has its own durable operation key and result
references; retrying it must not void/repost twice.

## Executable-style examples for future domain tests

These scenarios use synthetic data and symbolic keys `K1`/`K2`, representing
different generated UUIDv4 values. They are specifications, not working endpoints
or claims that ledger tests already run.

| Given / action | Expected result |
|---|---|
| User U in workspace W submits operation O, key K1, valid PHP 100.00 command | One balanced posting; 201 receipt R; replay header false |
| U repeats O/K1 with the same command after losing the response | Same 201 receipt R; replay true; new request ID; no new entries |
| U repeats O/K1 with JSON properties reordered / valid PHP 100.0 representation | Same canonical command and result R |
| U repeats O/K1 changing PHP 100.00 to PHP 200.00 | 409 conflict; one PHP 100.00 posting remains |
| Two separate PostgreSQL connections submit O/K1 concurrently | At most one commits; other receives in-progress or the committed replay |
| First attempt rolls back after creating provisional entries | No entries/identity/audit commit; retry can produce exactly one posting |
| First attempt commits and the process dies before sending its response | Retry returns R without another posting |
| User U loses membership before retry | Permission failure; no financial receipt disclosed or new posting |
| U submits a separate intended expense with K2 and the same amount | A separate posting is allowed; keys do not replace duplicate review |
| Retry O/K1 after months, session cleanup, archival, or later correction | Original receipt R, not the correction; no second operation |
| Result evidence is unexpectedly absent but K1's identity remains | Safe 503; no attempt to recreate the financial operation |
| Same confirmed import row resumes under another job/HTTP key | Existing row identity prevents duplicate posting |

## Alternatives considered

- **Disable the button / remember keys in the browser:** useful UX but cannot
  protect concurrent requests, process restarts, or background workers.
- **Redis or an expiring response cache as the authority:** losing/expiring the
  record could allow a duplicate. PostgreSQL already owns atomic financial state.
- **Keep every full request/response forever:** easy literal replay but duplicates
  sensitive financial data. Immutable receipts and minimal metadata reduce that cost.
- **Expire successful identities after a short TTL:** bounds storage but violates
  the accepted no-second-posting invariant on a later retry.
- **Deduplicate all equal-looking expenses:** can erase legitimate purchases and
  contradicts the explicit import duplicate-review workflow.

## Consequences and delivery boundary

Durable metadata grows with successful financial operations and must remain
consistent with backups and future deletion policy. Stable receipts deliberately
describe the original operation rather than the current resource. Clients must
preserve operation keys across uncertain outcomes; changing a key is a new action.

#14 documents the accepted convention and adds only support actually needed by
current routes; it does not require a speculative financial identity table.
Milestone 2's owning services/migrations implement durable uniqueness, locking,
receipts, and real PostgreSQL concurrency/rollback tests. Milestone 4 implements
batch/row identity and bounded import resume tests. A shared API helper is never
evidence that a financial posting is balanced, authorized, or safe to retry.

## Acceptance record

- [ ] Brenson Go accepts key scope, command matching, and conflict behavior.
- [ ] Brenson Go accepts PostgreSQL atomicity, concurrent-attempt, and failure rules.
- [ ] Brenson Go accepts original receipt/status replay and current authorization checks.
- [ ] Brenson Go accepts identity retention with financial history and the recovery-gap limitation.
- [ ] Record explicit acceptance/date and link the accepted record from #12/#14.

No acceptance has been recorded. Issue #12 and milestone gates remain open.

## References

- [Accepted retry and correction semantics](../FINANCIAL_SEMANTICS.md#43-corrections-and-deletion)
- [Accepted import confirmation and resume behavior](../wireframes/02_CSV_IMPORT.md#7-step-4--confirm)
- [Django atomic transactions](https://docs.djangoproject.com/en/5.2/topics/db/transactions/)
- [PostgreSQL transaction-level advisory locks](https://www.postgresql.org/docs/17/explicit-locking.html#ADVISORY-LOCKS)
