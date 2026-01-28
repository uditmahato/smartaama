# backend/app/models/audit_log.py

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Immutable audit log.
    Do not update/delete rows; every action is append-only.

    Examples:
    - LOGIN_SUCCESS / LOGIN_FAILURE
    - PATIENT_CREATED
    - CLINICAL_EVENT_CREATED
    - REFERRAL_SUBMITTED / REFERRAL_RECEIVED / REFERRAL_CLOSED
    - AI_RISK_REQUESTED / AI_RISK_RESULT_RECORDED
    """

    __tablename__ = "audit_logs"

    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Target entity info (generic to support all modules)
    entity_type: Mapped[Optional[str]] = mapped_column(String(60), nullable=True, index=True)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    # Optional metadata for traceability
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Structured details (avoid putting PHI unnecessarily; keep minimal)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    actor: Mapped[Optional["User"]] = relationship("User", lazy="noload")

    __table_args__ = (
        Index("ix_audit_logs_action_time", "action", "created_at"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
    )
