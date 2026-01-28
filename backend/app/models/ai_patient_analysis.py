# backend/app/models/ai_patient_analysis.py

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utcnow


class AIPatientAnalysis(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Stores AI-generated patient summaries and referral recommendations.
    Automatically regenerated when patient data is updated.
    """
    __tablename__ = "ai_patient_analyses"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,  # One analysis per patient
    )

    # AI Summary of patient condition
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # AI Referral Recommendation
    referral_needed: Mapped[Optional[bool]] = mapped_column(nullable=True)
    referral_urgency: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # low, medium, high, critical
    referral_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0 to 1.0
    referral_reasons: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    recommended_facility: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    recommended_specialties: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    
    # Detailed referral analysis
    risk_factors: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    clinical_indicators: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    
    # OpenAI API metadata
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[Optional[int]] = mapped_column(nullable=True)
    
    # Data version tracking - incremented when patient data changes
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
