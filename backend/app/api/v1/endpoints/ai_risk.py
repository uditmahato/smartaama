# backend/app/api/v1/endpoints/ai_risk.py
"""
POST /ai/risk — rule-based advisory risk assessment (no LLM, no retrieval).

Authorization: clinician / hospital / admin, and the caller must have access
to the patient (facility scoping via get_accessible_patient_or_404).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.validators import AdvisoryLanguageError
from app.core.authz import get_accessible_patient_or_404
from app.core.permissions import require_clinician_or_admin
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.ai import AiRiskRequest, AiRiskResponse
from app.services.advisory_rules import DISCLAIMER, ENGINE_VERSION
from app.services.risk_engine import RiskEngine
from app.core.rate_limit import normalize_client_ip

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _client_ip(x_forwarded_for: Optional[str]) -> Optional[str]:
    # Shared, length-bounded, validated helper (see app.core.rate_limit).
    return normalize_client_ip(x_forwarded_for)


@router.post("/risk", response_model=AiRiskResponse)
def assess_risk(
    payload: AiRiskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinician_or_admin),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
) -> AiRiskResponse:
    """
    Rule-based maternal risk assessment (advisory only). Produces an explainable
    result with evidence from the latest recorded value per data point.
    """
    get_accessible_patient_or_404(db, current_user, payload.patient_id)

    engine = RiskEngine()
    try:
        recommendation = engine.assess(db, payload)
    except ValueError as e:
        # e.g., patient not found (already checked above; kept defensively)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AdvisoryLanguageError as e:
        # Guardrail triggered: output used non-advisory language
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception:
        # Do not leak internals
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Advisory risk assessment failed",
        )

    # Audit log: minimal metadata, no PHI payload
    audit = AuditLog(
        actor_user_id=current_user.id,
        action="AI_RISK_ASSESSMENT_RUN",
        entity_type="patient",
        entity_id=payload.patient_id,
        ip_address=_client_ip(x_forwarded_for),
        user_agent=user_agent,
        details={
            "patient_id": str(payload.patient_id),
            "referral_id": str(payload.referral_id) if payload.referral_id else None,
            "risk_level": recommendation.overall_risk_level,
            "referral_recommended": recommendation.referral_recommended,
            "referral_urgency": recommendation.referral_urgency,
            "engine": ENGINE_VERSION,
        },
    )
    db.add(audit)
    db.commit()

    return AiRiskResponse(
        patient_id=payload.patient_id,
        generated_at=_utcnow(),
        recommendation=recommendation,
        model_version=ENGINE_VERSION,
        disclaimer=DISCLAIMER,
    )
