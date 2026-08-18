# Wireframe 02 — CSV Import and Preview

| Field | Value |
|---|---|
| Status | Proposed for product-owner acceptance |
| Parent | [Product wireframes](../PRODUCT_WIREFRAMES.md) |
| Financial rules | [Financial semantics](../FINANCIAL_SEMANTICS.md) |

## 1. Goal and flow

The workflow stages a CSV file for inspection and explicit review before any ledger posting occurs.

```text
Upload → Map columns → Review → Confirm → Complete
```

Users may move backward without re-uploading while the staged import remains valid. Exiting asks whether to discard the staged job. No row writes directly to the ledger.

## 2. Step 1 — Upload

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Imports / New CSV import                                                    │
│ Import transactions                                                        │
│ 1 Upload ── 2 Map columns ── 3 Review ── 4 Confirm ── 5 Complete           │
├─────────────────────────────────────────────────────────────────────────────┤
│ Destination account *                                                       │
│ [BPI Checking • 1234                                                 ▾]     │
│                                                                             │
│ CSV file *                                                                  │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ Drop a CSV file here or [Choose file]                                  │ │
│ │ Accepted: .csv • Maximum configured upload size                        │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ Privacy: The file is staged for this import and retained according to the   │
│ documented import retention policy.                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                        [Cancel] [Inspect]   │
└─────────────────────────────────────────────────────────────────────────────┘
```

After inspection, show filename, row count, detected encoding, delimiter, headers, and any file-level warnings. The SHA-256 hash is stored for idempotency and audit but need not be displayed in the primary UI.

File errors distinguish unsupported type, excessive size, unreadable encoding, missing header, and structurally invalid content. A rejected file never creates import rows.

## 3. Step 2 — Map columns

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1 Upload ── 2 MAP COLUMNS ── 3 Review ── 4 Confirm ── 5 Complete           │
├─────────────────────────────────────────────────────────────────────────────┤
│ File: bpi-august-2026.csv        124 rows        Encoding: UTF-8            │
│                                                                             │
│ Canonical field        Source column             Sample values              │
│ Transaction date *     [Transaction Date    ▾]   08/18/2026, 08/17/2026    │
│ Posted date            [Posting Date        ▾]   08/19/2026, 08/18/2026    │
│ Payee/description *    [Description         ▾]   MERALCO, SM SUPERMARKET   │
│ Amount format *        (●) Single amount  ( ) Separate debit and credit     │
│ Amount *               [Amount              ▾]   -1250.00, 50000.00        │
│ External reference     [Reference Number    ▾]   481923, 481924             │
│ Notes                   [Not mapped          ▾]                               │
│                                                                             │
│ Date format             [MM/DD/YYYY          ▾]                              │
│ Decimal separator       [Period (1,234.56)   ▾]                              │
│                                                                             │
│ Preview normalization                                                     │
│ 08/18/2026 | MERALCO       | -1250.00 → 2026-08-18 | ₱1,250.00 expense     │
│ 08/17/2026 | PAYROLL       | 50000.00 → 2026-08-17 | ₱50,000.00 income     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                               [Back] [Validate and review]   │
└─────────────────────────────────────────────────────────────────────────────┘
```

Rules:

- Required mappings cannot target the same source column unless the selected amount format permits it.
- Separate debit and credit mode requires both columns and defines whether blanks or zeros mean no value.
- Sample normalization updates immediately and never changes the original staged values.
- The user sees whether type is a suggestion. Amount sign alone must not silently finalize transfer or refund classification.
- A saved mapping profile is deferred unless representative repeat files justify it; the wireframe leaves room for a future optional profile without exposing it in MVP.

## 4. Step 3 — Review

### 4.1 Desktop review table

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1 Upload ── 2 Map columns ── 3 REVIEW ── 4 Confirm ── 5 Complete           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 124 rows  |  112 ready  |  4 warnings  |  3 probable duplicates  | 5 errors│
│ [All states ▾] [Search payee…]                    [Resolve next issue]       │
│                                                                             │
│ Sel State       Date       Description       Amount       Type/Category     │
│ [x] Ready       08/18/26   MERALCO           -₱1,250.00   Expense/Utilities │
│ [ ] Exact dup.  08/18/26   MERALCO           -₱1,250.00   Skipped           │
│ [!] Review      08/17/26   TRANSFER           -₱5,000.00   Choose type       │
│ [!] Probable    08/16/26   SM SUPERMARKET     -₱900.00     Compare           │
│ [ ] Error       Invalid    CASH WITHDRAWAL    -₱2,000.00   Fix date          │
│                                                                             │
│ Selected: 112 rows                                       Total: ₱73,420.50  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                     [Back] [Review import]   │
└─────────────────────────────────────────────────────────────────────────────┘
```

The amount column may show an inflow/outflow sign for review, while editing uses a positive magnitude plus explicit type/direction. Table rows expose original source values on demand without replacing the normalized values.

### 4.2 Row editor

Selecting a row opens a side panel on desktop and a full screen on mobile:

```text
Row 18 of 124                         Source row 19

Original: 08/17/2026 | TRANSFER | -5000.00 | Ref 481923

Transaction date *  [2026-08-17]
Posted date          [2026-08-18]
Description *        [TRANSFER]
Amount               [₱5,000.00]
Type *                [Transfer ▾]
From account *        [BPI Checking • 1234 ▾]
To account *          [Choose account ▾]

[Skip row]                                      [Apply changes]
```

Edits affect normalized staging data only. The original row remains preserved for audit.

## 5. Duplicate review

### 5.1 Exact duplicate

An exact match with a stable external ID is automatically unselected and labeled **Exact duplicate — skipped**. The user may inspect the existing transaction and source reason but cannot accidentally select it as a new row without an explicit override flow. MVP may omit override if stable-ID uniqueness is authoritative.

### 5.2 Probable duplicate

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ Review probable duplicate                                                   │
├───────────────────────────────┬─────────────────────────────────────────────┤
│ Imported row                  │ Existing transaction                        │
│ 2026-08-16                    │ 2026-08-16                                  │
│ SM SUPERMARKET                │ SM Supermarket                              │
│ ₱900.00 expense              │ ₱900.00 expense                            │
│ BPI Checking • 1234           │ BPI Checking • 1234                         │
│ No external reference         │ Manual source                               │
├───────────────────────────────┴─────────────────────────────────────────────┤
│ Why flagged: same account, date, amount, and similar payee                  │
│                                                                             │
│ ( ) Skip imported row as duplicate                                          │
│ ( ) Import as a new transaction                                             │
│                                                                             │
│ [Previous]                                            [Save and next]       │
└─────────────────────────────────────────────────────────────────────────────┘
```

Every probable duplicate requires one visible disposition. There is no preselected choice. The decision and reviewer are retained with the import row.

## 6. Errors and warnings

| State | Meaning | Can confirm? |
|---|---|---|
| Ready | Valid and selected | Yes |
| Warning | Valid but needs awareness, such as uncategorized activity | Yes after acknowledgement where required |
| Needs review | Type, transfer destination, refund, or probable duplicate is unresolved | No |
| Exact duplicate | Stable match, automatically skipped and reported | Yes; row not posted |
| Error | Invalid date, amount, missing required value, or unsupported precision | No unless row is explicitly skipped |
| Skipped | User excluded row with recorded disposition | Yes; row not posted |

The workflow never hides valid rows because other rows are malformed. Filters and issue counts remain available until every selected row is confirmable.

## 7. Step 4 — Confirm

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1 Upload ── 2 Map columns ── 3 Review ── 4 CONFIRM ── 5 Complete           │
├─────────────────────────────────────────────────────────────────────────────┤
│ Import into BPI Checking • 1234                                             │
│                                                                             │
│ 112 transactions ready to post                          Net: ₱73,420.50     │
│   87 expenses                                                               │
│   20 income                                                                 │
│    5 transfers                                                              │
│                                                                             │
│ 12 rows will not post                                                       │
│    4 exact duplicates • 3 probable duplicates skipped • 5 invalid skipped  │
│                                                                             │
│ [x] I reviewed duplicate decisions and skipped rows.                        │
│                                                                             │
│ Posting is idempotent. Retrying this confirmed import will not create       │
│ another copy. The completed batch can be reversed with audit history kept.  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                             [Back to review] [Post import]   │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Post import** requires a final confirmation, becomes disabled after activation, and reports progress without allowing the user to submit another batch. If a bounded posting batch fails, the job shows exactly what committed and provides a safe resume path using the same idempotency identity.

## 8. Step 5 — Complete

```text
Import complete

112 transactions posted to BPI Checking • 1234
12 rows skipped
Import batch: BPI August 2026
Completed: 2026-08-18 14:32 workspace time

[View imported transactions] [Download completion report]
[Reverse this import]
```

Reversal explains that posted transactions will be voided through an audited batch operation; source rows and import history remain. Reversal is blocked or guided when affected account entries have since been reconciled.

## 9. Mobile

- The stepper shows current step and total, for example **Step 3 of 5 — Review**.
- Mapping fields stack with their sample values immediately below.
- Review rows become cards with State, Date, Description, Amount, Type, Category, and disposition action.
- A sticky issue filter switches among Ready, Review, Duplicate, and Error.
- Probable duplicate comparison stacks Imported row above Existing transaction and keeps both headings visible.
- Confirmation totals stack vertically and the primary action remains below the acknowledgement.
- No essential source field is accessible only by horizontal scrolling.

## 10. Accessibility

- The stepper identifies current, completed, and upcoming steps in text.
- Row state is announced with each row/card and never encoded by color alone.
- Table headers remain programmatically associated with cells.
- Issue counts link to filtered row sets and announce the new result count.
- Opening a row editor moves focus to its heading; closing returns focus to the row.
- Duplicate choices are a required radio group with no default.
- Progress and completion are announced without repeatedly interrupting assistive technology.
- Original and normalized values have explicit labels so they cannot be confused.

## 11. Acceptance scenarios

- [ ] Upload and inspect a valid CSV without posting transactions.
- [ ] Reject an invalid file with a specific recoverable explanation.
- [ ] Map single-amount and separate debit/credit formats.
- [ ] Preserve and reveal original values while editing normalized staging data.
- [ ] Review and categorize an otherwise valid uncategorized row.
- [ ] Resolve an ambiguous transfer explicitly.
- [ ] Suppress and report a stable-ID exact duplicate.
- [ ] Require Import or Skip for every probable duplicate.
- [ ] Skip a malformed row without hiding or corrupting valid rows.
- [ ] Confirm only after every selected row is valid and reviewed.
- [ ] Retry a confirmed import without creating duplicate postings.
- [ ] View a completion report and initiate an audited reversal.
- [ ] Complete the happy path using keyboard-only desktop navigation.
- [ ] Review and resolve every state at a 320 px mobile width.
