# backend/app/models/referral.py

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONVariant, TimestampMixin, UUIDPrimaryKeyMixin


class ReferralStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    RECEIVED = "received"
    CLOSED = "closed"
    CANCELLED = "cancelled"


# One shared SQL Enum type object for every referral_status column, so create_all emits the
# PostgreSQL ENUM type exactly once (and a plain VARCHAR on SQLite).
REFERRAL_STATUS_ENUM = Enum(ReferralStatus, name="referral_status")


class Referral(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Referral record (auditable).
    Referral includes patient timeline via query of ClinicalEvent by patient_id
    and referral_id tagging for events created during referral workflow.

    IMPORTANT:
    - Do not delete referrals; status transitions are append-only in audit logs
      and in referral_status_history.
    """
    __tablename__ = "referrals"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Sending / receiving facility. The *_id columns are the authoritative FKs (id-first party
    # checks in app/core/authz.py); the name columns are display snapshots and the legacy
    # fallback used only when the FK is NULL (rows created before revision 0002_facilities
    # whose name did not match any facility). New referrals always carry both.
    from_facility_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("facilities.id", ondelete="SET NULL", name="fk_referrals_from_facility_id"),
        nullable=True,
        index=True,
    )
    to_facility_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("facilities.id", ondelete="SET NULL", name="fk_referrals_to_facility_id"),
        nullable=True,
        index=True,
    )
    from_facility: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    to_facility: Mapped[str] = mapped_column(String(200), nullable=False, index=True)

    status: Mapped[ReferralStatus] = mapped_column(
        REFERRAL_STATUS_ENUM,
        nullable=False,
        default=ReferralStatus.DRAFT,
        index=True,
    )

    # Receiving facility's status/acknowledgment (editable only by the receiving facility or admin)
    received_facility_status: Mapped[Optional[ReferralStatus]] = mapped_column(
        REFERRAL_STATUS_ENUM,
        nullable=True,
        index=True,
    )

    # Clinically explicit reason is mandatory for auditability
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional structured reasons (e.g., multiple risk flags)
    reason_codes: Mapped[Optional[List[str]]] = mapped_column(JSONVariant, nullable=True)

    # AI advisory payload (must be explainable if present)
    ai_recommendation: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONVariant, nullable=True)

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
    from_facility_ref: Mapped[Optional["Facility"]] = relationship(
        "Facility", foreign_keys=[from_facility_id], lazy="select"
    )
    to_facility_ref: Mapped[Optional["Facility"]] = relationship(
        "Facility", foreign_keys=[to_facility_id], lazy="select"
    )

    # Events optionally tagged to this referral (not required, but useful)
    events: Mapped[List["ClinicalEvent"]] = relationship(
        "ClinicalEvent",
        primaryjoin="Referral.id==ClinicalEvent.referral_id",
        lazy="noload",
        viewonly=True,
    )

    history: Mapped[List["ReferralStatusHistory"]] = relationship(
        "ReferralStatusHistory",
        back_populates="referral",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="noload",
        order_by="ReferralStatusHistory.created_at",
    )

    __table_args__ = (
        Index("ix_referrals_patient_status", "patient_id", "status"),
        Index("ix_referrals_route", "from_facility", "to_facility"),
        Index("ix_referrals_route_ids", "from_facility_id", "to_facility_id"),
    )
