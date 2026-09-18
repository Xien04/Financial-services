# ADR 0001: Use a Django modular monolith

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-08-18 |
| Accepted by | Brenson Go on 2026-09-18 |
| Decision owners | Product owner and engineering |
| Related documents | [Product architecture](../PRODUCT_ARCHITECTURE.md), [financial semantics](../FINANCIAL_SEMANTICS.md), [product wireframes](../PRODUCT_WIREFRAMES.md) |

## Context

Financial Services has strongly related financial domains, transaction-wide atomicity requirements, shared workspace authorization, and no demonstrated need for independently operated services. Authentication, relational migrations, administration, background work, imports, and reporting all depend on one trustworthy ledger foundation.

The repository currently has no accepted physical application layout. Stage 1 needs a layout that keeps domain ownership explicit without creating distributed-system boundaries prematurely.

## Decision

Build the backend as one Django and Django REST Framework deployment organized as a modular monolith. Build the responsive client as a Next.js and TypeScript application in the same repository. Deploy the client, API, Celery worker, PostgreSQL, and Redis as separately configurable processes/containers while keeping one backend codebase and one authoritative PostgreSQL database.

### Backend module boundaries

The Django package contains these owning modules:

| Module | Owns |
|---|---|
| `identity` | Users, workspaces, membership, roles, tenant authorization |
| `ledger` | Accounts, categories, tags, transactions, entries, balances, reconciliation |
| `imports` | Uploads, mappings, staging rows, duplicate review, posting orchestration |
| `planning` | Budgets, recurring items, subscriptions, and goals |
| `reporting` | Dashboard metrics, reports, drill-down definitions, and exports |
| `integrations` | Object storage and future provider-neutral external adapters |

Modules expose application/domain services. API views, serializers, tasks, management commands, and other modules call those services rather than writing another module's models directly. Cross-module writes use an explicit application service and one database transaction.

Celery workers import and execute the same application services as the API. Jobs receive identifiers, reload authoritative state, and remain safe to retry. No module becomes a separately deployed service during MVP.

### Repository layout

Adopt this physical layout when Stage 1 scaffolding begins:

```text
/
├── backend/
│   ├── manage.py
│   ├── config/                       # Django settings, URL/ASGI/WSGI, Celery setup
│   ├── financial_services/
│   │   ├── identity/
│   │   ├── ledger/
│   │   ├── imports/
│   │   ├── planning/
│   │   ├── reporting/
│   │   └── integrations/
│   └── tests/
│       ├── integration/
│       └── contract/
├── frontend/
│   ├── src/
│   │   ├── app/                      # Next.js routes and layouts
│   │   ├── features/                 # UI grouped by product workflow/domain
│   │   └── lib/                      # Shared API client and presentation utilities
│   └── tests/
├── infra/                            # Container definitions and operational scripts
├── docs/
├── compose.yaml
├── .env.example
└── README.md
```

Each Django owning module keeps its models, migrations, services, domain rules, API boundary, and module-level tests together. Cross-module integration/contract tests live under `backend/tests`. Frontend features may mirror product concepts for navigation and presentation, but they do not become alternate owners of financial rules.

The root `compose.yaml` is the local/self-hosting orchestration entry point. Environment-specific secrets remain outside the repository.

### API and integration boundary

- Expose versioned REST/JSON under `/api/v1` and generate OpenAPI from the implementation.
- Keep financial and authorization behavior in backend services, not serializers or React code.
- Put provider-specific code behind interfaces in `integrations`; normalized data enters `imports` before ledger posting.
- Use asynchronous jobs only for work that benefits from retry/background execution; synchronous financial posting remains transactional.

## Alternatives considered

### Microservices

Rejected for MVP because they would introduce distributed transactions, duplicated authorization, additional deployment/observability work, and failure modes without evidence of independent scaling needs.

### FastAPI backend

Not selected because the product is dominated by relational modeling, authentication, migrations, administration, and transactional workflows. FastAPI would require assembling more of this infrastructure. It remains a future alternative only through a superseding ADR.

### Django-rendered interface without Next.js

Not selected because the accepted responsive workflows benefit from a dedicated client application and typed API boundary. The backend remains the only accounting engine.

### Separate repositories

Not selected for MVP because coordinated contract, environment, and end-to-end changes are easier to review and test in one repository.

## Consequences

### Positive

- Ledger operations, tenant checks, audit changes, and imports can commit atomically.
- Domain ownership remains explicit without network boundaries.
- One repository supports coordinated API/client contracts and local Docker Compose setup.
- Celery reuses the same domain services and validation rules.
- Modules can be extracted later only if measured operational needs justify it.

### Costs and constraints

- Module boundaries require review discipline because Python imports make accidental coupling easy.
- The entire backend is normally released as one unit.
- A shared database can tempt cross-module queries; owning services must remain the supported boundary.
- Next.js and Django require coordinated development tooling and contract tests.

## Acceptance criteria

- [x] Product owner accepts the Django/DRF modular-monolith direction.
- [x] Product owner accepts the Next.js client in the same repository.
- [x] Product owner accepts the module ownership table.
- [x] Product owner accepts the physical repository layout.
- [x] Product owner accepts one backend deployment codebase and one authoritative database for MVP.

Accepted on 2026-09-18. Stage 1 scaffolding follows this decision; changing it requires a superseding ADR.
