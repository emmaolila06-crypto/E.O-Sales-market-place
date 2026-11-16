"""Create the first administrator from private environment variables.

Run from the backend directory:
  BOOTSTRAP_ADMIN_EMAIL=... BOOTSTRAP_ADMIN_NAME=... BOOTSTRAP_ADMIN_PASSWORD=... python -m scripts.create_admin

This is a local/server CLI only; it is not exposed as an HTTP endpoint.
"""
import os
import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.security import hash_password


def main() -> int:
    email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
    full_name = os.environ.get("BOOTSTRAP_ADMIN_NAME", "").strip()
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")

    if not email or "@" not in email or not full_name or len(full_name) < 2:
        print("Set a valid BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_NAME.", file=sys.stderr)
        return 2
    if len(password) < 14:
        print("BOOTSTRAP_ADMIN_PASSWORD must be at least 14 characters.", file=sys.stderr)
        return 2

    db = SessionLocal()
    try:
        if db.scalar(select(User.id).where(User.role == "admin").limit(1)):
            print("An administrator already exists; bootstrap is disabled.")
            return 1
        if db.scalar(select(User.id).where(User.email == email)):
            print("That email already belongs to an account. Use a different admin email.")
            return 1

        admin = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role="admin",
            language="en",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"Administrator account created for {email}. Keep its password private.")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
