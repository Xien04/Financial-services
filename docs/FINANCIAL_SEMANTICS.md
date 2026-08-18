# Financial Services — Financial Semantics

| Field | Value |
|---|---|
| Status | Accepted |
| Version | 1.0 |
| Last updated | 2026-08-18 |
| Applies to | MVP, Philippine peso (`PHP`) base currency |
| Accepted by | Brenson Go on 2026-08-18 |

This document defines the accepted financial behavior that the ledger, API, imports, reports, budgets, and interface must share. It turns the product blueprint into testable examples. These product semantics are binding unless a later accepted revision explicitly supersedes them.

The words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Core accounting convention

### 1.1 Balanced entries

A user-facing `Transaction` owns two or more ledger entries. Every posted transaction MUST satisfy:

```text
sum(entry.amount) = 0
```

Amounts use a debit-positive convention:

| Entry target | Increase | Decrease | Normal raw balance |
|---|---:|---:|---:|
| Asset account | Positive | Negative | Positive |
| Liability account | Negative | Positive | Negative |
| Expense category | Positive | Negative/refund | Positive |
| Income category | Negative | Positive/reversal | Negative |
| System equity | Depends on balancing entry | Depends on balancing entry | Not user-facing |

An entry MUST target exactly one dimension:

1. A user account;
2. An income or expense category; or
3. A system-only equity purpose such as `opening_balance_equity` or `balance_adjustment_equity`.

System equity entries are never shown as user categories and never contribute to income, expense, cash-flow, savings-rate, burn-rate, or budget totals. The ledger schema MUST represent the system purpose explicitly; it MUST NOT encode opening balances as fake income.

### 1.2 Account classifications and signs

| Account type | Classification | Raw increase | Displayed balance |
|---|---|---:|---:|
| Cash | Asset | Positive | Raw balance |
| Checking | Asset | Positive | Raw balance |
| Savings | Asset | Positive | Raw balance |
| Investment | Asset | Positive | Raw or valuation-adjusted balance |
| Asset | Asset | Positive | Raw or valuation-adjusted balance |
| Credit card | Liability | Negative | `-1 × raw balance` |
| Loan | Liability | Negative | `-1 × raw balance` |
| Other | Chosen as asset or liability at creation | According to classification | According to classification |

A positive displayed liability balance means an amount is owed. A negative displayed liability balance means the account has a credit. Values MUST NOT be clamped to zero.

The signed activity amount shown in an account register is the raw account-entry amount:

- Asset deposits/inflows are positive; withdrawals/outflows are negative.
- Liability charges/borrowings are negative; payments/credits are positive.

For an included account, its net-worth contribution is its raw balance. This makes asset balances additive and liability balances subtractive without UI-specific sign logic.

### 1.3 Authoritative balance

For a ledger-based account at date `D`:

```text
raw_balance(D) = sum(active account entries with transaction_date <= D)
```

`active` means the owning transaction is `posted`; pending and void transactions are excluded. Opening balances are real posted ledger transactions and MUST NOT also be added from an account metadata field.

For a manually valued asset or investment account, the latest authoritative manual snapshot on or before `D` becomes the end-of-day balance for its snapshot date. Active account entries after that date are added through `D`:

```text
raw_balance(D) = latest_snapshot.balance
               + sum(active entries where snapshot_date < transaction_date <= D)
```

If no snapshot exists, the ledger balance applies. Calculated snapshots are caches and never override the ledger. Manual valuation snapshots are allowed only for manually valued asset, investment, and other-asset accounts in MVP; transactional cash, checking, savings, credit-card, and loan accounts are corrected through ledger adjustments or reconciliation instead.

Snapshot input and display use the account-native displayed sign. The domain converts liability values to raw ledger signs if liability valuation snapshots are supported later.

## 2. Transaction classifications

`transaction_type` describes the user intent but MUST NOT be the source of reporting totals. Reports derive from category entries.

| Type | Required shape | Reporting behavior |
|---|---|---|
| `income` | At least one income-category entry and one account entry | Income categories contribute to income |
| `expense` | At least one expense-category entry and one account entry | Expense categories contribute to expense; refunds are negative expense entries |
| `transfer` | Exactly two account entries and no income/expense category | Excluded from income, expense, cash flow, burn rate, savings rate, category spending, and budgets |
| `adjustment` | Account entry plus explicit system-equity entry | Changes account/net worth; excluded from operating metrics |

A transaction containing both principal movement and an expense, such as a loan payment with interest, is classified as `expense`; only its expense-category entry affects expense reports. MVP MUST NOT infer reporting behavior from the type alone.

Transfers MUST affect exactly two accounts in MVP. A transaction MUST NOT contain both income and expense categories in MVP; compound payroll withholding and similar workflows are deferred until their semantics are separately accepted.

### 2.1 Uncategorized income and expense

Every workspace has visible, non-deletable system categories named `Uncategorized Income` and `Uncategorized Expense`. A posted income or expense that has no user-selected category MUST use the corresponding uncategorized category; it MUST NOT use system equity merely because classification is incomplete.

Uncategorized entries count in income, expense, cash-flow, burn-rate, savings-rate, and category-spending reports so totals still reconcile to posted activity. They are highlighted for review, cannot be archived or reparented, and cannot receive a budget line. Uncategorized expense therefore appears as unbudgeted spending. Reclassification of a posted transaction follows the same audited void-and-repost rule as any other correction.

Imports MAY suggest income or expense from the account classification and amount sign, but the preview must make that proposed type visible. Transfer and refund recognition must not be silently inferred from amount sign alone.

## 3. Canonical posting examples

All examples use Philippine pesos (`PHP`, symbol `₱`) and assume the transaction becomes posted. Positive and negative signs below are stored ledger amounts.

### 3.1 Opening balances

Opening a checking account with ₱1,000:

| Target | Amount |
|---|---:|
| Checking account | `+1000.00` |
| System: opening balance equity | `-1000.00` |

Result: checking displays `₱1,000.00`; net worth increases by `₱1,000.00`; income and cash flow remain unchanged.

Opening a credit card with ₱600 owed:

| Target | Amount |
|---|---:|
| Credit-card account | `-600.00` |
| System: opening balance equity | `+600.00` |

Result: the card displays `₱600.00 owed`; net worth decreases by `₱600.00`; expense and cash flow remain unchanged.

The opening-balance date is the effective beginning-of-day balance date. An opening balance is created atomically with the account. Changing it uses an audited void-and-repost sequence.

### 3.2 Income

A ₱2,000 paycheck deposited into checking:

| Target | Amount |
|---|---:|
| Checking account | `+2000.00` |
| Income: Salary | `-2000.00` |

Result: checking and net worth increase by `₱2,000.00`; income and cash flow increase by `₱2,000.00`.

### 3.3 Expense

A ₱50 grocery purchase paid from checking:

| Target | Amount |
|---|---:|
| Expense: Groceries | `+50.00` |
| Checking account | `-50.00` |

Result: checking and net worth decrease by `₱50.00`; expense increases and cash flow decreases by `₱50.00`.

### 3.4 Split expense

An ₱82.40 checking purchase split between groceries and household supplies:

| Target | Amount |
|---|---:|
| Expense: Groceries | `+67.40` |
| Expense: Household | `+15.00` |
| Checking account | `-82.40` |

The category allocations MUST equal the magnitude of the account-side amount exactly. A split that differs by even one currency minor unit cannot post.

### 3.5 Asset transfer

Moving ₱500 from checking to savings:

| Target | Amount |
|---|---:|
| Savings account | `+500.00` |
| Checking account | `-500.00` |

Result: total net worth and all income/expense metrics remain unchanged.

### 3.6 Credit-card purchase

Charging ₱75 of groceries:

| Target | Amount |
|---|---:|
| Expense: Groceries | `+75.00` |
| Credit-card account | `-75.00` |

Result: the displayed card balance owed and expense increase by `₱75.00`; net worth and cash flow decrease by `₱75.00`.

### 3.7 Credit-card payment

Paying ₱200 from checking to a credit card:

| Target | Amount |
|---|---:|
| Credit-card account | `+200.00` |
| Checking account | `-200.00` |

Result: cash and the amount owed each decrease by `₱200.00`; net worth is unchanged. The payment is a transfer, not an expense.

### 3.8 Refund

A ₱20 grocery refund returned to checking:

| Target | Amount |
|---|---:|
| Checking account | `+20.00` |
| Expense: Groceries | `-20.00` |

Result: the refund reduces grocery expense and increases cash flow and net worth by `₱20.00`. A credit-card refund uses `+20.00` on the card account and the same `-20.00` expense entry.

Refunds remain `expense` transactions and retain a reference to the original transaction when known. A refund may exceed spending in the selected reporting period; reports and budgets MUST preserve the resulting negative net expense rather than clamp it.

### 3.9 Loan proceeds

Receiving ₱10,000 of loan proceeds into checking:

| Target | Amount |
|---|---:|
| Checking account | `+10000.00` |
| Loan account | `-10000.00` |

Result: assets and liabilities increase equally; net worth, income, expense, and cash flow remain unchanged. Loan proceeds are financing, not income.

### 3.10 Loan payment with interest

A ₱300 payment consisting of ₱250 principal and ₱50 interest:

| Target | Amount |
|---|---:|
| Loan account | `+250.00` |
| Expense: Interest | `+50.00` |
| Checking account | `-300.00` |

Result: the displayed loan balance falls by `₱250.00`; expense and cash flow decrease by `₱50.00`; net worth falls by `₱50.00`. Principal repayment is not an expense.

### 3.11 Manual balance adjustment

Correcting an unreconciled checking balance upward by ₱25 when no income or expense occurred:

| Target | Amount |
|---|---:|
| Checking account | `+25.00` |
| System: balance adjustment equity | `-25.00` |

Result: the account and net worth increase by `₱25.00`; operating income, expense, and cash flow remain unchanged. The user MUST supply a reason, and the change is audited.

If the ₱25 actually represents missing income, the user records an income transaction instead. The application MUST NOT silently create balance adjustments during reconciliation.

### 3.12 Void and replacement

Suppose the posted ₱50 grocery transaction from section 3.3 should have been ₱45. The correction runs atomically:

1. Mark the original transaction void while retaining its `+50.00` grocery and `-50.00` checking entries for audit.
2. Post a replacement linked to the original with `+45.00` to groceries and `-45.00` to checking.
3. Exclude the void transaction and include the replacement in all active calculations.

Result: checking and net worth decrease by `₱45.00`, grocery expense is `₱45.00`, and exports/audit views retain both versions. A failure at any point leaves the original posted and creates no replacement; retrying the same correction is idempotent.

## 4. Transaction lifecycle and correction

### 4.1 Posting status

Transaction posting status has three values:

```text
pending -> posted -> void
    └──────────────> void
```

- `pending`: balanced provisional entries may be edited; excluded from authoritative balances, reports, budgets, goals, and reconciliation.
- `posted`: entries are immutable and included in authoritative balances and eligible reports.
- `void`: terminal, excluded from active balances and reports; original entries and audit history remain stored.

There is no persisted draft transaction in MVP; incomplete import rows remain in import staging. Manual creation defaults to `posted` unless the user explicitly marks the transaction pending.

Posting a pending transaction validates all invariants and makes its entries immutable. A posted transaction MUST NOT return to pending.

### 4.2 Reconciliation is not transaction status

Reconciliation MUST be tracked per account entry, through a `ReconciliationItem` or equivalent link between a reconciliation record and an account-side ledger entry. It MUST NOT be a transaction-wide status. This is required because the checking and savings legs of one transfer can appear on different statements and be reconciled independently.

Consequently, the accepted model removes `reconciled` from the transaction status values described in the initial blueprint. Reconciliation state is orthogonal to `pending`, `posted`, and `void`.

### 4.3 Corrections and deletion

- Pending transactions may be edited before posting; every change updates validation and provenance.
- An unreconciled posted transaction is corrected atomically by voiding it and posting a replacement linked to the original.
- A posted transaction with any reconciled account entry cannot be voided or replaced until the affected latest reconciliation is undone, or the user records a new current-period adjustment.
- User-facing deletion of any persisted transaction is an audited void operation, never physical erasure.
- A void transaction cannot be restored. Restoring its economic effect requires a new linked transaction.
- Retrying a create, post, void-and-repost, or import operation with the same idempotency key returns the original result and creates no additional entries.

Voiding changes reports for the original transaction date because the voided entries are excluded from active calculations. Audit views and exports retain the original and replacement relationship.

## 5. Financial dates, periods, and timezones

### 5.1 Date meanings

- `transaction_date` is the user-visible economic date and drives account history, budgets, dashboard metrics, and reports.
- `posted_date` is the institution or statement settlement date and drives reconciliation eligibility. It is null while pending and required when posted.
- Manual transactions default `posted_date` to `transaction_date` when posted.
- Imports preserve every supplied source date. The mapped transaction date remains user-reviewable before confirmation.
- `created_at`, `updated_at`, and audit timestamps describe system events, not financial periods.

Financial dates are database `DATE` values and MUST NOT shift when a user or server changes timezone. Event timestamps are stored in UTC.

### 5.2 Workspace timezone

Each workspace uses a valid IANA timezone. It determines the meaning of “today,” default form dates, timestamp display, and when scheduled jobs consider a local day complete. Changing the workspace timezone never rewrites stored financial dates or historical timestamps.

### 5.3 MVP periods

MVP budgets and monthly reports use calendar months. `fiscal_month_start_day` MUST remain `1` in MVP; non-calendar fiscal periods are deferred.

Public API date filters use inclusive `date_from` and `date_to` values. Internally, period queries SHOULD use a half-open interval:

```text
start_date <= transaction_date < day_after_end_date
```

An as-of balance includes active transactions through the end of the requested financial date. Leap years and variable month lengths follow the Gregorian calendar.

## 6. Currency, precision, and rounding

- Philippine peso (`PHP`) is the only supported workspace base currency in MVP. Every posted entry uses `PHP`; multi-currency and foreign-exchange accounting remain deferred.
- Monetary values use decimal arithmetic and are stored as `NUMERIC(19,4)` or an equivalent exact type. Binary floating point is prohibited.
- API money values are base-10 strings, such as `"-82.40"`, never JSON floating-point numbers.
- Philippine peso values are quantized to `0.01` (one centavo) before validation and posting.
- Internal derived calculations use at least 28 decimal digits and do not round intermediate values unless the formula explicitly requires allocation.
- Final monetary outputs use decimal round-half-to-even at the workspace currency precision.
- Negative zero is normalized to positive zero.
- A posting outside the `NUMERIC(19,4)` range or with unsupported currency precision fails validation rather than truncating.

User-entered splits must already sum exactly after currency quantization. A future proportional-allocation feature MUST use a deterministic largest-remainder allocation so the allocated minor units equal the source amount; it is not part of MVP.

## 7. Reconciliation semantics

A reconciliation belongs to one account and records statement start/end dates, statement ending balance, selected account entries, creator, completion time, and audit history.

1. The statement balance is entered in the account's displayed sign and converted to raw ledger sign by the domain.
2. Only posted, non-void account entries with `posted_date <= statement_end_date` are eligible.
3. The calculated statement balance is the sum of previously reconciled account entries plus the currently selected eligible entries.
4. The raw difference is `statement_raw_balance - calculated_raw_balance`.
5. Finalization is allowed only when the difference equals zero at the workspace currency precision.
6. Finalization links each selected account entry to the reconciliation; it does not mutate the transaction's posting status.

The application never creates an automatic adjustment merely to force a zero difference. Users must find missing/incorrect transactions or explicitly post a reasoned adjustment.

Statement end dates for an account must move forward. Only the latest completed reconciliation for an account may be undone in MVP. Undo is audited, removes that reconciliation's entry links, and does not change or delete the underlying posted transactions.

## 8. Reporting formulas

Unless stated otherwise, reports include category entries owned by posted, non-void transactions whose `transaction_date` is in the requested inclusive period. Pending transactions appear only as a separately labeled preview and never in official totals.

### 8.1 Net worth

```text
net_worth(as_of) = sum(raw_balance(account, as_of))
                   for accounts where include_in_net_worth = true
```

Asset raw balances are normally positive and liability raw balances normally negative. Archived accounts remain included unless `include_in_net_worth` is explicitly disabled; archiving only hides routine UI. Manual valuation rules in section 1.3 apply.

### 8.2 Income and expense

```text
income(period)  = -1 × sum(income-category entry amounts)
expense(period) =      sum(expense-category entry amounts)
```

Refunds and reversals reduce these totals and can make a period total negative. Transfers, system-equity adjustments, and opening balances have no category entries and therefore contribute zero.

### 8.3 Cash flow

```text
cash_flow(period) = income(period) - expense(period)
```

Cash flow is operating categorized cash flow, not the raw change in bank balances. Transfers, loan proceeds, principal payments, opening balances, and uncategorized system adjustments are excluded. Interest and other categorized fees are included.

### 8.4 Savings rate

```text
savings_rate(period) = cash_flow(period) / income(period)
```

The API returns a decimal ratio, not a formatted percentage. If income is zero or negative, savings rate is `null` with reason `non_positive_income`; it is never reported as zero or infinity. The value is not capped, so refunds or corrections can produce results above 100% or below -100%.

### 8.5 Category spending

Category spending is the net sum of expense-category entries for the selected category and period. A parent-category report sums its active and archived descendants by stable category ID. Transfers are never categories. Negative values caused by refunds remain visible.

### 8.6 Burn rate

MVP monthly burn rate is the average net expense across as many as the three most recently completed calendar months before the as-of month:

```text
monthly_burn_rate = max(0, sum(monthly net expense) / month_count)
```

- The current partial month is excluded.
- The window starts no earlier than the month containing the first posted transaction, and includes zero-expense complete months inside that window.
- `month_count` is between one and three. If there is no complete month, the result is `null` with reason `insufficient_history`.
- All expense categories are included in MVP. Exceptional-category exclusions are deferred until a configuration model is accepted.
- Refunds reduce net expense. The final aggregate is floored at zero so burn rate cannot be negative; underlying monthly expense values remain available for explanation.

Every aggregate response MUST include base currency, date range, inclusion rules, and a link/filter definition that reproduces its supporting transactions.

## 9. Budget semantics

MVP budget lines apply only to active, non-system leaf expense categories, preventing parent and child lines from double-counting the same allocation. Official actuals include posted entries; pending actuals MAY be shown separately. Uncategorized expense is reported as unbudgeted spending rather than assigned to a budget line.

For category `C` and calendar month `M`:

```text
actual(C, M) = sum(expense entry amounts for C in M)

available(C, M) = planned(C, M)
                + rollover(C, M)
                - actual(C, M)
```

Refunds reduce actual and may make it negative. Available is never clamped.

Rollover rules:

- The first budgeted month has rollover `0`.
- If rollover is disabled, rollover is `0`.
- If enabled without a cap, rollover equals the previous month's available amount, including a negative overspend.
- If enabled with cap `K`, positive rollover is `min(previous_available, K)`; negative rollover carries in full and is not capped.
- A cap must be zero or positive and use workspace currency precision.
- Finalized historical budget results are not recomputed silently after category or rule changes; any later recalculation is explicit and audited.

Example with `₱500` planned:

| Prior available | Rollover setting | Current actual | Current available |
|---:|---|---:|---:|
| `₱100` | Disabled | `₱450` | `₱50` |
| `₱100` | Enabled, no cap | `₱450` | `₱150` |
| `₱100` | Enabled, `₱60` cap | `₱450` | `₱110` |
| `-₱75` | Enabled, `₱60` cap | `₱450` | `-₱25` |

## 10. Required implementation consequences

Acceptance of this document requires the later schema and services to preserve these decisions:

- Use debit-positive signed entries whose transaction sum is zero.
- Represent system-equity purposes explicitly rather than as user categories.
- Treat ledger postings as the only source of opening balances.
- Keep transaction posting status (`pending`, `posted`, `void`) separate from per-account-entry reconciliation.
- Route all sign conversion, balance calculation, posting, correction, reconciliation, metric, and budget logic through the owning domain services.
- Generate executable fixtures from every canonical example before dashboard or import features consume the ledger.

These are accepted product semantics, not accepted technical ADRs. The future ledger-entry ADR and data model must cite this document. Changing these behaviors requires an explicit product-semantics revision and any corresponding ADR update.

## 11. Product-owner acceptance record

Approval confirms all of the following choices:

- [x] Debit-positive storage with negative raw liability balances and positive displayed amounts owed
- [x] System-equity offsets for opening balances and non-operating adjustments
- [x] Visible system uncategorized categories that remain part of operating reports
- [x] Per-account-entry reconciliation, separate from transaction posting status
- [x] `transaction_date` for reports/budgets and `posted_date` for reconciliation
- [x] Calendar-month MVP periods and `fiscal_month_start_day = 1`
- [x] Philippine peso (`PHP`) as the MVP base currency with `0.01` centavo precision, exact decimals, and round-half-to-even outputs
- [x] Refunds reduce expense without being clamped; burn rate alone is floored at zero
- [x] Savings rate is null when income is zero or negative
- [x] Negative budget rollover carries in full while a cap limits only positive rollover
- [x] All canonical examples, lifecycle transitions, and correction rules above

Acceptance follow-up:

- [x] Record acceptance and close the applicable Milestone 0 roadmap items.
- [x] Align the preliminary architecture model with per-entry reconciliation.
- [ ] Create and accept the modular-monolith, ledger-entry, and PostgreSQL ADRs before scaffolding relies on them.
- [ ] Turn every example in section 3 and every formula boundary in sections 6–9 into framework-independent test fixtures during the ledger milestone.
