import os
import sys

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import User
from app.security import hash_password


def main() -> None:
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
    name = os.getenv("BOOTSTRAP_ADMIN_NAME", "").strip()
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")

    if not email or not name or len(password) < 14:
        print("Set BOOTSTRAP_ADMIN_EMAIL, BOOTSTRAP_ADMIN_NAME and BOOTSTRAP_ADMIN_PASSWORD (at least 14 characters).", file=sys.stderr)
        raise SystemExit(2)

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            user.role = "admin"
            user.is_active = True
            user.password_hash = hash_password(password)
            user.full_name = name
        else:
            user = User(
                email=email,
                full_name=name,
                password_hash=hash_password(password),
                role="admin",
                language="en",
                is_active=True,
            )
            db.add(user)
        db.commit()
        print(f"Administrator account ready for {email}. Remove BOOTSTRAP_ADMIN_PASSWORD from the environment now.")


if __name__ == "__main__":
    main()
