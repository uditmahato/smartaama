# backend/app/db/init_db.py

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.session import engine
from app.db.base import Base


def init_db() -> None:
    """
    Creates all tables.

    NOTE:
    - In production, prefer Alembic migrations.
    - This is useful for local bootstrap in early development.
    """
    Base.metadata.create_all(bind=engine)
