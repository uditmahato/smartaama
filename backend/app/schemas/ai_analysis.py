# backend/app/schemas/ai_analysis.py
"""
Schemas for /ai-analysis/* (rule-based advisory summary + referral suggestion).

These shapes are consumed by the frontend cards
(frontend/src/components/AIPatientSummary.tsx, AIReferralRecommendation.tsx).
Field names are stable; enum vocabularies:
- risk_level : unknown | low | medium | high | critical
- urgency    : low | medium | high | critical
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.services.advisory_rules import DISCLAIMER, ENGINE_VERSION


class AIPatientSummary(BaseModel):
    """Rule-based summary of the patient's latest recorded clinical values."""
    summary: str = Field(..., description="Advisory summary sentence")
    key_findings: List[str] = Field(default_factory=list, description="Key findings (flagged first, then reassuring)")
    risk_level: Optional[str] = Field(None, description="unknown | low | medium | high | critical")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Counts, engine id and disclaimer")


class AIReferralRecommendation(BaseModel):
    """Rule-based referral suggestion (advisory only; clinician decides)."""
    referral_needed: bool = Field(..., description="Rules suggest referral evaluation")
    urgency: str = Field(..., description="low | medium | high | critical")
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Referral score: sum of triggered rule weights capped at 0.95. Transparency score, NOT a probability.",
    )
    reasons: List[str] = Field(..., description="Advisory reasons")
    recommended_facility: Optional[str] = Field(None, description="Not implemented; always null")
    recommended_specialties: List[str] = Field(default_factory=list, description="Not implemented; always empty")
    risk_factors: Dict[str, Any] = Field(
        default_factory=dict,
        description="{detected_risks: [{name, weight, value, code, severity}], confidence_calculation: str, data_points_analyzed: int}",
    )
    clinical_indicators: Dict[str, Any] = Field(default_factory=dict, description="Key clinical indicators (per rule code)")


class AIPatientAnalysisResponse(BaseModel):
    """Complete advisory analysis response for a patient."""
    model_config = ConfigDict(from_attributes=True)

    patient_id: UUID
    summary: Optional[AIPatientSummary] = None
    referral_recommendation: Optional[AIReferralRecommendation] = None
    last_analyzed_at: datetime
    data_version: int
    model_used: Optional[str] = Field(default=ENGINE_VERSION, description="Rule engine identifier (no LLM is used)")
    disclaimer: str = Field(default=DISCLAIMER)


class AIAnalysisStatus(BaseModel):
    """Status of the stored advisory analysis for a patient."""
    has_analysis: bool
    last_analyzed_at: Optional[datetime] = None
    data_version: int
    needs_update: bool = Field(
        ...,
        description="True when no analysis is stored or clinical data/referrals were recorded after last_analyzed_at",
    )
    last_data_change_at: Optional[datetime] = Field(
        default=None, description="Most recent clinical event / referral creation time, if any"
    )
    model_used: Optional[str] = None


class GenerateAIAnalysisRequest(BaseModel):
    """Request to generate or regenerate the advisory analysis"""
    patient_id: UUID
    force_regenerate: bool = Field(False, description="Force regeneration even if one is stored")
