# backend/app/schemas/ai.py
"""
Schemas for POST /ai/risk (rule-based advisory assessment).

Vocabulary (shared with /ai-analysis/*, see app/services/advisory_rules.py):
- overall_risk_level : unknown | low | medium | high | critical
- referral_urgency   : low | medium | high | critical
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.services.advisory_rules import (
    DISCLAIMER,
    ENGINE_VERSION,
    RISK_LEVELS,
    URGENCY_LEVELS,
)


class GuidelineCitation(BaseModel):
    """
    Structured guideline citation. Guideline retrieval is NOT implemented;
    `AdvisoryRiskRecommendation.citations` is always an empty list today and
    this model is kept only so the response shape is stable if retrieval is
    added later.
    """
    source: str = Field(..., description="Guideline or document source name")
    section: Optional[str] = Field(default=None, description="Section/chapter identifier if known")
    title: Optional[str] = Field(default=None, description="Title of the cited excerpt")
    excerpt: str = Field(..., min_length=10, description="Short excerpt supporting the recommendation")
    url: Optional[str] = Field(default=None, description="Optional public URL if applicable")


class RiskFactorEvidence(BaseModel):
    """
    Explains why a rule flagged a data point.
    """
    section: str = Field(..., min_length=1, max_length=64, description="ClinicalEvent.section")
    factor: str = Field(..., min_length=1, max_length=128, description="ClinicalEvent.factor")
    observed_value: Optional[Dict[str, Any]] = Field(default=None, description="Value payload from ClinicalEvent.value")
    event_time: Optional[datetime] = Field(default=None, description="Clinical time of evidence")
    note: Optional[str] = Field(default=None, description="Optional clinician-entered note from the event")
    code: Optional[str] = Field(default=None, description="Rule code, e.g. severe_hypertension")
    severity: Optional[str] = Field(default=None, description="info | warning | severe | critical")
    domain: Optional[str] = Field(default=None, description="maternal | fetal | history")
    finding: Optional[str] = Field(default=None, description="Advisory finding sentence")


class AdvisoryRiskRecommendation(BaseModel):
    """
    Rule-based advisory output. Explainable and non-autonomous.
    """
    overall_risk_level: str = Field(..., description="unknown | low | medium | high | critical")
    summary: str = Field(..., min_length=20, description="Clinician-facing summary of assessment")
    recommended_actions: List[str] = Field(default_factory=list, description="Suggested actions for clinician consideration")

    # Referral suggestion (advisory only; clinician decides)
    referral_recommended: bool = Field(..., description="Rules suggest referral evaluation; clinician decides")
    referral_urgency: str = Field(default="low", description="low | medium | high | critical")
    referral_reason: Optional[str] = Field(default=None, description="Primary referral reason (first of referral_reasons)")
    referral_reasons: List[str] = Field(default_factory=list, description="All advisory referral reasons")
    referral_score: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Sum of triggered rule weights (capped at 0.95). A transparency score, NOT a probability.",
    )

    # Mandatory explainability fields
    explanation: str = Field(..., min_length=50, description="Explainable rationale; advisory language only")
    evidence: List[RiskFactorEvidence] = Field(default_factory=list, description="Patient-specific evidence used")
    citations: List[GuidelineCitation] = Field(
        default_factory=list,
        description="Always empty: guideline retrieval is not implemented (future work).",
    )

    engine: str = Field(default=ENGINE_VERSION, description="Rule engine identifier")
    safety_note: str = Field(default=DISCLAIMER, description="Mandatory advisory disclaimer")

    @field_validator("overall_risk_level", mode="before")
    @classmethod
    def normalize_risk_level(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        v = v.strip().lower()
        if v not in RISK_LEVELS:
            raise ValueError(f"overall_risk_level must be one of {RISK_LEVELS}")
        return v

    @field_validator("referral_urgency", mode="before")
    @classmethod
    def normalize_urgency(cls, v: str) -> str:
        if v is None:
            return "low"
        if not isinstance(v, str):
            return v
        v = v.strip().lower()
        if v not in URGENCY_LEVELS:
            raise ValueError(f"referral_urgency must be one of {URGENCY_LEVELS}")
        return v

    @field_validator("summary", "explanation", mode="before")
    @classmethod
    def strip_text(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v


class AiRiskRequest(BaseModel):
    patient_id: UUID

    # Optional: focus text echoed into the summary (e.g., "evaluate preeclampsia risk")
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
    Response envelope returned to the client.
    """
    patient_id: UUID
    generated_at: datetime
    recommendation: AdvisoryRiskRecommendation

    # Trace fields for audit/debug (no PHI)
    model_version: str = Field(default=ENGINE_VERSION, description="Rule engine identifier (no LLM is used)")
    disclaimer: str = Field(default=DISCLAIMER)
