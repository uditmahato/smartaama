# backend/app/api/v1/endpoints/referrals.py

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.permissions import require_any_authenticated, require_clinician_or_admin
from app.db.session import get_db
from app.models.referral import ReferralStatus
from app.models.user import User
from app.schemas.referral import (
    ReferralCreate,
    ReferralOut,
    ReferralQuery,
    ReferralStatusUpdate,
    ReferralUpdate,
)
from app.services.referral_service import ReferralService

router = APIRouter()


def _client_ip(x_forwarded_for: Optional[str]) -> Optional[str]:
    if not x_forwarded_for:
        return None
    return x_forwarded_for.split(",")[0].strip() or None


@router.post("", response_model=ReferralOut, status_code=status.HTTP_201_CREATED)
def create_referral(
    payload: ReferralCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinician_or_admin),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
) -> ReferralOut:
    try:
        ref = ReferralService.create_referral(
            db,
            payload=payload,
            actor=current_user,
            ip=_client_ip(x_forwarded_for),
            user_agent=user_agent,
        )
        return ref
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{referral_id}", response_model=ReferralOut)
def get_referral(
    referral_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
) -> ReferralOut:
    ref = ReferralService.get_referral(db, referral_id)
    if not ref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found")
    return ref


@router.patch("/{referral_id}", response_model=ReferralOut)
def update_referral(
    referral_id: UUID,
    payload: ReferralUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinician_or_admin),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
) -> ReferralOut:
    ref = ReferralService.get_referral(db, referral_id)
    if not ref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found")

    updated = ReferralService.update_referral_decision(
        db,
        referral=ref,
        payload=payload,
        actor=current_user,
        ip=_client_ip(x_forwarded_for),
        user_agent=user_agent,
    )
    return updated


@router.post("/{referral_id}/status", response_model=ReferralOut)
def update_referral_status(
    referral_id: UUID,
    payload: ReferralStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinician_or_admin),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
) -> ReferralOut:
    ref = ReferralService.get_referral(db, referral_id)
    if not ref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found")

    try:
        updated = ReferralService.transition_status(
            db,
            referral=ref,
            new_status=payload.status,
            actor=current_user,
            ip=_client_ip(x_forwarded_for),
            user_agent=user_agent,
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=List[ReferralOut])
def list_referrals(
    patient_id: Optional[UUID] = Query(default=None),
    status_filter: Optional[ReferralStatus] = Query(default=None, alias="status"),
    from_facility: Optional[str] = Query(default=None),
    to_facility: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
) -> List[ReferralOut]:
    query = ReferralQuery(
        patient_id=patient_id,
        status=status_filter,
        from_facility=from_facility,
        to_facility=to_facility,
        limit=limit,
        offset=offset,
    )
    return ReferralService.list_referrals(db, query)
