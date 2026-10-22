# GitHub issue labels and creation guide

This guide records the label names and colors discussed for Financial Services,
plus PowerShell examples for creating labels and issues with GitHub CLI (`gh`).
Commands are examples to run manually; saving this file does not create anything
on GitHub. Technical decisions still require the ADR process in [AGENT.md](../AGENT.md).

## Label catalog

| Label | Color | Hex | Description |
|---|---|---|---|
| `type:feature` | Green | `#0E8A16` | New or expanded application capability |
| `type:task` | Light blue | `#C5DEF5` | Engineering, testing, or maintenance work |
| `type:bug` | Red | `#D73A4A` | Confirmed behavior that contradicts accepted requirements |
| `type:docs` | Blue | `#0075CA` | Documentation correction or improvement |
| `type:decision` | Purple | `#7057FF` | Unresolved product or technical decision |
| `priority:p0` | Dark red | `#B60205` | Immediate incident involving financial corruption, data loss, or security |
| `priority:p1` | Orange | `#D93F0B` | Blocks the current milestone or a required correctness/security gate |
| `priority:p2` | Yellow | `#FBCA04` | Planned work that can follow current blockers |
| `area:foundation` | Pale blue | `#BFD4F2` | Application scaffolding, shared tooling, and CI |
| `area:ledger` | Teal | `#006B75` | Accounts, postings, balances, and reconciliation |
| `area:identity` | Deep purple | `#5319E7` | Authentication, workspaces, roles, and authorization |
| `area:imports` | Mint | `#BFE5BF` | CSV staging, mapping, duplicate review, and posting orchestration |
| `area:reporting` | Cyan | `#76D7EA` | Dashboard metrics, reports, drill-down, and exports |
| `area:planning` | Lavender | `#D4C5F9` | Budgets, recurring items, and financial goals |
| `area:operations` | Slate | `#6E7781` | Deployment, monitoring, backups, recovery, and retention |
| `security` | Burgundy | `#8B1538` | Security or privacy requirements and review |
| `blocked` | Dark gray | `#444444` | Work cannot proceed because of a named dependency |

Use one primary type, one priority, and the relevant area labels. Add `security`
when appropriate. Use `blocked` only with a specific dependency recorded in the
issue, and remove it when resolved. Planned features are not bugs; a security
requirement is not evidence of a vulnerability. Priority names remain meaningful
without color.

Track delivery stages with milestones from [ROADMAP.md](ROADMAP.md). Track status
on a project board: Backlog, Ready, In progress, In review, and Done.

## Prepare GitHub CLI

Install [GitHub CLI](https://cli.github.com/) if `gh --version` is unavailable.
Run the following from this repository's root in PowerShell:

```powershell
gh --version
gh auth status
# If authentication is needed:
gh auth login

# Check the repository selected by gh before running creation commands:
gh repo view --json nameWithOwner --jq .nameWithOwner
gh label list --limit 100
```

The examples use the repository selected by `gh` in the current checkout. To
target an explicit repository, add `--repo OWNER/REPO` to the label and issue
commands, replacing `OWNER/REPO` with the verified repository name.

## Create labels

Run these once for labels that do not already exist. Colors passed to `gh` omit
the leading `#`. An existing label causes an error; add `--force` to an individual
command only when you intend to update that label's color and description.

```powershell
gh label create 'type:feature' --color '0E8A16' --description 'New or expanded application capability'
gh label create 'type:task' --color 'C5DEF5' --description 'Engineering, testing, or maintenance work'
gh label create 'type:bug' --color 'D73A4A' --description 'Confirmed behavior that contradicts accepted requirements'
gh label create 'type:docs' --color '0075CA' --description 'Documentation correction or improvement'
gh label create 'type:decision' --color '7057FF' --description 'Unresolved product or technical decision'
gh label create 'priority:p0' --color 'B60205' --description 'Immediate incident involving financial corruption, data loss, or security'
gh label create 'priority:p1' --color 'D93F0B' --description 'Blocks the current milestone or a required correctness/security gate'
gh label create 'priority:p2' --color 'FBCA04' --description 'Planned work that can follow current blockers'
gh label create 'area:foundation' --color 'BFD4F2' --description 'Application scaffolding, shared tooling, and CI'
gh label create 'area:ledger' --color '006B75' --description 'Accounts, postings, balances, and reconciliation'
gh label create 'area:identity' --color '5319E7' --description 'Authentication, workspaces, roles, and authorization'
gh label create 'area:imports' --color 'BFE5BF' --description 'CSV staging, mapping, duplicate review, and posting orchestration'
gh label create 'area:reporting' --color '76D7EA' --description 'Dashboard metrics, reports, drill-down, and exports'
gh label create 'area:planning' --color 'D4C5F9' --description 'Budgets, recurring items, and financial goals'
gh label create 'area:operations' --color '6E7781' --description 'Deployment, monitoring, backups, recovery, and retention'
gh label create 'security' --color '8B1538' --description 'Security or privacy requirements and review'
gh label create 'blocked' --color '444444' --description 'Work cannot proceed because of a named dependency'

gh label list --limit 100
```

## Suggested initial issues

These are proposed issues from the project review, not existing GitHub issues or
new architecture approvals. Check for existing issues before creating them.
Milestone numbers refer to the roadmap; GitHub milestones must be created
separately before assigning issues to them.

| Suggested title | Labels | Roadmap milestone |
|---|---|---|
| Scaffold Django, Next.js, PostgreSQL, and local startup | `type:feature`, `priority:p1`, `area:foundation` | 1 - Foundation |
| Establish automated tests, linting, type checks, and security scanning | `type:task`, `priority:p1`, `area:foundation`, `security` | 1 - Foundation |
| Decide authentication/session strategy and define role permissions | `type:decision`, `priority:p1`, `area:identity`, `security` | 1 - Foundation |
| Define idempotency key scope, conflict behavior, and retention | `type:decision`, `priority:p1`, `area:ledger` | 1 - Foundation |
| Implement accounting acceptance tests and concurrent-posting tests | `type:task`, `priority:p1`, `area:ledger` | 2 - Ledger |
| Define matching behavior when both transfer sides are imported | `type:decision`, `priority:p2`, `area:imports` | 4 - CSV Imports |
| Define deletion, audit, upload, and backup retention policies | `type:decision`, `priority:p2`, `area:operations`, `security` | 1 - Foundation |
| Define measurable performance and recovery acceptance targets | `type:task`, `priority:p2`, `area:operations` | 1 - Foundation |
| Specify goal allocation and contribution calculation examples | `type:decision`, `priority:p2`, `area:planning` | 7 - Goals |
| Align feature matrix with accepted MVP workflows and terminology | `type:docs`, `priority:p1`, `area:foundation` | 1 - Foundation |

## Create an issue from Markdown

Each body should describe the problem, expected outcome, acceptance criteria,
dependencies, verification, and relevant source documents. For decision issues,
completion means a recorded decision; implementation can be tracked separately.

This example writes an issue body to a uniquely named temporary Markdown file.
Review the displayed content before running the final `gh issue create` command.

```powershell
# Check open and closed issues for an existing match first:
gh issue list --state all --search 'Scaffold Django' --limit 100

$issueBodyFile = Join-Path ([System.IO.Path]::GetTempPath()) ('financial-services-issue-' + [guid]::NewGuid().ToString('N') + '.md')
@'
## Problem

The repository has accepted product definitions and foundation ADRs but no
runnable Django API, Next.js interface, or PostgreSQL development environment.

## Expected outcome

A contributor can start the application foundation locally from the README,
using the physical layout accepted in ADR 0001 and PostgreSQL per ADR 0003.

## Acceptance criteria

- [ ] Scaffold backend/ and frontend/ according to ADR 0001.
- [ ] Add root compose.yaml and relevant infra/ definitions for local startup.
- [ ] Configure PostgreSQL and verify clean-database migrations.
- [ ] Lock dependencies used by the scaffold and document runtime versions.
- [ ] Document configuration and startup commands without committed secrets.
- [ ] Demonstrate a clean local startup and record verification evidence.

## Dependencies and boundaries

- Follow accepted ADRs 0001-0003 and AGENT.md.
- Record material tooling decisions not already covered by accepted ADRs.
- Coordinate shared tooling/CI and identity work in separate linked issues.
- This scaffold alone does not complete Milestone 1.

## Verification

Record the startup, migration, and available quality-check commands actually run,
their results, and any checks that remain unavailable.

## References

- docs/ROADMAP.md - Milestone 1
- docs/adr/0001-use-django-modular-monolith.md
- docs/adr/0003-use-postgresql.md
- AGENT.md
'@ | Set-Content -LiteralPath $issueBodyFile -Encoding utf8

Get-Content -LiteralPath $issueBodyFile

# Run after reviewing the body and creating the required labels:
gh issue create --title 'Scaffold Django, Next.js, PostgreSQL, and local startup' --label 'type:feature' --label 'priority:p1' --label 'area:foundation' --body-file $issueBodyFile
```

For an existing Markdown body, use `--body-file 'path/to/issue.md'` instead. If the
matching GitHub milestone exists, add `--milestone 'EXACT MILESTONE TITLE'` using
its actual title. Each successful creation prints the issue URL. Re-running the
creation command creates another issue; check the returned URL and existing
issues before retrying an uncertain result.

Command references: [gh label create](https://cli.github.com/manual/gh_label_create)
and [gh issue create](https://cli.github.com/manual/gh_issue_create).
