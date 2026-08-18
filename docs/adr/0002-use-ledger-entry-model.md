# ADR 0002: Use a balanced ledger-entry model

| Field | Value |
|---|---|
| Status | Proposed |
| Date | 2026-08-18 |
| Decision owners | Product owner and engineering |
| Related documents | [Accepted financial semantics](../FINANCIAL_SEMANTICS.md), [product architecture](../PRODUCT_ARCHITECTURE.md), [transaction wireframe](../wireframes/01_TRANSACTION_ENTRY.md), [reconciliation wireframe](../wireframes/03_RECONCILIATION.md) |

## Context

The application must support accounts, opening balances, income, expenses, transfers, split transactions, refunds, credit-card payments, loan principal/interest, adjustments, imports, reconciliation, and explainable reports. A single signed amount and category on a transaction cannot represent these cases reliably without special-case balance logic.

Financial semantics version 1.0 already defines debit-positive signs, immutable posted entries, Philippine-peso precision, per-account-entry reconciliation, system-equity roles, and report formulas. The implementation needs one model that enforces those accepted behaviors centrally.

## Decision

Represent each user-facing financial event as a `Transaction` that owns a balanced set of `LedgerEntry` records.

### Transaction

A transaction stores user-facing context and provenance, including workspace, transaction/posted dates, payee, description, source, type, posting status, import identity, idempotency identity, audit linkage, and timestamps.

Posting status is exactly:

```text
pending | posted | void
```

Pending transactions may have mutable provisional entries but do not affect authoritative balances or reports. Posted entries are immutable. Void is terminal and excludes the original entries from active calculations while retaining them for audit.

### Ledger entry

Every entry stores an exact signed `amount` in `PHP` and targets exactly one of:

1. An account;
2. An income/expense category; or
3. An accepted system-equity role.

The database and domain service enforce exclusive targeting. A posted transaction must have at least one account entry and:

```text
sum(entry.amount) = 0
```

Use the accepted debit-positive convention:

- Asset increases and expense increases are positive.
- Liability increases and income increases are negative.
- Transfers have exactly two account entries and no category.
- Opening balances and non-operating adjustments balance through explicit system-equity roles, never fake categories.

Opening amounts accepted during account creation are posted as opening-balance transactions. Account metadata is not added independently to ledger-derived balances.

### Posting and correction service

One ledger domain service owns validation, sign conversion, quantization, posting, voiding, replacement, and idempotency. A transaction and every entry commit or fail in one database transaction.

- Create/post operations require an idempotency key.
- Retrying the same operation returns the original result.
- Correcting an unreconciled posted transaction atomically voids it and posts a linked replacement.
- A reconciled account entry blocks correction until the latest affected reconciliation is undone or a current-period adjustment is posted.
- User-facing deletion maps to audited void, never physical deletion.

API serializers, imports, reports, workers, and the client must not create entries or reproduce posting rules directly.

### Categories and system equity

Each workspace receives visible, non-deletable `Uncategorized Income` and `Uncategorized Expense` categories. They remain part of operating reports. Transfers and system equity are not categories.

System roles are an explicit constrained value set beginning with:

- `opening_balance_equity`
- `balance_adjustment_equity`

Adding a role that changes financial meaning requires updating accepted semantics and tests.

### Reconciliation

Reconciliation belongs to an account and links to account-side ledger entries through `ReconciliationItem` or an equivalent relation with unique entry membership. It is not transaction status. This permits transfer legs to reconcile independently on different account statements.

### Balances and reporting

- Ledger-derived account balance is the sum of active posted account entries through the financial date.
- Accepted valuation-snapshot behavior applies only to eligible manually valued accounts.
- Reports sum category or account entries according to accepted formulas rather than transaction type labels.
- Pending and void transactions remain excluded from official totals.
- Dashboard/report drill-down filters must reproduce the aggregate from the same active entries.

## Alternatives considered

### Store one amount, account, and category per transaction

Rejected because transfers, splits, loan payments, refunds, and corrections would require incompatible special cases and make report/balance reconciliation fragile.

### Maintain balances as directly editable columns

Rejected as the authoritative model because mutable totals lose provenance and cannot explain or reliably rebuild historical balances. Cached calculated snapshots remain allowed as non-authoritative performance aids.

### Full external general-ledger/chart-of-accounts product

Not selected because it would expose accounting complexity outside the personal-finance scope. The internal balanced model is sufficient while the user interface remains transaction-oriented.

### Mutate posted entries in place

Rejected because it destroys auditability and can invalidate reconciled statements and prior reports silently.

## Consequences

### Positive

- Transfers and credit-card/loan principal movements do not inflate income or expense.
- Splits, refunds, adjustments, and opening balances share one invariant.
- Balances and reports are rebuildable and explainable.
- Per-entry reconciliation matches real statement workflows.
- Immutable history and idempotent posting improve auditability and retry safety.

### Costs and constraints

- Posting services and database constraints are more complex than CRUD on a single transaction row.
- Corrections create additional retained records.
- Every report must understand active transaction state and accepted entry dimensions.
- Property-based and integration tests are mandatory for signs, balancing, correction, and retry behavior.

## Acceptance criteria

- [ ] Product owner accepts Transaction as the user-facing aggregate and LedgerEntry as the balance source.
- [ ] Product owner accepts debit-positive balanced postings and exclusive entry targets.
- [ ] Product owner accepts immutable posted entries and audited void-and-replace corrections.
- [ ] Product owner accepts explicit system-equity roles and uncategorized operating categories.
- [ ] Product owner accepts per-account-entry reconciliation outside transaction status.
- [ ] Product owner accepts one authoritative posting service used by APIs, imports, and workers.

No ledger implementation may treat this ADR as accepted while its status remains Proposed.
