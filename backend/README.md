# E.O SALES LTD backend

This directory contains the backend for the E.O SALES LTD multi-vendor marketplace.

## Launch requirements

- Uganda-first launch, with prices stored as integer UGX amounts.
- Customer, seller, and administrator roles.
- Seller onboarding and approval before products can be published.
- Product catalogue, stock, multi-vendor orders, delivery, and collection-point fulfilment.
- English, Luganda, and Swahili language preferences.
- Planned payment methods: MTN Mobile Money, Airtel Money, Visa, and Mastercard.

## Development status

Repository write access has been verified and the backend scaffold is being added in stages. Payment processing must remain disabled until provider credentials, signed webhook verification, reconciliation, and security testing are configured. Do not store secrets in Git; use environment variables.

## Planned stack

- FastAPI REST API
- SQLAlchemy
- SQLite for local development and PostgreSQL for deployment
- JWT authentication and Argon2 password hashing

The API is not production-ready until migrations, automated tests, administrator workflows, payment integrations, deployment configuration, backups, and a security review are complete.
