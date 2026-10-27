# ADR 0006: Use Django sessions for browser authentication

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-10-22 |
| Accepted by | Brenson Go on 2026-10-22 |
| Decision owners | Product owner and engineering |
| Related records | [ADR 0001 — Django modular monolith](0001-use-django-modular-monolith.md); [ADR 0003 — PostgreSQL](0003-use-postgresql.md) |
| Related documents | [Product architecture](../PRODUCT_ARCHITECTURE.md), [roadmap](../ROADMAP.md) |

## Context

Financial Services is a self-hostable web application with a Next.js interface,
a Django REST Framework API, and PostgreSQL.

MVP requires email/password authentication, password recovery, and workspace
authorization. MFA, passkeys, OAuth, and shared-household invitations remain
outside MVP.

The existing Next.js configuration forwards `/api` requests to Django. The
application needs one authentication authority, revocable browser sessions,
explicit CSRF protection, and permissions enforced by the backend.

## Decision

### 1. Django owns identity and authentication

Use Django's authentication framework and a custom user model in the `identity`
module.

The user model will:

- Use a UUID primary identifier.
- Use email as the login identifier.
- Store passwords exclusively through Django's password-hashing APIs.
- Support display name, timezone, active status, and timestamps.
- Be configured before the initial identity migrations.

Treat email addresses as case-insensitive application identifiers. Trim
surrounding whitespace, apply a consistent normalization policy, and enforce
case-insensitive uniqueness in PostgreSQL. Do not remove dots or apply
provider-specific address transformations.

Inactive users cannot authenticate or continue using existing sessions.

### 2. Store browser sessions in PostgreSQL

Use Django's database-backed session engine and DRF's `SessionAuthentication`.

The browser receives an opaque session identifier in a cookie. Session state
remains on the server.

Do not introduce JWT access/refresh tokens, browser token storage, or a separate
Next.js authentication system for MVP.

Retain Django's standard opaque session keys; the UUID requirement applies to
application domain identifiers.

### 3. Use one public origin

Expose the interface and `/api/v1` through the same public origin.

Django remains responsible for authentication even when requests pass through
Next.js or a production reverse proxy. Proxy configuration must preserve the
information Django needs to validate hosts, HTTPS, and CSRF origins.

Authenticated responses must not enter shared caches. Server-rendered requests
must forward only the requesting user's credentials.

### 4. Protect cookies and state-changing requests

Production session cookies must use:

- `Secure`
- `HttpOnly`
- `SameSite=Lax`
- No `Domain` attribute
- Path `/`

Require HTTPS in production. Permit insecure cookies only in explicit
local-development settings.

Require Django CSRF validation for all state-changing browser requests, including
anonymous login and password-recovery submissions. Logout must use POST.

Provide a CSRF bootstrap mechanism for the client and refresh the client's CSRF
token after login. `SameSite` cookies supplement CSRF protection; they do not
replace it.

### 5. Define session expiration and revocation

Use these initial policies:

- **Idle timeout:** 30 minutes.
- **Absolute lifetime:** 12 hours from successful authentication.
- **Remember me:** unavailable in MVP.

Enforce both limits on the server. Health checks and passive background polling
must not extend the idle timeout.

Rotate the session identifier on login. Logout invalidates the current session
on the server and clears its browser cookie.

A successful password change or password reset invalidates all existing
sessions, including the current session. Require a fresh login afterward.

Recheck account status and workspace membership during authorized requests.
Role changes and membership removal must affect subsequent requests without
requiring another login.

Expired session records must be removed through a documented maintenance command.

### 6. Provision the initial owner without public registration

Keep public registration disabled for MVP.

Provide an operator command to create the initial user and personal workspace
using the same identity services as other application paths.

The command must collect passwords securely without exposing them in command
arguments, logs, or repository files. Do not ship default credentials.

Public signup, invitations, and additional-user provisioning require separately
documented workflows.

### 7. Provide password recovery

Use Django's password-reset primitives with a link lifetime of **one hour**.

Recovery must:

- Return a generic response whether or not an email address exists.
- Use expiring links that become unusable after a successful reset.
- Prevent concurrent reuse of a reset link.
- Generate links from the configured public application URL.
- Avoid automatically logging the user in after reset.
- Keep passwords, reset links, and tokens out of logs.

Production email delivery requires operator-provided configuration. Document how
operators recover access when email delivery is unavailable.

Apply configurable rate limits to login and recovery endpoints using both
account and client-IP signals. Limits must work across API workers. Exact
thresholds and the limiter implementation must be recorded before those
endpoints ship.

### 8. Enforce workspace roles in the backend

Use `owner`, `editor`, and `viewer` roles.

| Capability | Owner | Editor | Viewer |
|---|---|---|---|
| View financial records and reports | Yes | Yes | Yes |
| Create or change financial records | Yes | Yes | No |
| Import data and reconcile accounts | Yes | Yes | No |
| Export the complete workspace | Yes | No | No |
| Manage workspace settings and membership | Yes | No | No |
| Initiate workspace deletion | Yes | No | No |

These permissions do not introduce shared-household interfaces into MVP. The
initial personal-workspace user is its owner.

Require current membership and object-level authorization at API, service, and
query boundaries. A supplied workspace or object identifier is never sufficient
authorization.

Prevent removal or demotion of the final owner. Django staff or superuser status
must not silently bypass workspace authorization in normal application APIs.

Deletion permission remains subject to the separately defined retention and
audited-deletion workflow.

## Alternatives considered

### JWT access and refresh tokens

Not selected for the MVP browser application. They would require additional
token storage, refresh, and revocation behavior without a current
independent-client requirement.

### A separate Next.js authentication authority

Not selected because Django already owns users, workspace authorization, and
application services. A second authority would require synchronization and
additional trust boundaries.

### Redis-backed sessions

Deferred. PostgreSQL already exists, and no measured session workload requires
another storage dependency.

### External identity provider

Deferred to future authentication requirements. MVP must remain straightforward
to self-host with email/password authentication.

## Consequences

The application uses Django's authentication facilities and centralizes session
control in the backend.

The deployment must preserve a single public origin, correctly forward cookies,
and configure HTTPS and trusted origins.

Database-backed sessions add database activity and require expired-session
cleanup. Idle and absolute timeouts require explicit implementation and
verification beyond merely setting a cookie lifetime.

Future native clients, public APIs, or federated login may require another
authentication mechanism through a new or superseding ADR.

## Acceptance criteria

- [x] Product owner accepts this ADR.
- [x] Confirm session timeouts, reset-link lifetime, and role permissions.
- [x] Confirm initial owner provisioning and disabled public registration.
- [x] Record implementation tasks for identity models, authentication, recovery, authorization, and deployment.
- [x] Define tests for CSRF, cookie behavior, session rotation, expiration, logout, and password-related revocation.
- [x] Define tests for inactive users, rate limiting, and reset-link expiration and reuse.
- [x] Define tests proving cross-workspace access fails and membership changes take effect.
- [x] Define tests preventing removal or demotion of the final owner.

Accepted by Brenson Go on 2026-10-22 after reviewing the proposed ADR. Acceptance
records the architecture decision. It does not mark authentication implementation
or Milestone 1 complete. Follow-up on 2026-10-22: implementation and test
definitions now exist, with rate-limit details in [ADR 0007](0007-implement-authentication-rate-limits.md)
and setup/deployment tasks in [authentication operation](../AUTHENTICATION.md).
Defined tests are not passing evidence: PostgreSQL execution, SMTP delivery, and
complete deployment verification remain open in
[authentication verification](../AUTHENTICATION_VERIFICATION.md).

## References

- [Django 5.2 sessions](https://docs.djangoproject.com/en/5.2/topics/http/sessions/)
- [Django 5.2 authentication](https://docs.djangoproject.com/en/5.2/topics/auth/default/)
- [DRF session authentication and login CSRF requirements](https://www.django-rest-framework.org/api-guide/authentication/#sessionauthentication)
