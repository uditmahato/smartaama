# backend/app/db/session.py

from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# DATABASE_URL comes from ONE place: app.core.config.settings (which loads backend/.env).
from app.core.config import settings

DATABASE_URL: str = settings.DATABASE_URL


def _is_sqlite_memory(url: str) -> bool:
    return url in ("sqlite://", "sqlite:///", "sqlite:///:memory:") or ":memory:" in url


def _engine_kwargs(url: str) -> dict:
    kwargs: dict = {"pool_pre_ping": True, "future": True}
    if url.startswith("sqlite"):
        # SQLite (tests / quick local runs): allow use across threads (TestClient) and keep a
        # single connection for in-memory DBs so all sessions see the same schema.
        kwargs["connect_args"] = {"check_same_thread": False}
        if _is_sqlite_memory(url):
            kwargs["poolclass"] = StaticPool
    return kwargs


engine: Engine = create_engine(DATABASE_URL, **_engine_kwargs(DATABASE_URL))

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
