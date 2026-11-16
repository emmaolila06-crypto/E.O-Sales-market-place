# E.O SALES LTD Marketplace

Uganda-first multi-vendor marketplace for E.O SALES LTD and approved independent sellers.

## Product direction
- Uganda launch with prices stored as integer UGX.
- Customer, seller, and administrator accounts.
- Seller onboarding and approval before product listings.
- Product catalogue, inventory, multi-vendor orders, delivery and collection.
- Language preferences: English, Luganda and Swahili.
- Planned payment methods: MTN Mobile Money, Airtel Money, Visa and Mastercard.

## Repository layout
- `backend/`: FastAPI service and SQLAlchemy data models.
- `docker-compose.yml`: local PostgreSQL and API development environment.

## Current backend milestone
The initial API scaffold provides registration/login, role checks, seller onboarding, product catalogue and seller product management, order creation, customer order history, seller order views, and administrator seller approval endpoints.

**Important:** payment methods are recorded as a customer's intended method only. The API does not charge money, confirm payment, or initiate payouts. Payment integration must not be enabled until provider contracts/credentials, signed webhook verification, idempotency, reconciliation, refunds and security testing are implemented.

## Run locally with Docker
1. Install Docker Desktop or Docker Engine.
2. From the repository root run:

```bash
docker compose up --build
```

3. Open `http://localhost:8000/docs` for API documentation and `http://localhost:8000/health` for the health check.

The compose file uses local-development credentials only. Change all passwords and secrets before any shared or hosted deployment.

## Run without Docker
From the `backend` directory:

```bash
python -m venv .venv
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The default local database is SQLite. For PostgreSQL, set `DATABASE_URL` to a PostgreSQL SQLAlchemy URL.

## Create the first administrator
Never expose public admin registration. Set `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_NAME`, and a strong `BOOTSTRAP_ADMIN_PASSWORD` in a private environment, then run from `backend/`:

```bash
python -m app.bootstrap_admin
```

Unset the bootstrap password after creating the administrator.

## Before production
This is an early development scaffold, not production-ready. Still required: Alembic migrations, automated tests, admin audit logs, email/phone verification, password reset, rate limits, image storage, expiring stock reservations and cancellation/restock flows, payment provider integrations and signed webhooks, delivery/collection-point operations, commission and payout ledger, HTTPS, monitoring, backups, privacy review and independent security review.
