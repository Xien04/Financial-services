# ADR 0008: Standardize API errors, request IDs, documentation, and pagination

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-10-27 |
| Decision owners | Brenson Go (product owner) and engineering |
| Accepted by | Brenson Go on 2026-10-27 |
| Related work | [Decision issue #12](https://github.com/Xien04/Financial-services/issues/12), [implementation #14](https://github.com/Xien04/Financial-services/issues/14), [logging #15](https://github.com/Xien04/Financial-services/issues/15) |
| Related records | [ADR 0001](0001-use-django-modular-monolith.md), [ADR 0006](0006-use-django-sessions-for-browser-authentication.md), [ADR 0007](0007-implement-authentication-rate-limits.md), [ADR 0009](0009-make-financial-writes-idempotent.md) |

## Decision in plain language

Give the application one set of rules for explaining mistakes, tracing requests,
describing its API, and showing long lists. Keep the existing login and health
behavior compatible while adding those rules.

| Topic | Decision | Example |
|---|---|---|
| Error messages | One predictable JSON format with a safe message and a stable error code | A missing email identifies the email field |
| Tracking requests | Django creates a fresh tracking UUID for every attempt | A user can report the tracking number of a failed save |
| API instruction book | Generate OpenAPI with drf-spectacular from the implemented routes | Changing a response also requires updating its checked contract |
| Long lists | Cursor pagination; 50 items by default, at most 100 | Load the next group without counting past thousands of entries |
| Page expiration | A page cursor expires after 24 hours | Restart the list if its old bookmark has expired |

The product owner accepted these rules on 2026-10-27. Acceptance records the
architecture decision; API behavior, dependencies, and milestone completion
still require the implementation and verification described below.

## Context

The application already exposes authentication and health endpoints under
`/api/v1`. Authentication uses Django sessions and CSRF under ADRs 0006–0007.
Current errors mix serializer field dictionaries, `detail` messages, and Django
framework responses. The frontend currently reads `detail`. No common request-ID,
generated OpenAPI, or pagination implementation exists.

Issue #12 needs explicit decisions before #14 implements these conventions.
Financial rules remain governed by the accepted financial semantics and ledger
ADRs; this decision defines their HTTP representation and shared boundaries.

## Decision

### 1. Preserve the versioned JSON boundary

- Keep `/api/v1`, current route spelling, and the single public origin. Do not
  introduce another authentication authority or bearer tokens.
- Keep existing successful response shapes. Singleton responses do not acquire
  a generic `data` wrapper. A successful POST uses the route's documented status:
  existing authentication operations retain 200/204; future creation uses 201
  and accepted background work uses 202. A 204 response has no JSON body.
- Accept JSON for JSON mutations. Reject malformed JSON, duplicate object keys,
  unknown input fields, and unsupported media types. Distinguish absent, null,
  and blank values in serializers; do not silently discard invalid inputs.
- Represent monetary API values as decimal strings, UUIDs as strings, financial
  dates as `YYYY-MM-DD`, and event timestamps in UTC with an explicit offset.
  Apply the accepted PHP precision and rounding rules; transport code never
  computes or rounds financial values independently.

### 2. Use one safe error format

Applicable API errors use `Content-Type: application/json` and these fields:

```json
{
  "code": "validation_error",
  "detail": "Check the highlighted fields.",
  "errors": [
    {"path": "/email", "code": "required", "message": "This field is required."}
  ],
  "request_id": "3fbbcd4f-b207-4712-bcbd-1b55da617db6"
}
```

`code` and field-level codes are stable identifiers for client behavior. `detail`
and `message` are safe human-readable text. `errors` is always an array, empty
for non-field failures. Paths use JSON Pointer escaping and array indices;
the empty string identifies a whole-request error. Do not echo unknown field
names, rejected values, passwords, reset credentials, or other submitted data.

| HTTP status | Meaning / representative code |
|---|---|
| 400 | Invalid input (`validation_error`), malformed JSON (`parse_error`), invalid credentials (`invalid_credentials`), or invalid cursor (`invalid_cursor` / `cursor_expired`) |
| 403 | Missing/expired session (`authentication_required`), denied permission (`permission_denied`), or failed CSRF (`csrf_failed`) |
| 404 | Missing resource or a resource outside the caller's visible workspace (`not_found`) |
| 405 | Unsupported method (`method_not_allowed`); preserve `Allow` |
| 406 | Unsupported response format (`not_acceptable`) |
| 415 | Unsupported request media type (`unsupported_media_type`) |
| 409 | A state or idempotency conflict, with the specific stable code in ADR 0009 |
| 429 | Rate limit exceeded (`rate_limited`); preserve `Retry-After` |
| 500 | Unexpected failure (`internal_error`); generic message only |
| 503 | Recognized temporary dependency failure (`service_unavailable`) |

Preserve session authentication's existing 403 behavior. A user may receive 403
for a role denial in a workspace they can see; foreign workspace/object identifiers
receive the same 404 shape as missing ones. Invalid login remains generic, and
recovery retains the same generic successful response regardless of account
existence. Do not expose framework exception strings or CSRF failure reasons.

Normalize DRF exceptions, explicitly returned error responses, Django API 404/500
handlers, and CSRF failures through the same contract. Preserve required headers
such as `Allow` and `Retry-After`. Errors must not turn failures into HTTP 200.
Client-controlled field paths must use known schema names and bounded indices;
cap field errors at 100 entries and use a fixed safe message for unknown fields.

Intentional exception: health probes keep their existing small bodies, including
readiness `503 {"status":"unavailable"}`. Document this exception in OpenAPI.
Failures generated before Django by a proxy, web server, or network cannot be
normalized here. The frontend must retain a safe fallback for non-JSON failures.

### 3. Generate request IDs at the application boundary

Django creates a fresh UUIDv4 before API handling and sets `X-Request-ID` on every
application-generated API response, including errors and health responses. The
error body's `request_id` equals that header. Successful bodies remain unchanged.

Treat every incoming `X-Request-ID` as untrusted: replace it, including a valid
UUID. Missing, malformed, oversized, or repeated headers never become log fields
or cause a separate client error. This intentionally chooses server generation
over accepting caller IDs; arbitrary strings must never reach logs or responses.
Trusted-proxy ID adoption would require a later explicit decision.

Carry the generated ID through request-scoped logging context without leaking it
between concurrent requests. #15 implements structured/redacted logging against
this contract. #16 verifies that the deployment preserves the response header.
An ID is a correlation label, never authentication, authorization, or an
idempotency key. A retry receives a new request ID and reuses its operation key.

### 4. Generate and check the API instruction book

Select **drf-spectacular** to generate **OpenAPI 3.0.3** from executable Django/DRF
routes, serializers, and explicit annotations for custom APIViews. Use separate
request/response components and stable operation IDs. Include actual success
and error schemas, response headers, and the health exception.

Describe the configured session cookie as cookie authentication. Mark genuinely
anonymous operations as anonymous; document that unsafe browser requests still
require `X-CSRFToken`, including anonymous login/recovery. Document the CSRF
bootstrap and token rotation after login without placing live values in examples.
Do not advertise JWT/Bearer authentication or suggest CSRF is optional.

#14 adds and exactly pins a compatible release through uv when application code
uses it. Compatibility with the repository's Python 3.14, Django 5.2.18, and DRF
3.18.3 must be proved in that change. Upstream's published requirements currently
list DRF only through 3.17; that is a compatibility risk, not proof of failure.
Do not silently downgrade the stack or substitute tooling; return to this ADR if
no compatible release passes the checks.

Keep a deterministic generated contract at `docs/api/openapi.json`. CI must
generate it using isolated test settings, validate it with warnings treated as
failures, and compare it with the committed file. Tests must exercise actual
route responses, statuses, and security behavior against the documented contract;
regenerating a file alone does not prove accuracy. Generation must not require
production credentials or query live application data.

Serve JSON schema at `/api/v1/schema` in development only; disable that route in
production for MVP and distribute the generated repository artifact instead.
Interactive Swagger/Redoc pages, CDN scripts, and generated client SDKs are
deferred. This avoids adding a browser documentation interface to the strict CSP.

### 5. Use bounded, signed cursor pagination for future collections

Future large collections return `results`, `next`, and `previous`; links are
relative to the public origin or null. Omit an automatic total count. Default
`page_size` is 50; accept integers 1–100 and return 400 outside that range.

Use keyset boundaries over the immutable tuple `(created_at, id)`, descending,
with UUID as the unique tie-breaker. Support forward/backward navigation without
offsets, including equal timestamps. A route needing another sort must document
its stable tuple and tests before exposing it. Financial-date filtering retains
its accepted meaning; creation order does not redefine a financial date.

The opaque cursor is a URL-safe, timestamp-signed, versioned JSON value using
Django signing with a dedicated pagination salt and a 24-hour maximum age. Bind
it to route, workspace, user, normalized filter digest, ordering, page size,
direction, and boundary tuple. Store no raw search text or financial payload in
the token; signing prevents tampering and does not encrypt its contents.
Reject tokens over 4096 characters, malformed/tampered tokens, and mismatched
route/filter/scope with 400 `invalid_cursor`. An expired token gives 400
`cursor_expired`; the client restarts the list. Authenticate and authorize before
using the cursor and reapply current workspace filters on every page.

Empty collections have empty results and null links. Navigation uses the strict
tuple boundary even if its source row is later removed. Pages are a live view,
not a frozen export: additions, voids, and authorization changes may change what
is visible between requests. A snapshot/export protocol needs its own decision.

No current route needs pagination: health and authentication return singleton
results. Keep `/auth/me`'s current embedded workspace membership representation;
revisit it when a real membership-list workflow exists. #14 must not invent a
financial list endpoint or an unused database model to demonstrate this contract.

## Examples to turn into contract tests in #14

| Scenario | Required outcome |
|---|---|
| GET `/api/v1/health/live` | 200, unchanged `{"status":"ok"}`, fresh `X-Request-ID` |
| POST login without CSRF | 403 `csrf_failed`, standard safe envelope, matching ID header/body |
| POST login with valid CSRF and missing email | 400 `validation_error`, `/email` field error |
| POST login with wrong credentials | 400 `invalid_credentials`, no account-existence disclosure |
| GET `/api/v1/auth/me` without a session | 403 `authentication_required` |
| GET an unknown API route | 404 `not_found`, no debug page |
| POST logout successfully | 204, empty body, request-ID header |
| Framework exception containing a synthetic sensitive value | Generic 500; neither value nor traceback in response |
| Incoming caller ID, malformed ID, or concurrent requests | Caller ID discarded; generated IDs remain isolated |
| Regenerated schema differs or has a warning | Contract check fails until the implementation/schema is corrected |

Future collection tests must cover equal timestamps, both directions, empty/end
pages, invalid/expired cursors, changed filters, current permissions, and concurrent
inserts. These become executable tests when a real collection is implemented;
this document does not claim those tests exist or pass.

## Alternatives considered

- **Keep endpoint-specific errors:** less initial work, but every client must
  guess how to interpret validation and framework failures.
- **RFC 9457 Problem Details:** a valid standard alternative. The selected small
  JSON envelope preserves the client's existing `detail` access and keeps one
  media type. It is deliberately not described as RFC 9457 compliant.
- **DRF's built-in OpenAPI generator / handwritten schemas:** upstream deprecates
  its built-in generation in favor of packages such as drf-spectacular; a separate
  handwritten contract is more likely to drift from executable views.
- **Caller-provided tracking IDs:** useful across trusted infrastructure, but no
  trusted ID source exists today; generating them in Django gives one authority.
- **Page numbers or offsets:** simpler bookmarks, but poorer behavior for large,
  changing ledgers. Built-in cursor pagination is an option only if it satisfies
  the signed composite-boundary contract; do not assume its default token does.

## Consequences and delivery boundary

One safe error contract simplifies the client and support. #14 must update the
frontend's field-error handling and existing response assertions together. New
strict validation may reject inputs that previously slipped through; document
that behavior. Adding a schema package and signed keyset pagination brings
maintenance/testing work. Cursor expiry may require restarting a list.

#12 records accepted decisions only. #14 implements applicable current contracts;
#15 implements logging; Milestone 2 adds real collection/domain behavior. Keep
Milestone 1 checkboxes and #12 acceptance IDs open until their own gates are met.

## Acceptance record

- [x] Brenson Go accepts the error envelope, validation rules, and status choices.
- [x] Brenson Go accepts server-generated request IDs and incoming-ID replacement.
- [x] Brenson Go accepts the OpenAPI tool, compatibility gate, and publication scope.
- [x] Brenson Go accepts pagination defaults, ordering, cursor binding, and expiry.
- [x] Record explicit acceptance/date and link the accepted record from #12/#14.

Accepted by Brenson Go on 2026-10-27 after reviewing ADRs 0008–0009 in
[PR #21](https://github.com/Xien04/Financial-services/pull/21). The product owner's
explicit confirmation was: "Both documents are accepted."

This accepts the decision, including the tooling compatibility gate. It does not
claim implementation or Milestone 1 is complete. Issue #12 remains open until
PR #21 is merged; #14 implements the applicable current API conventions.

## References

- [DRF exception handling](https://www.django-rest-framework.org/api-guide/exceptions/)
- [DRF session authentication](https://www.django-rest-framework.org/api-guide/authentication/#sessionauthentication)
- [DRF schema tooling guidance](https://www.django-rest-framework.org/api-guide/schemas/)
- [drf-spectacular requirements and capabilities](https://drf-spectacular.readthedocs.io/en/latest/readme.html)
- [Schema validation with warnings treated as failures](https://drf-spectacular.readthedocs.io/en/latest/client_generation.html)
- [DRF pagination guidance](https://www.django-rest-framework.org/api-guide/pagination/#cursorpagination)
- [Django signing and timestamp validation](https://docs.djangoproject.com/en/5.2/topics/signing/)
- [RFC 9457: Problem Details](https://www.rfc-editor.org/rfc/rfc9457.html)
