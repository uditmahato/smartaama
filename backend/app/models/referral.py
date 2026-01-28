# backend/app/models/referral.py

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class ReferralStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    RECEIVED = "received"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class Referral(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Referral record (auditable).
    Referral includes patient timeline via query of ClinicalEvent by patient_id
    and referral_id tagging for events created during referral workflow.

    IMPORTANT:
    - Do not delete referrals; status transitions are append-only in audit logs.
    """
    __tablename__ = "referrals"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Facilities / organizations (keep as strings; can be normalized later without breaking)
    from_facility: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    to_facility: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    status: Mapped[ReferralStatus] = mapped_column(
        Enum(ReferralStatus, name="referral_status"),
        nullable=False,
        default=ReferralStatus.DRAFT,
        index=True,
    )

    # Receiving facility's status/acknowledgment (read-only for referral creator, editable only by receiving facility)
    received_facility_status: Mapped[Optional[ReferralStatus]] = mapped_column(
        Enum(ReferralStatus, name="referral_status"),
        nullable=True,
        index=True,
    )

    # Clinically explicit reason is mandatory for auditability
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional structured reasons (e.g., multiple risk flags)
    reason_codes: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)

    # AI advisory payload (must be explainable if present)
    ai_recommendation: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Clinician decision and note (AI is advisory only)
    clinician_decision: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    clinician_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing fields
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="referrals")
    created_by: Mapped[Optional["User"]] = relationship("User", back_populates="created_referrals", lazy="noload")

    # Events optionally tagged to this referral (not required, but useful)
    events: Mapped[List["ClinicalEvent"]] = relationship(
        "ClinicalEvent",
        primaryjoin="Referral.id==ClinicalEvent.referral_id",
        lazy="noload",
        viewonly=True,
    )

    __table_args__ = (
        Index("ix_referrals_patient_status", "patient_id", "status"),
        Index("ix_referrals_route", "from_facility", "to_facility"),
    )
