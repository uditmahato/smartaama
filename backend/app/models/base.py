# backend/app/models/base.py

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    # timezone-aware UTC timestamps
    return datetime.now(timezone.utc)


# Export utcnow for use in other models
__all__ = ['Base', 'UUIDPrimaryKeyMixin', 'TimestampMixin', 'utcnow']


class Base(DeclarativeBase):
    """Root SQLAlchemy Declarative Base for all ORM models."""
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


class UUIDPrimaryKeyMixin:
    """Provides a UUID primary key named `id`."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
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
