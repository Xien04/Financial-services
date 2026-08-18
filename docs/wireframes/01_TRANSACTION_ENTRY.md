# Wireframe 01 — Transaction Entry

| Field | Value |
|---|---|
| Status | Accepted |
| Version | 1.0 |
| Accepted by | Brenson Go on 2026-08-18 |
| Parent | [Product wireframes](../PRODUCT_WIREFRAMES.md) |
| Financial rules | [Financial semantics](../FINANCIAL_SEMANTICS.md) |

## 1. Goal and entry points

The workflow lets a user enter or correct financial activity without understanding ledger signs. It supports expense, income, transfer, split expense, refund, and balance adjustment scenarios in Philippine pesos.

Entry points:

- **Add transaction** from Dashboard, Transactions, or Account detail
- **Add missing transaction** from Reconciliation
- **Edit** from transaction detail
- **Record refund** from an existing expense
- **Correct transaction** from an unreconciled posted transaction

The originating page and active account are preserved so **Cancel** and successful completion return to useful context.

## 2. Desktop — standard expense

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Transactions / Add transaction                                              │
│ Add transaction                                               [Close]       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Type                                                                        │
│ (●) Expense   ( ) Income   ( ) Transfer   ( ) Adjustment                    │
│                                                                             │
│ Account *                         Amount *                                   │
│ [BPI Checking • 1234       ▾]     [₱ 1,250.00                        ]       │
│                                                                             │
│ Payee *                           Category *                                 │
│ [Meralco                     ]     [Utilities                         ▾]       │
│                                                                             │
│ Transaction date *                Posting status                            │
│ [2026-08-18                 ]      (●) Posted   ( ) Pending                  │
│                                                                             │
│ Posted date *                     [ ] Split into categories                 │
│ [2026-08-18                 ]                                                  │
│                                                                             │
│ Tags                               Notes                                     │
│ [Add tags                    ▾]     [Optional details…                  ]     │
│                                                                             │
│ Effect                                                                      │
│ BPI Checking decreases by ₱1,250.00. Utilities expense increases by        │
│ ₱1,250.00.                                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                    [Cancel] [Save posted]   │
└─────────────────────────────────────────────────────────────────────────────┘
```

Behavior:

- Amount accepts a positive magnitude with at most two centavo digits.
- The account/category effect summary updates before saving and uses human language.
- Selecting **Pending** hides Posted date and changes the primary action to **Save pending**.
- Manual posted transactions default Posted date to Transaction date; either date remains editable before save.
- Uncategorized Expense is available and visibly labeled for later review.
- Save is idempotent and disabled while the request is in progress.

## 3. Type variations

| Type | Fields replacing expense category | Effect summary |
|---|---|---|
| Income | Income category, including Uncategorized Income | Account increases; selected income increases |
| Transfer | From account and To account | One account decreases, the other increases; income and expense unchanged |
| Refund | Original transaction where known and refund destination | Destination increases; original expense category decreases |
| Adjustment | Account, increase/decrease choice, required reason | Account/net worth changes; operating income and expense unchanged |

The amount field remains a positive magnitude. Type-specific direction controls determine the effect. Transfer accounts must differ. Refund and transfer recognition must be explicit rather than inferred from sign alone.

### 3.1 Transfer variation

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Type: ( ) Expense  ( ) Income  (●) Transfer  ( ) Adjustment                 │
│                                                                             │
│ From account *                      To account *                             │
│ [BPI Checking • 1234         ▾]     [BDO Savings • 9876              ▾]     │
│                                                                             │
│ Amount *                            Transaction date *                       │
│ [₱ 5,000.00                   ]     [2026-08-18                       ]       │
│                                                                             │
│ Effect                                                                      │
│ Move ₱5,000.00 from BPI Checking to BDO Savings. Net worth, income,        │
│ expense, cash flow, and budgets do not change.                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

Credit-card payments use this transfer variation: checking is the source and the credit card is the destination.

### 3.2 Adjustment variation

```text
Account *             Direction *              Amount *
[BPI Checking     ▾]  (●) Increase ( ) Decrease [₱ 25.00]

Reason *
[Correction after reviewing statement history                         ]

Warning: Adjustments change account balance and net worth but do not count as
income or expense. Use Income or Expense if that is what actually occurred.
```

## 4. Split expense

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Amount: ₱1,250.00                  Split total: ₱1,100.00                   │
│                                    Remaining:   ₱150.00                     │
│                                                                             │
│ Category                                      Amount                        │
│ [Groceries                              ▾]     [₱ 900.00]       [Remove]    │
│ [Household supplies                     ▾]     [₱ 200.00]       [Remove]    │
│ [+ Add split]                                                               │
│                                                                             │
│ Error: Allocate the remaining ₱150.00 before saving.                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

Rules:

- Split rows require a category and positive amount.
- The running split total and remaining amount are announced after every change.
- Saving is disabled until the quantized split total equals the transaction amount exactly.
- Duplicate categories are allowed but the interface offers to combine them.
- Removing a row never silently reallocates its amount.
- Switching away from Expense asks before discarding split rows.

## 5. Refund flow

When launched from an expense, the original payee, category, account, amount available for reference, and original date appear above the refund form.

```text
Original: SM Supermarket • Groceries • ₱1,200.00 • 2026-08-10

Refund destination *                Refund amount *
[BPI Checking • 1234          ▾]    [₱ 300.00]

Transaction date *                  Reference
[2026-08-18]                        Linked to original transaction

Effect: Groceries expense decreases by ₱300.00 and checking increases by
₱300.00. A refund may exceed spending in the selected report period.
```

A standalone refund requires the user to choose its expense category. The interface does not reject a refund that exceeds the original transaction, but it warns when the amount is greater and requires confirmation.

## 6. Edit, correction, and void states

| Existing state | Available behavior |
|---|---|
| Pending | Edit fields directly, post, or void |
| Posted and unreconciled | View, correct through atomic void-and-replace, or void |
| Posted with any reconciled account entry | View; correction and void are blocked with guidance to undo the latest reconciliation or create a current adjustment |
| Void | Read-only audit view with link to replacement when present |

Correction confirmation:

```text
Correct posted transaction?

The original transaction and entries will remain in audit history as void.
A corrected replacement will be posted atomically.

[Cancel] [Void original and post correction]
```

Void confirmation names the transaction, amount, date, and reporting consequence. It never uses the word “delete” as the primary action.

## 7. Validation and failure behavior

| Condition | Response |
|---|---|
| Missing required value | Inline error and error-summary link to field |
| More than two centavo digits | Explain PHP precision; do not silently truncate |
| Zero amount | Reject with “Amount must be greater than ₱0.00” |
| Same transfer accounts | Reject and focus To account |
| Split does not balance | Show exact remaining or overallocated amount |
| Pending transaction has posted date | Hide/clear posted date only after user confirms if manually entered |
| Reconciled entry correction | Block and link to the applicable account reconciliation |
| Duplicate submit/retry | Return the original durable result without another posting |
| Network/server error | Preserve every field and offer Retry |
| Stale transaction during correction | Reload authoritative version and explain the conflict |

## 8. Mobile

```text
┌──────────────────────────────┐
│ Back        Add transaction  │
├──────────────────────────────┤
│ Type                         │
│ [Expense ▾]                  │
│                              │
│ Account *                    │
│ [BPI Checking • 1234 ▾]      │
│                              │
│ Amount *                     │
│ [₱ 1,250.00]                 │
│                              │
│ Payee *                      │
│ [Meralco]                    │
│                              │
│ Category *                   │
│ [Utilities ▾]                │
│                              │
│ Date *        Status         │
│ [2026-08-18]  [Posted ▾]     │
│                              │
│ Effect                       │
│ Checking -₱1,250.00          │
│ Utilities +₱1,250.00         │
├──────────────────────────────┤
│ [Cancel] [Save posted]       │
└──────────────────────────────┘
```

- The form is one column; paired date/status fields may share a row only when readable.
- Split rows become stacked category/amount groups.
- The effect summary stays immediately above the sticky action region.
- Back prompts only when entered data would be lost.
- The numeric keyboard may open for amount, but the field remains accessible to hardware keyboards and assistive technology.

## 9. Accessibility and keyboard behavior

- Type selection is a labeled radio group on desktop and an equivalent labeled select on constrained mobile layouts.
- Tab order follows visual order; Enter does not submit while focus is inside split editing.
- The first invalid field receives focus after submission; the error summary is announced first.
- Add/remove split actions identify their row and category.
- Currency symbol is visually present while the accessible value includes “Philippine pesos.”
- The effect summary uses text, not arrows or color alone.
- Success returns focus to the new or corrected transaction heading.

## 10. Acceptance scenarios

- [x] Record a posted cash/checking expense.
- [x] Record posted income and Uncategorized Income.
- [x] Save and later post a pending transaction.
- [x] Split an expense exactly across multiple categories.
- [x] Transfer between two different asset accounts.
- [x] Pay a credit card without creating an expense.
- [x] Record a linked and standalone refund.
- [x] Record a reasoned non-operating balance adjustment.
- [x] Correct an unreconciled posted transaction through void-and-replace.
- [x] Block correction of a reconciled account entry with actionable guidance.
- [x] Complete each supported action using keyboard-only desktop navigation.
- [x] Complete the happy paths at a 320 px mobile width without lost fields or meaning.
