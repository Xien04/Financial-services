# Financial Services

Financial Services is a privacy-first, self-hostable personal-finance application for managing Philippine-peso accounts, transactions, imports, budgets, recurring expenses, liabilities, savings goals, and financial reporting. Its accounting core will use immutable ledger entries behind a familiar transaction interface so transfers, splits, refunds, and liabilities produce trustworthy balances.

## Status

**Planning / Stage 0.** The product and architecture blueprint is documented, but the Django API, Next.js interface, database, and automated tests have not been scaffolded yet. See the [roadmap](docs/ROADMAP.md) for delivery status.

## Planned stack

- Next.js, React, and TypeScript for the web interface
- Django and Django REST Framework for the API and financial domain
- PostgreSQL for durable relational data
- Celery and Redis for background work
- Docker Compose for local and self-hosted deployment
- Local or S3-compatible object storage for imports and attachments

## Local setup

There is no runnable application in the repository yet. To prepare local configuration:

```powershell
git clone <repository-url>
cd financial-services
Copy-Item .env.example .env
```

On macOS or Linux, use `cp .env.example .env`. Populate `.env` with local values; never commit it. Runtime installation and startup commands will be added during Stage 1 when the Django and Next.js projects exist. `requirements.txt` is intentionally empty until the Python application is scaffolded and exact dependencies can be locked.

## Configuration

Required and optional variable names are documented in [.env.example](.env.example). Secrets must be supplied through environment variables or an ignored local secrets file. Never commit service-account JSON, tokens, database passwords, or application encryption keys.

## Testing

Automated tests do not exist yet. Stage 1 will add the project-level test commands; Stage 2 requires unit and property-based coverage for every monetary calculation, split, transfer, refund, opening balance, and reconciliation rule.

## Documentation

- [Product architecture](docs/PRODUCT_ARCHITECTURE.md)
- [Financial semantics](docs/FINANCIAL_SEMANTICS.md)
- [Delivery roadmap](docs/ROADMAP.md)
- [Architecture decision records](docs/adr/README.md)
