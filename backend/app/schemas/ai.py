# backend/app/schemas/ai.py

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class GuidelineCitation(BaseModel):
    """
    A retrieval citation that supports explainability.
    """
    source: str = Field(..., description="Guideline or document source name (e.g., 'Nepal MoHP ANC Guideline')")
    section: Optional[str] = Field(default=None, description="Section/chapter identifier if known")
    title: Optional[str] = Field(default=None, description="Title of the cited excerpt")
    excerpt: str = Field(..., min_length=10, description="Short excerpt supporting the recommendation (keep concise)")
    url: Optional[str] = Field(default=None, description="Optional public URL if applicable")


class RiskFactorEvidence(BaseModel):
    """
    Explains why a risk factor was flagged.
    """
    section: str = Field(..., min_length=1, max_length=64, description="ClinicalEvent.section")
    factor: str = Field(..., min_length=1, max_length=128, description="ClinicalEvent.factor")
    observed_value: Optional[Dict[str, Any]] = Field(default=None, description="Value payload from ClinicalEvent.value")
    event_time: Optional[datetime] = Field(default=None, description="Clinical time of evidence")
    note: Optional[str] = Field(default=None, description="Optional clinician-entered note from the event")


class AdvisoryRiskRecommendation(BaseModel):
    """
    AI advisory output. Must be explainable and non-autonomous.
    """
    overall_risk_level: str = Field(..., description="e.g., low | moderate | high | critical")
    summary: str = Field(..., min_length=20, description="Clinician-facing summary of assessment")
    recommended_actions: List[str] = Field(default_factory=list, description="Suggested actions for clinician consideration")

    # Referral recommendation (AI is advisory only)
    referral_recommended: bool = Field(..., description="AI may recommend; clinician decides")
    referral_urgency: Optional[str] = Field(default=None, description="e.g., routine | urgent | immediate")
    referral_reason: Optional[str] = Field(default=None, description="Explicit referral reason if recommended")

    # Mandatory explainability fields
    explanation: str = Field(..., min_length=50, description="Explainable rationale; no autonomous language")
    evidence: List[RiskFactorEvidence] = Field(default_factory=list, description="Patient-specific evidence used")
    citations: List[GuidelineCitation] = Field(default_factory=list, description="Guideline citations supporting reasoning")

    safety_note: str = Field(
        default="AI is advisory only. Final clinical decisions must be made by the responsible clinician.",
        description="Mandatory safety disclaimer",
    )

    @field_validator("overall_risk_level", mode="before")
    @classmethod
    def normalize_risk_level(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        return v.strip().lower()

    @field_validator("summary", "explanation", mode="before")
    @classmethod
    def strip_text(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            v = v.strip()
            return v
        return v


class AiRiskRequest(BaseModel):
    patient_id: UUID

    # Optional: ask the model to focus on a context (e.g., "evaluate preeclampsia risk")
    clinical_question: Optional[str] = Field(default=None, max_length=400)

    # Optional: referral context if called during referral workflow
    referral_id: Optional[UUID] = None

    @field_validator("clinical_question", mode="before")
    @classmethod
    def strip_question(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


class AiRiskResponse(BaseModel):
    """
    Response envelope returned to frontend.
    """
    patient_id: UUID
    generated_at: datetime
    recommendation: AdvisoryRiskRecommendation

    # Minimal trace fields for audit/debug (no PHI)
    model_version: Optional[str] = Field(default=None)
    rag_used: bool = Field(default=True)
