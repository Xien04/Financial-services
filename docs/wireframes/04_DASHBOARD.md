# Wireframe 04 — Dashboard

| Field | Value |
|---|---|
| Status | Proposed for product-owner acceptance |
| Parent | [Product wireframes](../PRODUCT_WIREFRAMES.md) |
| Financial rules | [Financial semantics](../FINANCIAL_SEMANTICS.md) |

## 1. Goal

The dashboard provides an explainable Philippine-peso overview and a direct path from every aggregate to its supporting transactions. It does not forecast, provide financial advice, or hide inclusion rules.

MVP dashboard measures:

- Net worth
- Cash flow
- Monthly burn rate
- Savings rate
- Income versus expense
- Spending by category
- Pending activity, clearly separated from official totals

## 2. Desktop overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Dashboard                                              [+ Add transaction]  │
│ Period [August 2026 ▾]  Accounts [All included ▾]  Currency PHP             │
├─────────────────────────────────────────────────────────────────────────────┤
│ Net worth              Cash flow             Burn rate       Savings rate  │
│ ₱1,245,800.00         ₱12,450.00            ₱34,200/month   19.4%         │
│ As of Aug 31           Aug 1–31              3 full months   Aug 1–31      │
│ [View accounts]        [View transactions]   [View expenses] [View detail] │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ Net worth trend                      │ Income vs expense                    │
│                                      │                                      │
│ ₱1.30m ┤                 ╭────        │ Income   ₱64,200 █████████████      │
│ ₱1.20m ┤        ╭────────╯            │ Expense  ₱51,750 ██████████         │
│ ₱1.10m ┤────────╯                     │                                      │
│         May  Jun  Jul  Aug            │ [View supporting transactions]       │
│ [View account balances]               │                                      │
├──────────────────────────────────────┼──────────────────────────────────────┤
│ Spending by category                 │ Pending activity                     │
│ Housing       ₱18,000 █████████      │ 4 transactions • net -₱3,250        │
│ Food           ₱9,600 █████           │ Not included in official totals      │
│ Utilities      ₱4,250 ██              │ [Review pending transactions]         │
│ Transport      ₱3,900 ██              │                                      │
│ [View all category spending]          │                                      │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

Every card and visualization includes its effective date/range, `PHP`, and a drill-down action. The layout uses one page heading; the metric labels become the accessible headings for their regions.

## 3. Global controls

### 3.1 Period

- Net worth uses an **As of** date.
- Cash flow, savings rate, income/expense, and category spending use the selected inclusive date range.
- Burn rate uses its accepted trailing complete-month definition and states the actual months used.
- Presets include Current month, Previous month, Year to date, and Custom range.
- Calendar-month MVP rules apply; no fiscal or multi-currency option appears.

### 3.2 Accounts

- Default: all accounts where `include_in_net_worth` is true for net-worth metrics and all relevant accounts for transaction-derived operating metrics.
- The account filter names excluded accounts and identifies when a metric uses a different inclusion rule.
- Archived accounts remain included when their inclusion flag is true.
- Changing account selection updates every affected region together and updates the disclosed inclusion text.

### 3.3 Currency

`Currency PHP` is displayed as non-interactive context. MVP does not show a currency selector.

## 4. Metric cards and states

### 4.1 Net worth

```text
Net worth
₱1,245,800.00
As of August 31, 2026 • 6 included accounts
[View account balances]
```

- Value equals the sum of raw balances for included accounts under accepted asset/liability signs.
- Manual valuations use the latest eligible authoritative snapshot plus subsequent entries.
- Drill-down opens an account-balance breakdown, then account activity.

### 4.2 Cash flow

```text
Cash flow
₱12,450.00
Income ₱64,200.00 − Expense ₱51,750.00
August 1–31 • Transfers excluded
[View supporting transactions]
```

The drill-down applies the same period and account filters and presents income and expense category entries. Transfers, loan principal, loan proceeds, opening balances, and system-equity adjustments remain excluded.

### 4.3 Burn rate

```text
Monthly burn rate
₱34,200.00
Average net expense • May–July 2026
Current partial month excluded
[View monthly expenses]
```

Insufficient history:

```text
Monthly burn rate
Not available yet
One complete calendar month is required.
[View calculation rules]
```

The interface does not substitute zero for unavailable history. The final burn-rate value is floored at zero, while underlying negative monthly expense remains visible in drill-down.

### 4.4 Savings rate

```text
Savings rate
19.4%
Cash flow ₱12,450.00 ÷ Income ₱64,200.00
August 1–31
[View supporting transactions]
```

Non-positive income:

```text
Savings rate
Not available
Savings rate requires income greater than ₱0.00 for this period.
[View income and expenses]
```

Values are not capped at 100% or -100%.

## 5. Visualizations and drill-down

### 5.1 Net-worth trend

- X-axis shows financial dates; Y-axis shows Philippine pesos.
- The selected As-of date is the final point.
- The chart distinguishes asset total, liability total, and net worth only if three series remain readable; otherwise the MVP defaults to one net-worth line with a tabular account breakdown.
- Manual snapshots are identifiable in detail, not through decorative markers required to interpret the line.
- Selecting a point opens the account balance composition for that date.
- An accessible table lists date, assets, liabilities, and net worth.

### 5.2 Income versus expense

- Two directly labeled values use the same period and account filters.
- Refunds reduce the corresponding net expense or income result.
- Selecting Income or Expense opens the matching filtered transaction set.
- Transfers never appear as a third bar or hidden component.
- An accessible table contains measure, value, period, and inclusion rules.

### 5.3 Spending by category

- Shows net expense for the leading categories with an explicit **View all** path.
- Uncategorized Expense is visible and labeled **Needs review** when non-zero.
- Negative category spending from refunds remains visible and is not clamped.
- Parent totals sum stable descendant category IDs; the drill-down discloses descendants.
- Selecting a category opens its supporting posted transactions with the dashboard filters preserved.
- An accessible table contains category, amount, share of net expense when the denominator is positive, and transaction count.

## 6. Drill-down transaction view

```text
Transactions supporting Cash flow
August 1–31, 2026 • PHP • All relevant accounts

Formula: categorized income minus categorized expense. Transfers, opening
balances, loan principal/proceeds, and system adjustments excluded.

[Income and expense ▾] [All accounts ▾] [Search…]

Date       Payee             Account              Category       Amount
08/18/26   Payroll           BPI Checking • 1234  Salary       +₱50,000.00
08/17/26   Meralco           BPI Checking • 1234  Utilities     -₱1,250.00

Displayed total: ₱12,450.00
```

Requirements:

- The drill-down is reproducible from explicit filters; it is not a separate unexplained query.
- The aggregate value and displayed supporting total reconcile under the disclosed formula.
- Pagination does not change the total.
- Users can open a transaction detail and return without losing the dashboard/drill-down context.

## 7. Pending activity

Pending transactions are excluded from official metrics and appear in a separate region:

```text
Pending activity
4 transactions • net account movement -₱3,250.00
Not included in net worth trend, cash flow, burn rate, savings rate, spending,
budgets, goals, or reconciliation.
[Review pending transactions]
```

The pending net movement is contextual and must not be visually added to the official cash-flow value. If no pending activity exists, the region may collapse to a short “No pending transactions” line.

## 8. Empty, partial, and error states

### New workspace

```text
Start your financial overview

Add an account and opening balance, enter a transaction, or import a CSV to
build your dashboard.

[Add account] [Import CSV]
```

No metric displays `₱0.00` when no underlying data exists; use **No data yet**.

### Partial data

- Net worth can display when accounts exist even if operating metrics have no period activity.
- Burn rate and savings rate use their specific null explanations.
- A category chart with only Uncategorized Expense still renders that category and review action.
- Manual-valuation accounts with stale snapshots identify the snapshot date without inventing a new value.

### Region error

One failed metric or chart does not blank the entire dashboard. The affected region states what failed and offers Retry. Previous values are labeled stale if temporarily retained. Filters remain operable only when their result can be refreshed consistently.

## 9. Mobile

```text
┌──────────────────────────────┐
│ Dashboard       [+ Add]      │
│ [August 2026 ▾] [Accounts ▾] │
│ PHP                          │
├──────────────────────────────┤
│ Net worth                    │
│ ₱1,245,800.00               │
│ As of Aug 31                 │
│ [View accounts]              │
├──────────────────────────────┤
│ Cash flow                    │
│ ₱12,450.00                  │
│ Income ₱64,200               │
│ Expense ₱51,750              │
│ [View transactions]          │
├──────────────────────────────┤
│ Burn rate       Savings rate │
│ ₱34,200/mo      19.4%       │
├──────────────────────────────┤
│ Net worth trend              │
│ [Responsive chart]           │
│ [View data table]            │
├──────────────────────────────┤
│ Spending by category         │
│ [Directly labeled bars]      │
│ [View all]                   │
├──────────────────────────────┤
│ Pending: 4 transactions      │
│ [Review]                     │
└──────────────────────────────┘
```

- Regions stack in decision order: net worth, cash flow, rate context, trend, category spending, pending activity.
- Period and account filters remain at the top and wrap without horizontal page scrolling.
- Charts reduce labels rather than shrinking text; accessible tables remain available.
- Metric cards do not become a horizontally scrolling carousel.
- Drill-down opens the responsive Transaction list with filters visible.

## 10. Accessibility

- Dashboard regions use descriptive headings and a predictable reading order.
- Each chart has an accessible summary and equivalent table.
- Chart selection is keyboard operable and never the only way to open drill-down.
- Positive/negative amounts include explicit signs and are not distinguished only by color.
- Null values state why the metric is unavailable.
- Filter changes announce that dashboard values updated and preserve focus.
- Loading indicators do not replace headings, preventing layout and context loss.
- Abbreviated visual values such as `₱1.25M` expose the full accessible amount.

## 11. Acceptance scenarios

- [ ] Display PHP net worth with asset and liability contributions handled correctly.
- [ ] Display cash flow as categorized income minus expense with transfers excluded.
- [ ] Explain the exact burn-rate months and insufficient-history state.
- [ ] Display savings rate and the non-positive-income null state.
- [ ] Keep pending transactions separate from official metrics.
- [ ] Preserve negative category spending caused by refunds.
- [ ] Surface Uncategorized Expense as needing review.
- [ ] Drill every aggregate down to reproducible supporting records.
- [ ] Preserve period/account context when opening and returning from a transaction.
- [ ] Provide equivalent tables for every chart.
- [ ] Show a useful new-workspace state without fabricated zeroes.
- [ ] Recover a failed region without obscuring unaffected metrics.
- [ ] Navigate all controls and drill-down actions using keyboard only.
- [ ] Retain readable hierarchy and complete meaning at a 320 px mobile width.
