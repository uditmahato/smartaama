# backend/app/models/ai_patient_analysis.py

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, JSONVariant, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class AIPatientAnalysis(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Stores the rule-based advisory summary and referral suggestion for a patient
    (one row per patient). Invalidated (deleted) whenever clinical data changes
    and regenerated on next access.

    Column types are dialect-portable: JSONB on PostgreSQL, JSON elsewhere
    (tests run on SQLite).
    """
    __tablename__ = "ai_patient_analyses"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,  # One analysis per patient
    )

    # Advisory summary of the latest recorded values
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONVariant, nullable=True)

    # Advisory referral suggestion
    referral_needed: Mapped[Optional[bool]] = mapped_column(nullable=True)
    referral_urgency: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # low | medium | high | critical
    referral_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # referral score 0.0–0.95
    referral_reasons: Mapped[Optional[List[str]]] = mapped_column(JSONVariant, nullable=True)
    # Reserved (facility suggestion is not implemented; always NULL / empty)
    recommended_facility: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recommended_specialties: Mapped[Optional[List[str]]] = mapped_column(JSONVariant, nullable=True)

    # Detailed rule output
    risk_factors: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONVariant, nullable=True)
    clinical_indicators: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONVariant, nullable=True)

    # Engine identifier, e.g. "rule-based-advisory-v2" (no LLM is used).
    # NOTE: legacy databases may still contain a nullable `tokens_used` column; it is
    # no longer mapped or written.
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Data version tracking - incremented on each regeneration
    data_version: Mapped[int] = mapped_column(nullable=False, default=1)
    last_analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )

    # Relationships
    patient: Mapped["Patient"] = relationship("Patient", back_populates="ai_analysis")

    def __repr__(self) -> str:
        return (
            f"<AIPatientAnalysis patient_id={self.patient_id} "
            f"referral_needed={self.referral_needed} urgency={self.referral_urgency}>"
        )
