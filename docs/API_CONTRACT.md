# Shared API contracts

The implementation follows accepted ADRs [0008](adr/0008-standardize-api-contracts.md)
and [0009](adr/0009-make-financial-writes-idempotent.md). The generated specification
is [api/openapi.json](api/openapi.json); it describes the ten existing authentication
and health operations, not proposed financial endpoints.

## Inputs and responses

JSON mutation bodies must be objects with only the declared input fields.
Malformed/duplicate-key/nonfinite JSON fails with 400 `parse_error`; unknown
fields fail with 400 `validation_error`. Unsupported nonempty media types fail
with 415. Password confirmation is a client-side field and must not be submitted.

Successful shapes remain unchanged: CSRF bootstrap returns `csrf_token`, login
returns `user` plus the rotated `csrf_token`, `me` returns `user`, recovery/reset/
change return `detail`, and logout/activity return empty 204 responses. Session
cookies and Django CSRF remain mandatory as documented in
[authentication operation](AUTHENTICATION.md#api-and-deployment-contract).

Errors use one safe shape:

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

Codes are stable; human messages may evolve. Paths use JSON Pointer escaping;
the empty string denotes a whole-request issue. Only declared paths and fixed
safe messages are exposed, with at most 100 field errors. Unknown field names,
input values, exception messages, and credentials are not copied to responses.

The current status/code contract is:

| Status | Code |
|---|---|
| 400 | `validation_error`, `parse_error`, `invalid_credentials` |
| 403 | `authentication_required`, `permission_denied`, `csrf_failed` |
| 404 | `not_found` |
| 405 | `method_not_allowed`; retain `Allow` |
| 406 | `not_acceptable` |
| 415 | `unsupported_media_type` |
| 429 | `rate_limited`; retain `Retry-After` seconds |
| 500 | `internal_error` |
| 503 | `service_unavailable` for recognized operational connection failures |

Django CSRF and API 400/404/500 boundary handlers use the same safe envelope.
DRF exceptions and explicitly returned API errors are normalized. Anonymous
session denial remains 403; invalid login and recovery remain generic so account
existence is not disclosed. Session rotation, expiry, password revocation, workspace
authorization, and cookie protections still belong to their existing identity services.

Health responses are an intentional exception: `{"status":"ok"}` and
`{"status":"ready"}`, or readiness 503 `{"status":"unavailable"}`. Clients and
Compose verification can continue comparing these exact probe bodies. Errors
produced before Django by an edge/network may have another format; the frontend
uses a generic fallback rather than showing raw non-contract responses.

## Request correlation

Every application-generated `/api/v1` response includes `X-Request-ID`, a fresh
server-generated UUIDv4. An error's body contains the same identifier. Successful
bodies and empty 204 responses are not wrapped. All incoming caller IDs are
discarded, including valid UUIDs, malformed values, and repeated header values.

`config.api.middleware.request_id_context` makes the ID available while handling
a request and resets it on success/failure. Synchronous thread and asynchronous
request tests exercise isolation. It is a correlation label, never authentication
or an operation/idempotency key. A retry gets a fresh request ID.

The frontend preserves typed field errors, marks associated form controls, and
shows a matching server reference on failure. It sends same-origin cookies and
refreshes CSRF before mutations. Full structured logging/redaction is #15;
deployment/proxy header verification is #16. This change does not claim either gate.

## Generate and review OpenAPI

The selected drf-spectacular 0.30.0 works with the pinned Django 5.2.18, DRF 3.18.3,
and Python 3.14 runtime. The initial isolated smoke check used Python 3.14.8 and
proved generation, OpenAPI 3.0.3 validation, and a decorated APIView HTTP response.
Repository contract/integration checks exercise the actual view annotations next.
Exact dependencies and their transitive locks are in pyproject.toml/uv.lock.

From the repository root:

```powershell
uv run --locked python infra/check_api_schema.py
uv run --locked python infra/check_api_schema.py --update
```

The first command validates generation with warnings treated as failures and
compares deterministic JSON with the committed artifact; drift/missing files
return nonzero. The second writes a candidate artifact. Review its diff alongside
the executable route/serializer changes, then rerun checks. Never edit the generated
file manually or use regeneration alone as proof runtime responses conform.

The script forces isolated test settings, does not read `.env`, and requires no
application database or production credentials. CI runs its check, and tests
validate actual anonymous/authenticated responses against their documented shapes,
including UUID/email formats, status codes, headers, and the health exception.
Input schemas expose rejection of additional properties. Session authentication
uses `cookieAuth`; unsafe operations document both CSRF header and cookie, even
on anonymous login/recovery. There is no JWT/Bearer scheme.

`GET /api/v1/schema` serves JSON only in local development settings. The serving
endpoint is omitted from the public contract and is absent in test/production
settings by default. No Swagger/Redoc UI or remote documentation scripts are added.

## Scope for future collections and financial operations

No current endpoint needs pagination: authentication/health return single results,
and `me` retains its existing workspace representation. Do not add placeholder
financial collections or enable pagination globally on singleton responses.
When a real collection arrives, implement ADR 0008's signed composite cursor,
50/100 page-size limits, filter/scope binding, 24-hour cursor expiry, and boundary
tests with the owning route. Default DRF cursor encoding alone is not that contract.

No current authentication/health request uses `Idempotency-Key`. In particular,
password/session/CSRF responses must never be cached or replayed. Milestone 2's
ledger services implement ADR 0009's durable scoped identity, canonical command,
immutable receipt, PostgreSQL uniqueness/locking, and actual concurrency/rollback
tests. Imports add confirmed batch/row identity in their owning milestone.
Extend the shared error-code/OpenAPI declarations with the accepted financial
conflict/replay codes when those operations exist; a generic HTTP helper does not
prove monetary correctness or posting idempotency.

Retention/access and recovery follow ADRs [0010](adr/0010-define-data-retention-and-deletion.md)
and [0011](adr/0011-define-backup-and-recovery-targets.md). This issue creates no
financial model, expiry job, backup workflow, or successful-posting response cache.
