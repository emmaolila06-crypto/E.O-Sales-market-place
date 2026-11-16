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
- `GET /seller/orders`, `GET /seller/earnings`, `GET /seller/payouts`, `POST /seller/payouts` (delivered paid balance only)
- `GET /admin/payouts`, `PATCH /admin/payouts/{id}/review` (approve for manual processing or reject)
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
This is a development foundation, not a production release. Checkout creates an unpaid order and reserves inventory; it does **not** process payments. Customers can cancel unpaid orders awaiting payment, which restores reserved stock. Do not represent an order as paid until a verified payment-provider webhook confirms settlement. Automatic reservation expiry, refunds and seller payouts are not implemented yet. Marketplace commission snapshots and paid-order earnings reports are now available; no earnings are treated as payable until a verified payment is confirmed.

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

These initial tests cover password hashing, JWT identity claims, supported language values, product and order validation, seller fulfilment input, and commission calculations. They are a starting point, not comprehensive integration or security tests.


## Web interfaces
- Administrator dashboard: `/admin/dashboard`
- Seller portal: `/seller/portal`

Both interfaces use the API's bearer-token login. Seller product publishing requires an administrator-approved seller profile. The seller portal supports inventory management, order-line fulfilment, paid-order earnings summaries and payout request history. Sellers can request only from paid and delivered order-line earnings; administrators can approve requests for manual processing or reject them. Actual transfers remain disabled until verified payment collection and a secure disbursement provider are integrated.


### Seller order fulfilment

Each order line now has its own fulfilment status so one seller cannot change another seller's part of a multi-vendor order. Sellers can advance only their own paid order items through processing, ready for collection or dispatched, and delivered. Apply database changes with `alembic upgrade head`. Seller fulfilment updates remain blocked until a trusted payment integration confirms the order as paid.


### Marketplace commission and earnings

The marketplace commission rate is configurable with `MARKETPLACE_COMMISSION_PERCENT` (default `10.0`). Each new order line stores the commission rate in basis points and the resulting UGX platform fee and seller net amount, so later rate changes do not rewrite historical order calculations. Seller earnings and administrator financial reports include confirmed paid orders only. Existing order lines created before this migration are assigned a 10% snapshot by the migration, but their fee and net amounts default to zero; review historical records before relying on those rows for accounting. Apply `alembic upgrade head` to add the commission columns. Payouts and actual money transfers remain disabled.


## Collection point management

Administrators can manage pickup locations from the Admin Dashboard under **Collection points**. Create a point with its name, district, full address, contact phone and opening hours, then activate or deactivate it. Customers see active collection points at checkout and orders store the selected collection point ID as well as a readable address snapshot. Apply the new database migration with `alembic upgrade head` before using this feature. Existing text-based collection details remain readable for historical orders.


## Delivery assignment and tracking

For paid home-delivery order items, an approved seller moves the item to **Dispatched** and supplies the delivery person's name and phone number. The API creates a unique E.O tracking reference and records the dispatch time. The customer sees the item status, tracking reference and courier contact in My Orders. The customer-only `GET /orders/{order_id}/tracking` endpoint returns the destination and item-level tracking history; it verifies order ownership. Sellers see only the delivery address for their own order items. Delivery status is updated by the seller when the parcel is delivered. This is an internal marketplace tracking workflow, not a live GPS or third-party courier integration. Apply migrations with `alembic upgrade head` before using it.


## Seller payout requests (preparation only)

Seller balances available for payout include only order lines that are both confirmed paid and marked delivered. Pending and administrator-approved-for-manual-processing requests reserve that balance so the same earnings cannot be requested twice. Sellers can submit a request with a mobile-money destination; administrators can approve it for manual processing or reject it, with a review note and history retained. **Approval is not a payment:** the system has no mobile-money disbursement integration and has no "paid" payout state. Do not tell sellers that funds have been transferred. Apply migration `0006_seller_payouts` with `alembic upgrade head` before using these routes.
