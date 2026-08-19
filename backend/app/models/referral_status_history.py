# backend/app/models/referral_status_history.py

from __future__ import annotations

import enum
import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReferralHistoryKind(str, enum.Enum):
    CREATED = "created"
    STATUS = "status"                    # referring-side `status` transition
    RECEIVED_STATUS = "received_status"  # receiving-side `received_facility_status` transition
    DECISION = "decision"                # clinician_decision / clinician_note update


class ReferralStatusHistory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Append-only history of referral state changes (one row per create / transition /
    received-status change / decision update). Notes attached to a transition live here,
    NOT in Referral.clinician_note.
    """

    __tablename__ = "referral_status_history"

    referral_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("referrals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Stored as plain strings (values of ReferralHistoryKind) to stay portable and forward-compatible.
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    from_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    to_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Snapshot of the actor's display name at the time of the change (survives user deletion)
    actor_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    referral: Mapped["Referral"] = relationship("Referral", back_populates="history")

    __table_args__ = (
        Index("ix_referral_status_history_referral_time", "referral_id", "created_at"),
    )
