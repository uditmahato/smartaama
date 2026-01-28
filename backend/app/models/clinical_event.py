# backend/app/models/clinical_event.py

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class ClinicalEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Immutable clinical event record.

    Core concepts:
    - section: high-level module area (e.g., "menstrual_history", "vitals", "lab_investigations")
    - factor: specific data element within section (e.g., "lmp_date", "bp_systolic")
    - value: stored in JSONB to support multiple types (string/number/date/structured)
    - event_time: when observation/entry occurred clinically (distinct from created_at)
    - created_at: system timestamp (immutable) when event was recorded in system

    IMPORTANT:
    - This table must never be updated or deleted in normal operations.
    - Corrections are recorded as new events (e.g., factor="bp_systolic", value=..., with a note).
    """

    __tablename__ = "clinical_events"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional: who entered the event (RBAC/audit). Will link once user model exists.
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Clinical timing (when the data point applies)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        index=True,
    )

    # Section -> factor -> value model
    section: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    factor: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # Value stored as JSONB for flexible typed payload
    value: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Human-entered note / justification / correction context (optional)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Optional linkage to referral context (e.g., marking events created during referral)
    referral_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("referrals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="clinical_events")
    created_by: Mapped[Optional["User"]] = relationship("User", lazy="noload")
    referral: Mapped[Optional["Referral"]] = relationship("Referral", lazy="noload")

    __table_args__ = (
        CheckConstraint("char_length(section) > 0", name="ck_clinical_events_section_nonempty"),
        CheckConstraint("char_length(factor) > 0", name="ck_clinical_events_factor_nonempty"),
        Index(
            "ix_clinical_events_patient_section_factor_time",
            "patient_id",
            "section",
            "factor",
            "event_time",
        ),
        Index(
            "ix_clinical_events_patient_time",
            "patient_id",
            "event_time",
        ),
    )
