# backend/app/api/v1/endpoints/ai_risk.py

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.validators import AdvisoryLanguageError
from app.core.permissions import require_clinician_or_admin
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.ai import AiRiskRequest, AiRiskResponse
from app.services.risk_engine import RiskEngine

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _client_ip(x_forwarded_for: Optional[str]) -> Optional[str]:
    if not x_forwarded_for:
        return None
    return x_forwarded_for.split(",")[0].strip() or None


@router.post("/risk", response_model=AiRiskResponse)
def assess_risk(
    payload: AiRiskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinician_or_admin),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
) -> AiRiskResponse:
    """
    AI-assisted maternal risk assessment (advisory only).
    Produces explainable outputs with evidence + guideline citations (if available).
    """
    engine = RiskEngine()

    try:
        recommendation = engine.assess(db, payload)
    except ValueError as e:
        # e.g., patient not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AdvisoryLanguageError as e:
        # Guardrail triggered: output used non-advisory language
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception:
        # Do not leak internals
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI risk assessment failed",
        )

    # Audit log: do not store full PHI payload; store minimal metadata
    ip = _client_ip(x_forwarded_for)
    audit = AuditLog(
        actor_user_id=current_user.id,
        action="AI_RISK_ASSESSMENT_RUN",
        entity_type="patient",
        entity_id=payload.patient_id,
        ip_address=ip,
        user_agent=user_agent,
        details={
            "patient_id": str(payload.patient_id),
            "referral_id": str(payload.referral_id) if payload.referral_id else None,
            "risk_level": recommendation.overall_risk_level,
            "referral_recommended": recommendation.referral_recommended,
            "rag_used": True,
        },
    )
    db.add(audit)
    db.commit()

    return AiRiskResponse(
        patient_id=payload.patient_id,
        generated_at=_utcnow(),
        recommendation=recommendation,
        model_version="risk-engine-v1",
        rag_used=True,
    )
