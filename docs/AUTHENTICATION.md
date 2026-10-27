# Authentication setup and operation

Implementation follows [ADR 0006](adr/0006-use-django-sessions-for-browser-authentication.md)
and [ADR 0007](adr/0007-implement-authentication-rate-limits.md). Public signup is
disabled. The browser uses Django's PostgreSQL sessions, with a 30-minute idle
timeout and a 12-hour absolute lifetime. There is no remember-me option.

## First account

Apply migrations before creating the owner. With the README Compose environment:

```powershell
docker compose run --rm api python manage.py migrate --noinput
docker compose run --rm api python manage.py provision_owner
```

The interactive command asks for an email, display name, timezone, workspace name,
and a hidden, confirmed password. No default credentials or password arguments
exist. It creates exactly one initial owner and personal PHP workspace atomically;
rerunning it after any user exists fails. Use at least 12 characters and avoid
common passwords or personal details. Do not pipe passwords or record the prompt.

For host development, use `uv run --env-file .env python backend/manage.py` with
the same subcommands and a reachable PostgreSQL database. `.env` values are never
loaded implicitly by Django.

Open the application, sign in, and verify the displayed workspace. Password
change is available on the signed-in home screen. It requires the current
password and signs every session out, including the requesting browser.

## Password recovery and email

Set `APP_URL` to the actual public origin (for example the local frontend origin)
and configure `EMAIL_HOST`, `EMAIL_PORT` (default 587), `EMAIL_HOST_USER`,
`EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` (default true), and `DEFAULT_FROM_EMAIL`.
Production requires an HTTPS origin, explicit hosts and trusted HTTPS CSRF
origins, plus an email host and sender. A local SMTP catcher can be used for
development. Do not enable console/file email backends that print or retain reset
links in application logs or repository files.

Choose **Forgot password?** on the sign-in screen. The response is the same for
existing, nonexistent, and inactive accounts. Links expire after one hour and
are single-use. The form removes the reset fragment from the address/history;
reopen the email link if you refresh the form. A successful reset requires a fresh
login and invalidates all old sessions on their next authenticated request.
Email failures produce a generic sanitized log message; inspect SMTP settings
without recording messages, tokens, account credentials, or complete request bodies.

If email is unavailable, an authorized operator with host/container access can run:

```powershell
docker compose run --rm api python manage.py recover_owner
```

This securely prompts for the active account and a new password and invalidates
all its existing sessions. Protect shell access as an administrative capability.

## Limits and maintenance

| Environment variable | Default | Window |
|---|---:|---|
| `AUTH_LOGIN_ACCOUNT_LIMIT` | 5 | 15 minutes |
| `AUTH_LOGIN_IP_LIMIT` | 30 | 15 minutes |
| `AUTH_RECOVERY_ACCOUNT_LIMIT` | 3 | 1 hour |
| `AUTH_RECOVERY_IP_LIMIT` | 10 | 1 hour |
| `AUTH_RESET_ACCOUNT_LIMIT` | 10 | 1 hour |
| `AUTH_RESET_IP_LIMIT` | 30 | 1 hour |

All counts must be positive; blank optional settings use the defaults.
PostgreSQL counters enforce budgets across workers. IP means the
trusted Django peer address; forwarded IP headers are ignored. The local Next.js
proxy shares a peer-IP budget. Before public deployment, configure and verify a
trusted edge that supplies real client addresses, or account for shared budgets.
Do not expose a spoofable forwarding configuration. Database failure denies
authentication attempts rather than bypassing the limiter.

Run these daily through the operator's scheduler:

```powershell
docker compose run --rm api python manage.py clearsessions
docker compose run --rm api python manage.py clear_auth_limits
```

Expired/revoked sessions cannot authenticate even before their database rows are
removed. Do not clear live rate-limit buckets as routine maintenance.

## API and deployment contract

All endpoints use `/api/v1/auth/`. JSON mutations require a CSRF cookie and
`X-CSRFToken`, including anonymous login and recovery. Bootstrap with `GET csrf`.
Login rotates session and CSRF tokens; bootstrap again before subsequent
mutations. The frontend uses same-origin credentials and never stores bearer
tokens. POST logout is idempotent; GET logout is rejected.

| Method | Suffix | Purpose |
|---|---|---|
| GET | `csrf` | Return masked CSRF token and set cookie |
| POST | `login` | Email/password login; return current user and memberships |
| GET | `me` | Current user and live workspace memberships; never renew idle time |
| POST | `activity` | Renew idle time after real user input |
| POST | `logout` | Revoke current session and clear its cookie |
| POST | `password/recover` | Generic email-recovery response |
| POST | `password/reset` | Submit `uid`, `token`, and `new_password` |
| POST | `password/change` | Submit `current_password` and `new_password`; revoke sessions |

Production cookies are Secure, HttpOnly, SameSite=Lax, host-only, path `/`.
Local settings explicitly permit HTTP. Keep web and API on one public origin,
preserve the public Origin/Host through the proxy, and terminate HTTPS at a trusted
edge. Current Compose remains local-only. No arbitrary forwarded-protocol trust
is enabled; a production TLS gateway/serving configuration remains separate work.
Never cache authentication responses or personalized data. Next.js generates a
fresh CSP nonce per page; the dynamic authentication HTML must not be cached.

The identity service exposes workspace membership selectors and role checks with
no staff/superuser bypass. Owner/editor may write, import, and reconcile; only
owners may export, manage membership, or request deletion. Final-owner protection
exists in the membership service. These are internal foundations; no member
administration UI or financial API is added by this task. Future services and
queries must still enforce these policies for each owned object.

## Verification

Run the checks in [TESTING.md](TESTING.md). The PostgreSQL suite includes login,
session rotation, CSRF, cookie flags, deactivation, idle/absolute expiry,
password-related session revocation, reset expiry/reuse, shared counters,
workspace access, final-owner protection, and concurrent reset/provision races.
Component tests cover sign-in, errors/retry, recovery, reset fragments, password
confirmation, sign-out, and user-driven activity. Full browser and actual SMTP
delivery verification remain separate from component tests.
