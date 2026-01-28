from __future__ import annotations

import os

from sqlalchemy import select

# ensure models are loaded
from app.db.base import Base  # noqa: F401
import app.models  # noqa: F401

from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User, UserRole


def create_super_admin(username: str, email: str, password: str, full_name: str | None = None):
    db = next(get_db())  # correct way to use dependency generator

    try:
        stmt = select(User).where(User.is_super_admin.is_(True))
        existing = db.execute(stmt).scalar_one_or_none()

        if existing:
            print("Super admin already exists:", existing.username)
            return

        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=UserRole.ADMIN,
            is_super_admin=True,
            password_hash=hash_password(password),
            is_active=True,
            is_approved=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        print("Super admin created successfully!")
        print("ID:", user.id)
        print("Username:", user.username)

    finally:
        db.close()


if __name__ == "__main__":
    username = os.getenv("SUPER_ADMIN_USERNAME", "superadmin")
    email = os.getenv("SUPER_ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("SUPER_ADMIN_PASSWORD", "supersecret123")
    full_name = os.getenv("SUPER_ADMIN_FULL_NAME", "Super Admin")

    create_super_admin(username, email, password, full_name)
