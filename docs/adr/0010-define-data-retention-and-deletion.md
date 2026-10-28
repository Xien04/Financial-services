# ADR 0010: Define data retention, access, and account closure

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-10-28 |
| Decision owners | Brenson Go (product owner) and engineering |
| Accepted by | Brenson Go on 2026-10-28 |
| Related work | [Policy decision #13](https://github.com/Xien04/Financial-services/issues/13), [logs #15](https://github.com/Xien04/Financial-services/issues/15), [backup/restore #18](https://github.com/Xien04/Financial-services/issues/18) |
| Related records | [Ledger ADR 0002](0002-use-ledger-entry-model.md), [sessions and roles ADR 0006](0006-use-django-sessions-for-browser-authentication.md), [authentication ADR 0007](0007-implement-authentication-rate-limits.md), [idempotency ADR 0009](0009-make-financial-writes-idempotent.md), [recovery ADR 0011](0011-define-backup-and-recovery-targets.md) |

## Decision in plain language

Keep financial history and the evidence needed to explain it. Remove temporary
data on a schedule. Closing a login stops access immediately; it does not silently
erase the financial notebook or its duplicate-prevention records.

| Topic | Accepted rule |
|---|---|
| Financial history and its audit/idempotency evidence | Retain without an automatic expiry in MVP, including after account/workspace closure |
| Login profile after confirmed closure | Disable immediately; remove direct profile identifiers after 30 days |
| Operational logs | 30 days; no financial payloads or credentials |
| Sanitized authentication/security event logs | 90 days; separate from durable financial/membership audit evidence |
| Backups | All half-hourly copies for 48 hours, then one per UTC day through 30 days |
| Temporary export files | Expire after 24 hours; revoke download access immediately on closure |
| Uploaded files | Unconfirmed work expires after 7 idle days; completed raw files expire after 7 days, with a 30-day limit from upload |

Brenson Go accepted these operating rules on 2026-10-28. Acceptance records policy;
it does not claim the corresponding jobs or workflows are implemented.
Retention periods below mean **cleanup becomes due** at that age; remove eligible
data within the next 24 hours unless a row states otherwise. Access expiration
is immediate and does not wait for physical cleanup. Times are elapsed UTC time.

## Context and assumptions

The product is initially a self-hostable personal-finance application. Existing
ADRs require immutable posted entries, audited void/archive operations, retained
membership evidence, workspace authorization, and durable operation identities.
Users, workspaces, memberships, audit rows, and authentication counters exist;
financial workflows, upload/export files, and backup automation do not yet exist.

This decision assumes the deployment operator controls its database, backup
storage, and keys. It selects no statutory retention period and claims no legal
compliance. Public multi-user hosting, a specific jurisdictional obligation, or a
requirement to permanently erase financial history needs a separate requirements
review before that deployment. Such a change must explicitly reconcile the
accepted ledger semantics rather than silently introduce destructive deletion.

## Decision

### 1. Give each data class an owner, lifecycle, and access boundary

Product owner means Brenson Go for this repository. Each deployment must name an
operator who runs maintenance and a recovery custodian who can retrieve keys.
One self-hosting person may perform both roles; record that single-person risk.
Engineering implements and tests the policy; it is not the custodian of real data.

| Data class | Retention / removal rule | Accountable module / operator | Permitted access |
|---|---|---|---|
| Financial transactions, entries, accounts, reconciliation, and posted import provenance | No automatic expiry; preserve originals and linked corrections/voids | Owning financial module; deployment operator protects storage | Current workspace membership/role; no access merely from knowing an ID |
| Successful financial operation identities and immutable receipt references | Same lifetime as their financial history; never expire to permit a second posting | Ledger/import owner under ADR 0009 | Owning service and currently authorized replay caller |
| Durable financial and membership audit evidence | Same lifetime as the history/workspace it explains; keep UUID/action/time/linkage, not credential or financial request bodies | Owning module; operator | Authorized owner workflow or controlled, audited recovery access |
| Active user profile and password hash | Keep while login is active; closed profiles follow section 2 | Identity; operator | User's own profile; narrowly authorized identity services |
| Expired session rows | Run daily cleanup; remove within 24 hours of stored expiry. Idle/absolute limits remain 30 minutes/12 hours | Identity; operator | Authentication service; no session values in logs |
| Password reset credentials | One-hour validity under ADR 0006; do not create a stored reset-token archive | Identity; operator protects SMTP configuration | Intended recovery recipient and validating service only |
| Authentication rate-limit buckets | Eligible once their start time is over 24 hours old; daily cleanup gives a normal maximum age of 48 hours | Identity; operator | Limiter/maintenance service; retain only keyed digests and counters |
| Operational/debug/error logs | 30 days from event, then cleanup within 24 hours; production debug payload collection stays disabled | Logging owner; operator | Authorized operations staff; application roles confer no log-store access |
| Sanitized authentication/security event logs | 90 days from event, then cleanup within 24 hours | Identity/logging owner; operator | Restricted security investigation access |
| Raw upload files and unposted staging | Expire unconfirmed work after 7 idle days; delete completed/cancelled raw files 7 days after completion/cancellation; raw files and unposted staging become due at 30 days from upload even if activity continues | Imports; operator | Authorized import actor/workspace role and isolated parser |
| Posted import row provenance | Retain original source values, mapping/version, disposition, and result linkage with the posted history; raw-file expiry must not remove required row evidence | Imports/ledger | Authorized workspace services; never operational logs |
| Generated export files | Access expires 24 hours after creation or immediately on revocation/closure; remove files within 24 hours of expiry | Reporting; operator | Authorized owner with current permission; no permanent public URLs |
| Database backups and temporary restore copies | Retention/holds in ADR 0011; remove disposable restore copies within 24 hours of drill completion | Deployment operator and recovery custodian | Backup writer/pruner/recovery roles, separated from app access |
| Recovery register: deletion, closure, credential reset, and access revocation instructions | 90 days minimum; longer while any retained backup could restore superseded state | Operator; independent protected storage | Recovery custodian; minimal UUID/action/time only |
| Sanitized committed verification records | Retain with repository history; no real user records, secrets, backup contents, or recovery keys | Engineering | Repository access policy |

Logs must exclude passwords, cookies/session identifiers, reset links/tokens,
raw request/response bodies, financial records, full account numbers, and direct
email/IP identifiers. Use generated request IDs and safe event/error codes.
The 90-day log rule must never become a cleanup rule for durable audit rows.
Deployment/proxy logs and error-reporting services must follow the same classes;
an external tool does not silently receive a longer retention exception.

### 2. Separate financial removal, login closure, and workspace closure

**Financial removal:** a persisted transaction is voided with audit evidence;
a financial account/category is archived according to its owning workflow.
Original financial entries, relationships, and idempotency identities remain.
This decision does not authorize individual or bulk physical ledger deletion.

**Login-account closure:** require a verified request. Disable login, revoke all
sessions and download capabilities, and stop new work under that identity at
confirmation. Existing membership/owner protections still apply: transfer ownership
or explicitly close the personal workspace before closing its final owner's login.
Do not strand an active workspace without an owner or use staff status as a bypass.

During the following 30 days, the operator may reverse closure only after verifying
identity and current ownership; never restore old sessions or an old password.
At day 30, remove email/display name and disable the password hash through the
owning identity workflow. Retain a non-login UUID tombstone where audit foreign
keys require it. The future workflow must define consistent uniqueness handling;
do not bypass the current protected foreign keys by directly deleting database rows.

**Workspace closure:** only an authorized owner may initiate it. Freeze ordinary
access, mutations, scheduled work, and existing export links. Offer an authenticated
export before confirmation when that workflow exists. Retain the financial notebook,
audit, and operation identities with restricted operator recovery access. Restoration
of a closed workspace requires a separate verified owner request and an audit event.

The accepted choice is closure and profile minimization, **not permanent
erasure of all financial data**. Retained payees, source rows, UUID relationships,
and financial details can still identify people. Do not describe them as anonymous.
There is no automatic financial-history purge in this MVP policy. An
irreversible workspace-erasure workflow requires an explicit later decision that
addresses ledger/audit semantics, all copies, and the intended deployment's obligations.

### 3. Explain how backup retention affects deletion

Routine live cleanup does not edit individual rows inside historical backup
archives. An older encrypted copy can retain data until that copy expires.
After profile cleanup, the normal additional backup-retention window is 30 days
plus up to 24 hours for cleanup. Including the closure grace period and both daily
cleanup windows, direct profile copies can remain for up to 62 days after closure
under normal operation. Incident preservation exceptions can extend that period;
report them explicitly rather than promise immediate erasure everywhere.

Record closure, profile cleanup, password reset/revocation, and role/access changes
in the minimal independently protected recovery register. It must cover every
backup that could resurrect superseded state; never expire its records while an
older retained copy still needs them. Future relevant workflows must include this
operator handoff before claiming the request is fully fulfilled. For MVP operations,
use a controlled manual register; an automated external journal is not introduced here.

ADR 0011 requires replaying these restrictions in isolation before reopening a
restored app. If the register is unavailable or does not cover the recovery gap,
normal login and financial writes remain blocked until identity/ownership and
missing operations are independently reconciled. A backup must not quietly reopen
a closed login, restore a revoked role, or bypass a completed profile cleanup.

### 4. Enforce retention without hiding maintenance failures

Every cleanup job must have a bounded selection rule, a preview/dry-run mode,
minimum-privilege credentials, sanitized counts, and failure reporting. Run normal
cleanup at least daily. If a deadline is missed, notify the operator on that run
and record an overdue-policy incident; do not silently extend retention.

Security/incident holds must name the data class, reason, operator, and next review
date (at most 7 days away). Preserve only what is necessary, restrict access, and
review weekly until resolved. A hold is an explicit exception, not permission to
put raw payloads or secrets into logs. It does not authorize a legal-compliance claim.

Future uploads/exports must build expiry, revocation, and scoped access into their
own milestones. If raw-file expiry interrupts an unconfirmed import, show it as
expired and require a new upload; never post from partially removed staging.
Revoke access when the applicable expiry is reached, including the 30-day cap;
cleanup's 24-hour grace does not allow additional posting. Preserve required
posted source-row evidence before deleting the raw file.

## Examples for review and later tests

| Scenario | Expected policy outcome |
|---|---|
| A user voids an expense | Original entries/audit/operation identity retained; active totals exclude it |
| A session expires at 10:00 UTC | Access denied immediately; expired row removed by 10:00 UTC the next day |
| A user closes a login on day 0 | Access stops on day 0; direct profile cleanup becomes due on day 30 |
| An old backup predates that closure | Reapply closure/cleanup instructions before normal access resumes |
| An operational log reaches 30 days | Delete within the next 24 hours unless a recorded hold applies |
| An import raw file expires after posting | Posted source-row provenance and retry identities remain |
| A 24-hour export link is used after the owner loses access | Deny access even before its file is physically removed |
| An old backup is held because newer backups failed | Report the retention exception; extend matching recovery-register coverage |

These are policy examples. They are not evidence of implemented deletion jobs,
account-closure interfaces, or financial workflows.

## Alternatives and consequences

- Keeping everything forever simplifies investigation but retains unnecessary
  profiles, files, and logs. This decision retains authoritative history and
  expires temporary classes separately.
- Deleting all history on account closure would conflict with current ledger
  semantics and undermine audit/retry evidence; it needs an explicit revised decision.
- Keeping only current database state would make old backups capable of reviving
  revoked access. A protected recovery register adds operator work but closes that gap.
- Shorter log/file windows reduce exposure and storage but make investigation or
  re-import less convenient. The accepted 30/90-day log periods are product choices.

Durable financial/audit storage grows over time. Profile minimization cannot
remove every identifying fact in financial history. The product owner accepted
these tradeoffs; a more demanding deletion requirement needs an explicit revised decision.

## Acceptance record and implementation ownership

- [x] Brenson Go accepts the data classes, access rules, owners, and retention periods.
- [x] Brenson Go accepts closure/profile minimization and no automatic financial-history erasure.
- [x] Brenson Go accepts backup-delay disclosure, recovery-register obligations, and incident holds.
- [x] Record explicit acceptance/date and link this ADR from #13 and #18.

Accepted by Brenson Go on 2026-10-28 after reviewing ADRs 0010–0011 for
[issue #13](https://github.com/Xien04/Financial-services/issues/13). The product
owner's explicit confirmation was: "both files are accepted."

This records M1-POL-01, M1-POL-02, M1-POL-05, and the relevant M1-POL-06 decisions;
it does not establish implementation evidence. #15 implements log lifecycle requirements;
#18 implements backup lifecycle/recovery controls. Dedicated identity/closure,
upload, and export implementation work must be linked to the owning milestone
before those workflows are delivered. Do not claim those features already exist.

| Delivery milestone | Policy implementation owned there |
|---|---|
| [Milestone 1 — Foundation](../ROADMAP.md#milestone-1--application-foundation-current) | #15 applies log retention/access rules; #18 implements protected backup retention and the foundation recovery gate |
| [Milestone 2 — Ledger](../ROADMAP.md#milestone-2--ledger-engine) | Retained financial/audit/operation identities and actual posting recovery/retry behavior |
| [Milestone 4 — CSV imports](../ROADMAP.md#milestone-4--csv-imports) | Raw/staging expiry, preserved posted source-row evidence, and safe import resumption |
| [Milestone 5 — Reports and export](../ROADMAP.md#milestone-5--dashboard-reports-and-export) | Owner-only export, download revocation/expiry, and temporary-file cleanup |
| [Milestone 8 — Hardening and release](../ROADMAP.md#milestone-8--hardening-and-mvp-release) | Deliver/validate account-closure and profile-minimization workflows and verify retention, portability, and recovery end to end |

## References

- [Accepted financial deletion semantics](../FINANCIAL_SEMANTICS.md#43-corrections-and-deletion)
- [Authentication maintenance commands](../AUTHENTICATION.md#limits-and-maintenance)
- [Django expired-session cleanup](https://docs.djangoproject.com/en/5.2/topics/http/sessions/#clearing-the-session-store)
