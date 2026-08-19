# backend/app/scripts/create_super_admin.py
"""
Create the first super-admin account (no defaults, no hard-coded credentials).

Usage (from backend/, with DATABASE_URL + SECRET_KEY configured):

    set SUPER_ADMIN_USERNAME=admin
    set SUPER_ADMIN_EMAIL=admin@example.org
    set SUPER_ADMIN_PASSWORD=<at least 10 characters>
    rem optional:
    set SUPER_ADMIN_FULL_NAME=Site Administrator
    set SUPER_ADMIN_FACILITY_NAME=Bir Hospital
    set SUPER_ADMIN_FACILITY_TYPE=hospital     (phc | hospital)
    python -m app.scripts.create_super_admin

SUPER_ADMIN_FACILITY_NAME (optional) must name an existing row of the facility directory
(case-insensitive; run `python -m app.db.init_db` first to seed it). SUPER_ADMIN_FACILITY_TYPE
additionally requires that kind. The admin is created without a facility when the name is omitted.

Exits non-zero with a clear message when a required variable is missing or invalid.
Idempotent: if a super admin already exists nothing is changed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import NoReturn

from dotenv import load_dotenv
from sqlalchemy import select

# Allow SUPER_ADMIN_* to be placed in backend/.env as well (real env vars still win).
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

# Registers every model on Base.metadata (there is no app/models/__init__.py; importing
# `app.models` alone would be an empty namespace package).
from app.db.base import Base  # noqa: E402,F401
from app.core.security import hash_password  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.services.facility_service import resolve_facility  # noqa: E402

PASSWORD_MIN_LENGTH = 10


def _fail(msg: str) -> NoReturn:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


def _require_env(name: str) -> str:
    value = (os.getenv(name) or "").strip()
    if not value:
        _fail(f"{name} is required (set it in the environment; no default is provided)")
    return value


def create_super_admin(
    *,
    username: str,
    email: str,
    password: str,
    full_name: str | None = None,
    facility_name: str | None = None,
    facility_type: str | None = None,
) -> User | None:
    if len(password) < PASSWORD_MIN_LENGTH:
        _fail(f"SUPER_ADMIN_PASSWORD must be at least {PASSWORD_MIN_LENGTH} characters")
    if facility_type and facility_type not in {"phc", "hospital"}:
        _fail("SUPER_ADMIN_FACILITY_TYPE must be 'phc' or 'hospital'")

    with SessionLocal() as db:
        existing = db.execute(select(User).where(User.is_super_admin.is_(True))).scalars().first()
        if existing:
            print(f"Super admin already exists: {existing.username} (nothing changed)")
            return existing

        clash = db.execute(
            select(User).where((User.username == username) | (User.email == email))
        ).scalars().first()
        if clash:
            _fail(f"a user with that username/email already exists: {clash.username}")

        facility = None
        if facility_name:
            facility = resolve_facility(db, name=facility_name, kind=facility_type or None)
            if facility is None:
                kind_hint = f" of type '{facility_type}'" if facility_type else ""
                _fail(
                    f"SUPER_ADMIN_FACILITY_NAME '{facility_name}'{kind_hint} is not in the facility "
                    "directory (run `python -m app.db.init_db` to seed it, or check the spelling)"
                )

        user = User(
            username=username,
            email=email,
            full_name=full_name or None,
            role=UserRole.ADMIN,
            is_super_admin=True,
            password_hash=hash_password(password),
            is_active=True,
            is_approved=True,
            facility_id=facility.id if facility else None,
            facility_name=facility.name if facility else None,
            facility_type=facility.kind if facility else None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        print("Super admin created successfully!")
        print(f"ID:       {user.id}")
        print(f"Username: {user.username}")
        if facility:
            print(f"Facility: {facility.name} ({facility.kind}, {facility.id})")
        return user


def main() -> None:
    username = _require_env("SUPER_ADMIN_USERNAME")
    email = _require_env("SUPER_ADMIN_EMAIL")
    password = os.getenv("SUPER_ADMIN_PASSWORD") or ""
    if not password:
        _fail("SUPER_ADMIN_PASSWORD is required (set it in the environment; no default is provided)")

    create_super_admin(
        username=username,
        email=email,
        password=password,
        full_name=(os.getenv("SUPER_ADMIN_FULL_NAME") or "").strip() or None,
        facility_name=(os.getenv("SUPER_ADMIN_FACILITY_NAME") or "").strip() or None,
        facility_type=(os.getenv("SUPER_ADMIN_FACILITY_TYPE") or "").strip().lower() or None,
    )


if __name__ == "__main__":
    main()
