# ADR 0011: Define encrypted backups and measurable recovery targets

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-10-28 |
| Decision owners | Brenson Go (product owner) and engineering |
| Accepted by | Brenson Go on 2026-10-28 |
| Related work | [Policy decision #13](https://github.com/Xien04/Financial-services/issues/13), [backup/restore #18](https://github.com/Xien04/Financial-services/issues/18), [production operations #16](https://github.com/Xien04/Financial-services/issues/16) |
| Related records | [PostgreSQL ADR 0003](0003-use-postgresql.md), [sessions ADR 0006](0006-use-django-sessions-for-browser-authentication.md), [idempotency ADR 0009](0009-make-financial-writes-idempotent.md), [retention ADR 0010](0010-define-data-retention-and-deletion.md) |

## Decision in plain language

Create protected copies often enough that a host failure should lose no more than
one hour of recent work. Aim to restore safe application use within four hours,
and regularly prove recovery works. A backup on the same failed computer cannot
be the only recovery copy.

| Topic | Accepted value |
|---|---|
| Maximum recent data loss (RPO) | 1 hour |
| Maximum interruption before verified safe use (RTO) | 4 hours, including detection and operator response |
| Backup cadence | Every 30 minutes; complete and copy off-host within 15 minutes |
| Retention | All completed half-hourly copies for 48 hours; one successful copy per UTC day through 30 days |
| Encryption | age public-key encryption before persistent storage or transfer |
| Recovery key | Outside the application host, in an operator-controlled vault plus a separate protected recovery copy |
| Full restore drill | Before deployment, at least every 30 days, and after changes affecting recoverability |

Brenson Go accepted these targets on 2026-10-28; they are not proven guarantees.
They assume a named operator
can respond, functioning independent storage, available recovery keys, and a
dataset that completes the backup/restore windows. A single operator who is
unavailable for hours may miss the RTO. Deployments must qualify their staffing
and storage against these assumptions; do not silently redefine the timer to
exclude operator delay. Changing a target requires an explicit revised decision.

## Context

PostgreSQL is authoritative. The current Compose stack has one database volume;
authentication and membership-audit data exist, but no backup job or restoration
drill implements these targets. Ledger and upload/export storage are future work.
Accepted ADR 0009 requires financial results and operation identities to recover
together, with a gate for missing operations before financial writes resume.

## Decision

### 1. Define exactly what the targets measure

**RPO:** at an incident, the age of the latest usable, independently stored
database recovery point must be at most 60 minutes. Measure from its conservative
database snapshot-start time to the incident time, not from upload completion.
If the newest archive is corrupt/unusable, use the newest actually usable point;
report any resulting target failure. A backup job's exit status alone is insufficient.

**RTO:** start at service interruption (a recorded simulated outage in a drill).
Stop only when restored application health, expected data, current identity and
permissions, and safe operation have been validated and the recovery gate below
is released. Include detection, operator response, obtaining keys/configuration,
provisioning the replacement environment, transfer, restore, and verification.
A working database prompt or a read-only page does not end this timer.

If an actual outage start is uncertain, record the last-known-good and detection
times, report the uncertainty conservatively, and do not claim a shorter proven RTO.
Reconstructing missing operations may exceed four hours; keep writes blocked and
report the missed target rather than bypass the safety gate.

Example: a source fails at 12:00 UTC; the latest usable off-host snapshot began
at 11:15 UTC. Achieved RPO is 45 minutes, even if upload finished at 11:29 UTC.
If validated safe use resumes at 15:00 UTC, achieved RTO is three hours.
Both pass these targets. A snapshot from 10:45 would fail the RPO.

### 2. Back up one consistent PostgreSQL state with recoverable prerequisites

Select PostgreSQL 17 `pg_dump` custom-format backups for the MVP, restored using
`pg_restore`. Include all application-owned schemas, migrations, identity/audit
records, and future financial results plus their durable operation identities
from the same snapshot. Do not dump related tables at unrelated times.

Recreate administrator/application/backup roles and least-privilege grants from
reviewed infrastructure instructions with newly supplied secrets. Do not assume
a single-database dump contains cluster roles. Restore without importing source
ownership/ACL choices, then apply and verify the intended grants. The backup
identity must read all required data but must not be a normal application credential
or possess unnecessary superuser/CREATEDB/CREATEROLE rights.

Include an encrypted manifest with snapshot-start and completion UTC times,
application commit/image identity, PostgreSQL/tool versions, migration identifiers,
artifact integrity hash, and the key identifier. Store no rows, environment values,
passwords, or full connection URLs in public logs or the unencrypted catalog.

Keep infrastructure/configuration templates and a protected recovery-secret bundle
independently available. Record their versions and prerequisites in the runbook;
do not embed deployment secrets in images, Git, reports, or the database archive's
metadata. Future object/file storage needs a consistent recovery manifest before
its workflow is released. A database-only success cannot prove recovery of files.

### 3. Schedule, monitor, and retain backups

Use the deployment operator's scheduler at UTC minutes 00 and 30. Only one backup
for a deployment may run at a time. Each must finish dumping, encrypting, checking
the artifact, and copying it off-host within 15 minutes of its scheduled start.
A deadline breach or skipped/failed run is a failure, not a successful empty copy.

The required destination is an independent off-host storage system with separate
credentials and a different host/failure domain from PostgreSQL. Use authenticated
encrypted transport and verify the remote identity. A second directory/container
on the same host is not off-host protection. The operator supplies the actual
destination; no cloud provider or paid storage account is selected by this ADR.

Check at least every five minutes for failed/missed runs and stale recoverable
points. Warn at 45 minutes of snapshot age; declare a breached RPO at more than
60 minutes. Notify the named operator through an agreed operational channel.
No notification service or recurring automation is installed by this decision.

Retain all successful copies younger than 48 hours. For copies aged 48 hours
through 30 days, retain the latest successful snapshot per UTC day. After 30 days,
copies become due for removal within 24 hours. Apply the same rules to every
managed local/off-host copy; a local staging copy may expire sooner after verified
off-host transfer. Do not silently create indefinite secondary archives.

Retain at least the last two integrity-checked recovery candidates during normal
pruning, plus the most recent archive successfully used in a full restore drill
until a replacement passes. That tested archive may be an additional copy beyond
the daily selections; it normally remains within the same 30-day window.
These are independent full dumps, not an incremental restore chain.
If these safeguards prevent expiry because replacements failed, preserve the candidates,
raise a retention/recovery incident, and apply ADR 0010's weekly reviewed hold.
The operator must resolve the failed pipeline and excess-retention exposure;
do not automatically delete the only remaining recovery point to meet a timer.

An artifact with matching hash and a readable archive index is a recovery
candidate, not proof of a successful application restore. Record integrity checks
and full restore drill results separately. Never promote a failed/incomplete
upload into the success catalog or use it as justification for deleting a good copy.

### 4. Encrypt and separate backup, deletion, and recovery powers

Select the standalone **age** CLI with native public-key recipients for backup
encryption. The automated writer receives only public encryption recipients plus
its limited database/storage credentials. Decryption identities remain with the
recovery custodian. #18 must pin/verify compatible tool versions when using them;
this ADR installs no dependency and generates no real key.

Stream the archive into encryption; do not persist a plaintext dump on ordinary
disk. Use restricted memory-backed or encrypted temporary space if tooling requires staging and
remove it on both success and failure. The restore environment has equivalent
protection, no public ingress, and encrypted storage for sensitive restored data.

Separate permissions: writer can create new backup objects, pruner can delete only
eligible cataloged objects, and recovery custodian can retrieve/decrypt approved
copies. Application containers cannot list/read/delete backup archives or access
decryption identities. Storage deletion authority must not be the writer's normal
credential. Require MFA for the human vault/storage account where available.

Keep one protected private-key copy in the operator's independent vault and a
second protected recovery copy in another location. Review access quarterly;
rotate encryption recipients at least annually and immediately after suspected
key exposure or custodian changes. Keep necessary old decryption identities
until their last retained archive/hold expires, unless verified re-encryption has
replaced it. Test decryption with the replacement key before retiring an old one.
Changing the recipient for new backups does not re-encrypt old copies.

### 5. Reopen only after a safe recovery gate

The runbook and #18 drill must exercise this sequence:

1. Record the interruption, isolate the affected deployment, and stop ordinary
   login, financial mutations, import workers, and other scheduled writers.
2. Obtain a usable off-host archive, manifest, keys, reviewed infrastructure,
   protected recovery register, and current configuration. Verify identity/integrity.
3. Create a new isolated PostgreSQL environment. Never overwrite an existing
   database/volume during a drill. Restore the consistent data and intended grants.
4. Clear restored sessions, invalidate pre-incident reset credentials through a
   documented authentication-key rotation without validating old fallback keys,
   and verify current account status/roles. Recover operator access only through
   a verified identity procedure; a restored password hash is not proof of ownership.
5. Reapply closure, profile cleanup, credential-reset/revocation, and permission
   restrictions from the separately protected register. Accounts whose current
   password/status cannot be confirmed stay disabled pending verified reset.
6. Reconcile the interval between the recovery point and the incident. Preserve
   the restored operation identities; reconstruct missing committed operations and
   their identities from authoritative retained evidence before allowing retries.
   ADR 0009 forbids treating a missing key in an old backup as proof no write happened.
7. If evidence is insufficient, keep affected workflows blocked and require
   verified owner/operator reconciliation. Do not mint new keys or automatically
   retry ambiguous financial writes to make the application appear recovered.
8. Verify health, schema/migrations, constraints, data relationships, grants,
   current membership boundaries, and rejection of old sessions/reset credentials.
   Record operator sign-off and only then reopen permitted operations/end the RTO.

The operator owns recovery and sign-off. The recovery custodian owns key retrieval;
the product/data owner resolves ambiguous business records. Preserve minimal
incident evidence without putting financial payloads or credentials into reports.

### 6. Prove recovery before relying on it

Perform a full isolated restore drill before first operational use, at least every 30 days,
and after changes to database major version, backup/encryption/storage tooling,
keys, or schemas/security behavior that affect recovery. A quarterly review checks
the inventory, named custodians, retention behavior, and continued target suitability.

#18 must use synthetic users/workspaces/memberships/audit data. Compare source and
restored relationships, constraints, migrations, and controlled application access;
measure actual elapsed recovery time and conservative recovery-point age. Test
corrupt/missing archive, wrong/missing key, unavailable destination, missed backup,
old-restriction replay, and a retention boundary preserving required usable copies.
Fail clearly and safely; do not label failed/partial drills as passing.

Hosted CI can prove isolated procedure behavior. A simulated secondary store on
one runner cannot prove physical off-host resilience or a human response SLA.
Each real deployment must qualify its destination, operator availability, dataset,
key access, and achieved targets. When financial/file workflows appear, extend
the drill to their actual data and retry behavior before relying on these targets.

Every report records source commit, environment, tool versions, date/tester,
scenario, start/end timestamps, recovery-point timestamp, achieved RPO/RTO,
validation results, cleanup, and limitations. Keep real archives/keys out of GitHub
Actions artifacts and reports. Sanitized evidence may be committed; sensitive
disposable restore resources must be removed within 24 hours after drill completion.

## Alternatives and consequences

- Daily backups with a 24-hour loss target are cheaper/simpler, but could lose a
  day's manual entries and import review. The selected hourly loss limit costs
  more storage/operations and needs the half-hourly schedule plus completion margin.
- Continuous WAL archiving/PITR can support tighter recovery points but adds
  operational complexity. Revisit it if logical dumps cannot meet the window.
- A live replica is useful for availability but does not replace retained backups
  for accidental deletion/corruption. Same-host copies alone do not cover host loss.
- A 24-hour recovery target is easier for an unattended personal installation.
  The selected four-hour limit assumes operator availability; moving to the looser
  target requires an explicit policy revision rather than a deployment-side override.

Frequent full dumps, independent storage, protection of old keys, manual register
maintenance, and restore drills have ongoing costs. Data lost after a recovery
point may require manual reconstruction; backups and idempotency cannot guarantee
zero loss. Missed targets require remediation or an explicit policy revision.

## Acceptance record and delivery boundary

- [x] Brenson Go accepts the one-hour RPO, four-hour RTO, clock definitions, and availability assumptions.
- [x] Brenson Go accepts cadence, completion deadline, off-host destination requirements, retention, and alerts.
- [x] Brenson Go accepts encryption tooling, custody/rotation, least privilege, and recovery responsibilities.
- [x] Brenson Go accepts the security/deletion/retry recovery gate and drill schedule/evidence requirements.
- [x] Record explicit acceptance/date and link the accepted policy from #13/#18.

Accepted by Brenson Go on 2026-10-28 after reviewing ADRs 0010–0011 for
[issue #13](https://github.com/Xien04/Financial-services/issues/13). The product
owner's explicit confirmation was: "both files are accepted."

This records M1-POL-03, M1-POL-04, and the relevant M1-POL-06 decisions only.
#18 implements the procedure and measured evidence;
#16 coordinates deployed secrets/serving configuration. It must not implement
future ledger/import/export/deletion features merely to satisfy a foundation drill.
Relevant application workflows own their hooks and future recovery extensions.

## References

- [PostgreSQL backup approaches](https://www.postgresql.org/docs/17/backup.html)
- [pg_dump consistent single-database backups](https://www.postgresql.org/docs/17/app-pgdump.html)
- [pg_restore ownership and privilege handling](https://www.postgresql.org/docs/17/app-pgrestore.html)
- [age encryption and key/recipient model](https://github.com/FiloSottile/age)
- [Recovery objectives for downtime and data loss](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_planning_for_recovery_objective_defined_recovery.html)
