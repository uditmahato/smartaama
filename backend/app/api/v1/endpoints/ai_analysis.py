# backend/app/api/v1/endpoints/ai_analysis.py

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import require_any_authenticated
from app.core.config import settings
from app.db.session import get_db
from app.models.ai_patient_analysis import AIPatientAnalysis
from app.models.patient import Patient
from app.models.user import User
from app.schemas.ai_analysis import (
    AIAnalysisStatus,
    AIPatientAnalysisResponse,
    AIPatientSummary,
    AIReferralRecommendation,
    GenerateAIAnalysisRequest,
)
from app.services.ai_patient_service import AIPatientService

router = APIRouter(tags=["AI Analysis"])


@router.get("/patient/{patient_id}", response_model=AIPatientAnalysisResponse)
async def get_patient_ai_analysis(
    patient_id: UUID,
    auto_generate: bool = Query(True, description="Auto-generate if not exists"),
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    """
    Get AI analysis for a patient. Auto-generates if not exists and auto_generate=True.
    """
    # Check if patient exists
    patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )
    
    # Check for existing analysis
    stmt = select(AIPatientAnalysis).where(AIPatientAnalysis.patient_id == patient_id)
    analysis = db.execute(stmt).scalar_one_or_none()
    
    # Auto-generate if requested and doesn't exist
    if not analysis and auto_generate:
        service = AIPatientService(db, settings)
        analysis = await service.get_or_generate_analysis(patient_id, force_regenerate=False)
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI analysis not available for this patient. Set auto_generate=true to generate.",
        )
    
    # Build response
    summary = None
    if analysis.summary:
        summary = AIPatientSummary(
            summary=analysis.summary,
            key_findings=analysis.summary_metadata.get("key_findings", []) if analysis.summary_metadata else [],
            risk_level=analysis.summary_metadata.get("risk_level") if analysis.summary_metadata else None,
            metadata=analysis.summary_metadata,
        )
    
    referral_rec = None
    if analysis.referral_needed is not None:
        referral_rec = AIReferralRecommendation(
            referral_needed=analysis.referral_needed,
            urgency=analysis.referral_urgency or "low",
            confidence=analysis.referral_confidence or 0.5,
            reasons=analysis.referral_reasons or [],
            recommended_facility=analysis.recommended_facility,
            recommended_specialties=analysis.recommended_specialties or [],
            risk_factors=analysis.risk_factors or {},
            clinical_indicators=analysis.clinical_indicators or {},
        )
    
    return AIPatientAnalysisResponse(
        patient_id=analysis.patient_id,
        summary=summary,
        referral_recommendation=referral_rec,
        last_analyzed_at=analysis.last_analyzed_at,
        data_version=analysis.data_version,
        model_used=analysis.model_used,
    )


@router.post("/generate", response_model=AIPatientAnalysisResponse)
async def generate_ai_analysis(
    request: GenerateAIAnalysisRequest,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    """
    Generate or regenerate AI analysis for a patient.
    """
    # Check if patient exists
    patient = db.execute(select(Patient).where(Patient.id == request.patient_id)).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {request.patient_id} not found",
        )
    
    # Generate analysis
    service = AIPatientService(db, settings)
    analysis = await service.get_or_generate_analysis(
        request.patient_id,
        force_regenerate=request.force_regenerate
    )
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI analysis",
        )
    
    # Build response
    summary = None
    if analysis.summary:
        summary = AIPatientSummary(
            summary=analysis.summary,
            key_findings=analysis.summary_metadata.get("key_findings", []) if analysis.summary_metadata else [],
            risk_level=analysis.summary_metadata.get("risk_level") if analysis.summary_metadata else None,
            metadata=analysis.summary_metadata,
        )
    
    referral_rec = None
    if analysis.referral_needed is not None:
        referral_rec = AIReferralRecommendation(
            referral_needed=analysis.referral_needed,
            urgency=analysis.referral_urgency or "low",
            confidence=analysis.referral_confidence or 0.5,
            reasons=analysis.referral_reasons or [],
            recommended_facility=analysis.recommended_facility,
            recommended_specialties=analysis.recommended_specialties or [],
            risk_factors=analysis.risk_factors or {},
            clinical_indicators=analysis.clinical_indicators or {},
        )
    
    return AIPatientAnalysisResponse(
        patient_id=analysis.patient_id,
        summary=summary,
        referral_recommendation=referral_rec,
        last_analyzed_at=analysis.last_analyzed_at,
        data_version=analysis.data_version,
        model_used=analysis.model_used,
    )


@router.get("/patient/{patient_id}/status", response_model=AIAnalysisStatus)
async def get_analysis_status(
    patient_id: UUID,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    """
    Get the status of AI analysis for a patient.
    """
    # Check if patient exists
    patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found",
        )
    
    # Check for analysis
    stmt = select(AIPatientAnalysis).where(AIPatientAnalysis.patient_id == patient_id)
    analysis = db.execute(stmt).scalar_one_or_none()
    
    if not analysis:
        return AIAnalysisStatus(
            has_analysis=False,
            last_analyzed_at=None,
            data_version=0,
            needs_update=True,
        )
    
    # TODO: Implement logic to detect if patient data has changed
    # For now, assume it doesn't need update
    needs_update = False
    
    return AIAnalysisStatus(
        has_analysis=True,
        last_analyzed_at=analysis.last_analyzed_at,
        data_version=analysis.data_version,
        needs_update=needs_update,
    )


@router.delete("/patient/{patient_id}")
async def delete_ai_analysis(
    patient_id: UUID,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    """
    Delete AI analysis for a patient (will be regenerated on next access).
    """
    stmt = select(AIPatientAnalysis).where(AIPatientAnalysis.patient_id == patient_id)
    analysis = db.execute(stmt).scalar_one_or_none()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI analysis not found for this patient",
        )
    
    db.delete(analysis)
    db.commit()
    
    return {"message": "AI analysis deleted successfully"}
