# backend/app/api/v1/endpoints/ai_analysis.py
"""
/ai-analysis/* — rule-based advisory summary + referral suggestion.

Authorization:
- Reads (GET .../analysis, GET .../status): any authenticated user WITH access
  to the patient (facility scoping via get_accessible_patient_or_404).
- Generation / regeneration / deletion (POST /generate, DELETE, and GET with
  force_regenerate=true or auto_generate when nothing is stored): clinician,
  hospital or admin, again scoped to accessible patients. A viewer reading a
  patient with no stored analysis receives 404 instead of triggering generation.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.ai.validators import AdvisoryLanguageError
from app.core.authz import get_accessible_patient_or_404
from app.core.permissions import require_any_authenticated, require_clinician_or_admin
from app.db.session import get_db
from app.models.ai_patient_analysis import AIPatientAnalysis
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.schemas.ai_analysis import (
    AIAnalysisStatus,
    AIPatientAnalysisResponse,
    AIPatientSummary,
    AIReferralRecommendation,
    GenerateAIAnalysisRequest,
)
from app.services.advisory_rules import DISCLAIMER, ENGINE_VERSION
from app.services.ai_patient_service import AIPatientService

router = APIRouter(tags=["AI Analysis"])

_GENERATOR_ROLES = {UserRole.ADMIN, UserRole.CLINICIAN, UserRole.HOSPITAL}


def _can_generate(user: User) -> bool:
    return user.role in _GENERATOR_ROLES


def _to_response(analysis: AIPatientAnalysis) -> AIPatientAnalysisResponse:
    meta = analysis.summary_metadata or {}
    summary: Optional[AIPatientSummary] = None
    if analysis.summary:
        summary = AIPatientSummary(
            summary=analysis.summary,
            key_findings=meta.get("key_findings", []) or [],
            risk_level=meta.get("risk_level"),
            metadata=meta,
        )

    referral_rec: Optional[AIReferralRecommendation] = None
    if analysis.referral_needed is not None:
        referral_rec = AIReferralRecommendation(
            referral_needed=analysis.referral_needed,
            urgency=analysis.referral_urgency or "low",
            confidence=analysis.referral_confidence if analysis.referral_confidence is not None else 0.0,
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
        model_used=analysis.model_used or ENGINE_VERSION,
        disclaimer=DISCLAIMER,
    )


def _generate(
    service: AIPatientService,
    patient_id: UUID,
    force: bool,
    actor: Optional[User] = None,
) -> AIPatientAnalysis:
    try:
        analysis = service.get_or_generate_analysis(patient_id, force_regenerate=force)
    except AdvisoryLanguageError as e:
        # Guardrail: engine produced non-advisory wording (should never happen; tests cover it)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate advisory analysis",
        )
    # Audit every (re)generation of a stored advisory analysis (no PHI in details).
    if actor is not None:
        service.db.add(
            AuditLog(
                actor_user_id=actor.id,
                action="ADVISORY_ANALYSIS_GENERATED",
                entity_type="patient",
                entity_id=patient_id,
                details={
                    "engine": ENGINE_VERSION,
                    "forced": bool(force),
                    "risk_level": analysis.summary_metadata.get("risk_level") if isinstance(analysis.summary_metadata, dict) else None,
                },
            )
        )
        service.db.commit()
    return analysis


@router.get("/patients/{patient_id}/analysis", response_model=AIPatientAnalysisResponse)
def get_patient_ai_analysis(
    patient_id: UUID,
    auto_generate: bool = Query(True, description="Generate if none is stored (clinician/hospital/admin only)"),
    force_regenerate: bool = Query(False, description="Regenerate even if one is stored (clinician/hospital/admin only)"),
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    """
    Return the stored advisory analysis for a patient the caller may access.
    Generation (auto or forced) requires clinician / hospital / admin role.
    """
    get_accessible_patient_or_404(db, current_user, patient_id)
    service = AIPatientService(db)
    analysis = service.get_existing(patient_id)

    wants_generation = force_regenerate or (analysis is None and auto_generate)
    if wants_generation:
        if _can_generate(current_user):
            analysis = _generate(service, patient_id, force=force_regenerate, actor=current_user)
        elif force_regenerate and analysis is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Regenerating the advisory analysis requires a clinician, hospital or admin account.",
            )
        # viewer + nothing stored -> fall through to 404 below (no generation)

    if not analysis:
        if _can_generate(current_user):
            detail = (
                "No advisory analysis is stored for this patient. "
                "Request with auto_generate=true or POST /ai-analysis/generate to create one."
            )
        else:
            detail = (
                "No advisory analysis has been generated for this patient yet. "
                "Generation requires a clinician, hospital or admin account."
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    return _to_response(analysis)


@router.post("/generate", response_model=AIPatientAnalysisResponse)
def generate_ai_analysis(
    request: GenerateAIAnalysisRequest,
    current_user: User = Depends(require_clinician_or_admin),
    db: Session = Depends(get_db),
):
    """
    Generate or regenerate the advisory analysis for a patient the caller may access.
    """
    get_accessible_patient_or_404(db, current_user, request.patient_id)
    service = AIPatientService(db)
    analysis = _generate(service, request.patient_id, force=request.force_regenerate, actor=current_user)
    return _to_response(analysis)


@router.get("/patients/{patient_id}/status", response_model=AIAnalysisStatus)
def get_analysis_status(
    patient_id: UUID,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db),
):
    """
    Status of the stored advisory analysis. `needs_update` is true when nothing
    is stored or when clinical events / referrals were recorded after it.
    """
    get_accessible_patient_or_404(db, current_user, patient_id)
    service = AIPatientService(db)
    analysis = service.get_existing(patient_id)
    needs_update, last_change = service.needs_update(analysis, patient_id)

    if not analysis:
        return AIAnalysisStatus(
            has_analysis=False,
            last_analyzed_at=None,
            data_version=0,
            needs_update=True,
            last_data_change_at=last_change,
            model_used=None,
        )

    return AIAnalysisStatus(
        has_analysis=True,
        last_analyzed_at=analysis.last_analyzed_at,
        data_version=analysis.data_version,
        needs_update=needs_update,
        last_data_change_at=last_change,
        model_used=analysis.model_used,
    )


@router.delete("/patients/{patient_id}")
def delete_ai_analysis(
    patient_id: UUID,
    current_user: User = Depends(require_clinician_or_admin),
    db: Session = Depends(get_db),
):
    """
    Delete the stored advisory analysis (it is regenerated on next generation request).
    """
    get_accessible_patient_or_404(db, current_user, patient_id)
    service = AIPatientService(db)
    analysis = service.get_existing(patient_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Advisory analysis not found for this patient",
        )

    db.delete(analysis)
    db.commit()
    return {"message": "Advisory analysis deleted successfully"}
