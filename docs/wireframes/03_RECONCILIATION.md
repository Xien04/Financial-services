# Wireframe 03 — Account Reconciliation

| Field | Value |
|---|---|
| Status | Accepted |
| Version | 1.0 |
| Accepted by | Brenson Go on 2026-08-18 |
| Parent | [Product wireframes](../PRODUCT_WIREFRAMES.md) |
| Financial rules | [Financial semantics](../FINANCIAL_SEMANTICS.md) |

## 1. Goal and entry point

Reconciliation verifies one account against one statement without creating automatic balancing activity. It links selected account-side ledger entries to the reconciliation; it never changes transaction posting status or automatically reconciles the other side of a transfer.

Entry point: **Reconcile** on an eligible account detail page.

Accounts with no completed reconciliation start from their opening history. Accounts with history show the latest completed statement date and balance.

## 2. Step 1 — Statement details

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Accounts / BPI Checking / Reconcile                                         │
│ Reconcile BPI Checking • 1234                                               │
│ 1 Statement details ── 2 Match activity ── 3 Complete                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Last reconciliation                                                        │
│ 2026-07-31 • Ending balance ₱42,180.25                                     │
│                                                                             │
│ Statement start date *              Statement end date *                    │
│ [2026-08-01]                        [2026-08-31]                            │
│                                                                             │
│ Statement ending balance *                                                  │
│ [₱ 38,925.75]                                                              │
│                                                                             │
│ Enter the balance exactly as displayed on the statement. Liability account  │
│ balances use the positive amount owed; the application converts signs.      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                    [Cancel] [Match activity]│
└─────────────────────────────────────────────────────────────────────────────┘
```

Rules:

- Statement end date must follow the latest completed end date for the account.
- Start date defaults to the day after the latest statement end and remains reviewable.
- Statement balance uses account-native display signs and PHP precision.
- A new reconciliation cannot overlap an existing completed reconciliation.
- Statement details remain visible and editable until completion; changing them recomputes eligibility and selection.

## 3. Step 2 — Match activity

### 3.1 Desktop

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Reconcile BPI Checking • 1234                     Statement ends 2026-08-31│
├──────────────────────────────────────────────┬──────────────────────────────┤
│ [Search activity…] [All eligible ▾]          │ Reconciliation summary       │
│                                              │                              │
│ Sel Posted    Description          Amount    │ Statement balance            │
│ [x] 08/02/26  Payroll          +₱50,000.00  │ ₱38,925.75                  │
│ [x] 08/03/26  Rent             -₱18,000.00  │                              │
│ [x] 08/05/26  Meralco           -₱1,250.00  │ Previously reconciled        │
│ [ ] 08/29/26  Transfer          -₱5,000.00  │ ₱42,180.25                  │
│ [ ] 08/31/26  Grocery             -₱900.00  │                              │
│                                              │ Selected activity            │
│ Pending (not eligible): 2                    │ -₱3,254.50                  │
│ [View pending activity]                      │                              │
│                                              │ Calculated balance           │
│ Showing 32 eligible account entries          │ ₱38,925.75                  │
│                                              │                              │
│                                              │ Difference                   │
│                                              │ ₱0.00 — Ready to complete   │
│                                              │                              │
│                                              │ [Add missing transaction]    │
│                                              │ [Record explicit adjustment] │
├──────────────────────────────────────────────┴──────────────────────────────┤
│                                           [Back] [Complete reconciliation]  │
└─────────────────────────────────────────────────────────────────────────────┘
```

Summary formulas:

```text
calculated balance = previously reconciled account entries
                   + currently selected eligible entries

difference = statement raw balance - calculated raw balance
```

The interface displays native account signs while the domain compares raw signs. Finalization is enabled only when the difference equals `₱0.00` after accepted PHP quantization.

### 3.2 Entry behavior

- Eligibility requires a posted, non-void account entry with Posted date on or before the statement end.
- Entries already linked to an earlier reconciliation appear in the previous balance, not in the selectable list.
- A transfer leg is selected only for this account. Its other account leg remains independently reconcilable.
- Each row exposes Transaction date, Posted date, payee/description, account-side amount, category/type, and source on expansion.
- Selecting a row updates the summary immediately and announces the new difference.
- **Select all visible** may exist only when its scope is explicit and it never includes filtered-out or ineligible entries silently.
- Pending and void activity is never selectable. Pending activity may be viewed separately for troubleshooting.

## 4. Difference states

### Balanced

```text
Difference
₱0.00
Ready to complete
```

The primary completion action is enabled.

### Under or over

```text
Difference
₱1,250.00
The selected activity does not match the statement.

[Find by amount] [Add missing transaction] [Record explicit adjustment]
```

The UI never offers **Auto-adjust**, **Force complete**, or a preselected balancing transaction. An explicit adjustment opens Transaction Entry with the account, date range, and required-reason variation; returning refreshes authoritative entries.

### Invalidated while open

If another session changes an eligible transaction, show:

```text
Activity changed while this reconciliation was open.
Review the refreshed entries and difference before completing.

[Refresh and review]
```

Selections are reapplied only to still-eligible, unchanged entry IDs. Removed or changed entries are identified.

## 5. Completion confirmation

```text
Complete reconciliation?

Account                 BPI Checking • 1234
Statement period        2026-08-01 to 2026-08-31
Statement balance       ₱38,925.75
Selected entries        32
Difference              ₱0.00

Selected account entries will be linked to this reconciliation. Transactions
remain posted; the other side of a transfer is not reconciled automatically.

[Cancel] [Complete reconciliation]
```

Completion is idempotent. If the request outcome is uncertain, retrying returns the same completed reconciliation rather than adding another record.

## 6. Completion receipt

```text
Reconciliation complete

BPI Checking • 1234
Statement ending 2026-08-31
Ending balance ₱38,925.75
32 account entries reconciled
Completed by Brenson Go on 2026-08-18 at 14:45

[Return to account] [View reconciliation]
```

The account detail displays the new last-reconciled date/balance and distinguishes posted-but-unreconciled activity from reconciled entries.

## 7. History and undo latest

```text
Reconciliation history

Statement end   Ending balance   Entries   Completed by       Action
2026-08-31      ₱38,925.75      32        Brenson Go         Undo latest
2026-07-31      ₱42,180.25      28        Brenson Go         View
```

Only the latest completed reconciliation exposes **Undo latest**.

Undo confirmation:

```text
Undo the latest reconciliation?

32 account entries will return to posted-but-unreconciled state. No transaction
or ledger entry will be changed or deleted. This action is recorded in audit
history.

[Cancel] [Undo reconciliation]
```

Older reconciliations remain read-only. A transaction with a reconciled entry cannot be voided or corrected until the affected latest reconciliation is undone, or a current-period adjustment is recorded.

## 8. Liability account variation

For a credit card or loan:

- Statement balance is entered and displayed as the positive amount owed.
- Charges increase displayed amount owed; payments and credits decrease it.
- The reconciliation summary converts the display amount to the accepted raw liability sign internally.
- Labels say **Amount owed** where this prevents ambiguity.
- Overpaid cards may show a negative displayed amount (credit); the UI does not clamp it.

## 9. Empty and error states

| State | Behavior |
|---|---|
| No eligible entries | Explain date/status eligibility and offer Back or Add transaction |
| No prior reconciliation | Use opening history as the starting point and explain that this is the first statement |
| Missing opening activity | Difference remains visible; offer Add missing transaction or explicit adjustment |
| Completion conflict | Preserve selections, reload the latest account state, and require review |
| Server/network error | Preserve statement details and selected entry IDs; provide Retry |
| Undo blocked | Explain that only the latest reconciliation can be undone and link to it |

## 10. Mobile

```text
┌──────────────────────────────┐
│ Back    Reconcile BPI        │
│ Step 2 of 3                  │
├──────────────────────────────┤
│ Difference          ₱0.00   │
│ Statement      ₱38,925.75   │
│ Calculated     ₱38,925.75   │
├──────────────────────────────┤
│ [Search activity…]           │
│                              │
│ [x] Payroll                  │
│     Posted 08/02/26          │
│     +₱50,000.00             │
│                              │
│ [x] Rent                     │
│     Posted 08/03/26          │
│     -₱18,000.00             │
│                              │
│ Pending, not eligible: 2     │
├──────────────────────────────┤
│ [Complete reconciliation]    │
└──────────────────────────────┘
```

- The difference summary remains sticky above the activity cards, not over them.
- Each card is one checkbox target with an expandable accessible detail region.
- Statement and calculated balances remain visible whenever selection changes.
- Completion confirmation is a full-width dialog/sheet with the same facts as desktop.
- Long lists paginate or load in stable batches without losing selection.

## 11. Accessibility

- Statement fields and balance instructions identify asset versus liability meaning.
- The selectable activity uses a semantic table on desktop and labeled checkbox groups/cards on mobile.
- Every amount announces sign and “Philippine pesos.”
- Difference changes use a polite live announcement; rapid checkbox changes are coalesced.
- Balanced state uses text and not color alone.
- Disabled completion explains what must change.
- Confirmation and undo dialogs announce scope and audit consequence.
- Focus returns to the reconciliation summary after adding a missing transaction.

## 12. Acceptance scenarios

- [x] Start a first reconciliation and one following prior history.
- [x] Enter asset and liability statement balances without sign ambiguity.
- [x] Select only posted, non-void entries eligible by Posted date.
- [x] Keep pending entries visible but ineligible.
- [x] Reconcile only one account leg of a transfer.
- [x] Update and announce the difference after every selection.
- [x] Block completion at any non-zero centavo difference.
- [x] Add a missing transaction without losing reconciliation context.
- [x] Offer an explicit reasoned adjustment but never automatic adjustment.
- [x] Complete idempotently and show an auditable receipt.
- [x] Undo only the latest reconciliation without changing transactions.
- [x] Recover safely when eligible activity changes in another session.
- [x] Complete the happy path using keyboard-only desktop navigation.
- [x] Complete the happy path at a 320 px mobile width.
