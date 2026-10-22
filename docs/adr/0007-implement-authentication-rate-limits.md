# ADR 0007: Implement shared authentication rate limits and browser protections

| Field | Value |
|---|---|
| Status | Accepted for implementation |
| Date | 2026-10-22 |
| Decision owners | Engineering, within the product owner's authorized authentication implementation |
| Related records | [ADR 0006](0006-use-django-sessions-for-browser-authentication.md), [toolchain](0004-use-uv-and-foundation-tooling.md) |

## Context

ADR 0006 requires configurable, cross-worker account/IP limits before shipping
login and recovery. PostgreSQL is already required; Redis remains undecided.
The authentication UI also requires a strict CSP and reset-token privacy.

## Decision

Use PostgreSQL rate-limit buckets, unique by a keyed SHA-256 digest of endpoint
scope, signal type, and normalized identifier. Lock each bucket inside an atomic
transaction before incrementing. Account and IP budgets are both consumed,
including rejected attempts. All API workers share the database. Storage failures
fail closed. Counters reset at the end of a fixed window; limits are deliberately
not cleared after successful authentication.

| Scope | Account limit | Client-IP limit | Fixed window |
|---|---:|---:|---|
| Login and authenticated password change | 5 | 30 | 15 minutes |
| Recovery email request | 3 | 10 | 1 hour |
| Reset confirmation (account signal is encoded user ID) | 10 | 30 | 1 hour |

The six limit counts are configurable with positive-integer environment settings
listed in `.env.example`. Windows are fixed by this implementation. Return 429
with `Retry-After`; retain only keyed digests and counters. Remove buckets older
than a day with `clear_auth_limits`. This limiter supplements edge request and
body-size limits; it does not provide volumetric denial-of-service protection.

Take the IP signal from `REMOTE_ADDR`. Never trust arbitrary forwarded IP headers.
Behind a proxy, it represents the immediate peer unless the trusted deployment
edge normalizes the actual client address before Django. Shared proxy clients
therefore conservatively share the IP budget. Deployment must resolve and verify
that topology before public exposure; spoofed headers must never select a bucket.

Use Django's standard password validators, with a 12-character minimum and a
1024-character API input maximum. Identity uses lowercase, trimmed email addresses
with a PostgreSQL lower-expression uniqueness constraint. Provision the first user
and workspace atomically, serialized with a transaction-scoped advisory lock.

Use a dedicated CSRF-protected activity POST for real keyboard/pointer input,
at most once per minute in the UI. Passive GETs and probes never renew idle
expiry. Successful protected mutations renew idle time up to the original
absolute deadline. Session markers missing from a preexisting session fail closed.

Password-reset credentials travel in a URL fragment, are removed from browser
history on opening the form, and are submitted in a JSON POST. They do not appear
in HTTP request targets. Use a no-referrer policy. Validate reset tokens under a
user-row lock before changing the password to prevent concurrent token reuse.
Email failures use a generic response and a sanitized operational log message.

Use a fresh nonce for Next.js scripts and styles on each dynamically rendered
page, following the framework's CSP integration. Permit development evaluation
and inline development styles only in development. Disallow framing and objects;
restrict fetches and form submissions to the public origin. Auth responses and
HTML are private and not stored in shared caches.

## Consequences

No runtime dependency or external limiter service is introduced. Each attempted
authentication performs database writes, and persistent counters need cleanup.
Fixed windows allow bursts at window boundaries; tune limits based on measured
operation rather than removing account/IP enforcement. Public deployments still
need a trusted reverse proxy, HTTPS, SMTP, and verified client-address handling.

Initial membership creation and internal role/removal operations append durable
identity-owned audit rows atomically. Rows contain UUID actor/workspace/subject
identifiers, previous/new roles, and creation time, without email addresses,
names, passwords, or tokens. Retention and user-deletion policy remain separate
decisions; this implementation never silently purges audit evidence.

Dynamic HTML incurs per-request rendering. Reset links should be reopened after
refreshing the cleared reset form. No public signup, invitation, member-management
API, or financial workflow is introduced.

## References

- [Django session framework](https://docs.djangoproject.com/en/5.2/topics/http/sessions/)
- [Django password authentication and recovery](https://docs.djangoproject.com/en/5.2/topics/auth/default/)
- [Next.js nonce CSP](https://nextjs.org/docs/app/guides/content-security-policy)
