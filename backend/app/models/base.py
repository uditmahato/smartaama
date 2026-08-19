# backend/app/models/base.py

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    # timezone-aware UTC timestamps
    return datetime.now(timezone.utc)


# Dialect-portable column types (PostgreSQL in production, SQLite in tests):
# - Uuid: SQLAlchemy 2.x generic UUID (native `uuid` on PG, CHAR(32) elsewhere)
# - JSONVariant: JSONB on PostgreSQL, plain JSON everywhere else
UUIDType = Uuid(as_uuid=True)
JSONVariant = JSON().with_variant(JSONB(), "postgresql")


# Export for use in other models
__all__ = ["Base", "UUIDPrimaryKeyMixin", "TimestampMixin", "utcnow", "UUIDType", "JSONVariant"]


class Base(DeclarativeBase):
    """Root SQLAlchemy Declarative Base for all ORM models."""
    type_annotation_map = {
        datetime: DateTime(timezone=True),
        uuid.UUID: Uuid(as_uuid=True),
    }


class UUIDPrimaryKeyMixin:
    """Provides a UUID primary key named `id`."""
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )


class TimestampMixin:
    """
    Standard created_at timestamp for immutable/event-based records.
    NOTE: For strict immutability, we avoid updated_at on clinical tables.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )
