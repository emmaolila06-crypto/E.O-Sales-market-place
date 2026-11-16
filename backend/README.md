# E.O SALES LTD API

FastAPI backend for the Uganda-first E.O SALES LTD multi-vendor marketplace.

## Local setup
From this directory:

```bash
python -m venv .venv
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

For a local PostgreSQL instance, set `DATABASE_URL` in your private `.env` file. The root `docker-compose.yml` starts PostgreSQL and the API together.

## API routes
- `GET /health`
- `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- `GET /seller/me`
- `GET /products`, `GET /products/{id}`, `POST /products`, `PATCH /products/{id}`
- `POST /orders`, `GET /orders/my`, `POST /orders/{id}/cancel` (unpaid orders only; restores stock)
- `GET /seller/orders`
- `GET /admin/dashboard` (admin web interface; dashboard data APIs require admin login)
- `GET /admin/overview`, `GET /admin/sellers/all`, `GET /admin/products`, `GET /admin/orders`
- `POST /admin/sellers/{id}/approve`, `POST /admin/sellers/{id}/reject`
- `POST /admin/products/{id}/activate`, `POST /admin/products/{id}/deactivate`
- `PATCH /admin/orders/{id}/status` (only after payment is confirmed)

Interactive API documentation is available at `/docs` while the service is running. The administrator web dashboard is served at `/admin/dashboard`.

## Seller onboarding
Seller registrations create a pending seller profile. An administrator must approve the profile before the seller can publish products.

## First administrator
First apply the database migrations with `alembic upgrade head` from this directory. Then set `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_NAME`, and `BOOTSTRAP_ADMIN_PASSWORD` (minimum 14 characters) in the process environment, and run:

```bash
python -m app.bootstrap_admin
```

The command creates or promotes that account to administrator and resets its password. Remove the bootstrap password from the environment immediately afterward. Never expose admin registration publicly.

## Important limitations
This is a development foundation, not a production release. Checkout creates an unpaid order and reserves inventory; it does **not** process payments. Customers can cancel unpaid orders awaiting payment, which restores reserved stock. Do not represent an order as paid until a verified payment-provider webhook confirms settlement. Automatic reservation expiry, refunds, commission accounting and seller payouts are not implemented yet.

Database tables are created with SQLAlchemy `create_all` in development. The Docker image runs `alembic upgrade head` before starting the API. Before production launch, verify the migration against the target PostgreSQL database and take a backup. Also required: comprehensive integration tests, audit logs, account verification and recovery, rate limiting, secure image storage, provider-specific payment integrations, delivery and collection-point workflows, monitoring, backups and an independent security review.


## Database migrations
For environments using Alembic, run from the `backend/` directory:

```bash
alembic upgrade head
```

Create a new migration after changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe schema change"
```

Review generated migration files before applying them. Development mode creates tables automatically for convenience; production mode expects migrations to be applied before the API starts.

## Run automated checks
From `backend/`:

```bash
pip install -r requirements.txt
pytest
```

These initial tests cover password hashing, JWT identity claims, supported language values, positive UGX product prices, partial product updates, and order input validation. They are a starting point, not comprehensive integration or security tests.


## Web interfaces
- Administrator dashboard: `/admin/dashboard`
- Seller portal: `/seller/portal`

Both interfaces use the API's bearer-token login. Seller product publishing requires an administrator-approved seller profile. The seller portal currently supports viewing the seller's inventory, adding products, and viewing order lines. It is an initial portal, not yet a complete earnings/payout interface.


### Seller order fulfilment

Each order line now has its own fulfilment status so one seller cannot change another seller's part of a multi-vendor order. Sellers can advance only their own paid order items through processing, ready for collection or dispatched, and delivered. Apply database changes with `alembic upgrade head`. Seller fulfilment updates remain blocked until a trusted payment integration confirms the order as paid.
