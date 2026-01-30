# backend/app/schemas/ai_analysis.py

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AIPatientSummary(BaseModel):
    """AI-generated summary of patient's clinical condition"""
    summary: str = Field(..., description="Natural language summary of patient condition")
    key_findings: List[str] = Field(default_factory=list, description="Key clinical findings")
    risk_level: Optional[str] = Field(None, description="Overall risk assessment: low, medium, high, critical")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AIReferralRecommendation(BaseModel):
    """AI-generated referral recommendation"""
    referral_needed: bool = Field(..., description="Whether referral is recommended")
    urgency: str = Field(..., description="Urgency level: low, medium, high, critical")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    reasons: List[str] = Field(..., description="Reasons for referral recommendation")
    recommended_facility: Optional[str] = Field(None, description="Recommended facility name")
    recommended_specialties: List[str] = Field(default_factory=list, description="Recommended medical specialties")
    risk_factors: Dict[str, Any] = Field(default_factory=dict, description="Identified risk factors")
    clinical_indicators: Dict[str, Any] = Field(default_factory=dict, description="Key clinical indicators")
    estimated_distance_km: Optional[float] = Field(None, description="Distance to recommended facility")


class AIPatientAnalysisResponse(BaseModel):
    """Complete AI analysis response for a patient"""
    patient_id: UUID
    summary: Optional[AIPatientSummary] = None
    referral_recommendation: Optional[AIReferralRecommendation] = None
    last_analyzed_at: datetime
    data_version: int
    model_used: Optional[str] = None
    
    class Config:
        from_attributes = True


class AIAnalysisStatus(BaseModel):
    """Status of AI analysis for a patient"""
    has_analysis: bool
    last_analyzed_at: Optional[datetime] = None
    data_version: int
    needs_update: bool = Field(..., description="Whether analysis needs regeneration due to data changes")


class GenerateAIAnalysisRequest(BaseModel):
    """Request to generate or regenerate AI analysis"""
    patient_id: UUID
    force_regenerate: bool = Field(False, description="Force regeneration even if up to date")
