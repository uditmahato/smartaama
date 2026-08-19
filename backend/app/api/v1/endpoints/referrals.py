# backend/app/api/v1/endpoints/referrals.py

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.authz import (
    require_receiving_facility,
    require_referral_party,
    require_referring_facility,
)
from app.core.permissions import require_any_authenticated, require_clinician_or_admin
from app.db.session import get_db
from app.models.referral import Referral, ReferralStatus
from app.models.user import User
from app.schemas.referral import (
    ReceivedFacilityStatusUpdate,
    ReferralCreate,
    ReferralDirection,
    ReferralHistoryOut,
    ReferralOut,
    ReferralQuery,
    ReferralStatusUpdate,
    ReferralUpdate,
)
from app.services.referral_service import ReferralAccessError, ReferralService
from app.core.rate_limit import normalize_client_ip

router = APIRouter()


def _client_ip(x_forwarded_for: Optional[str]) -> Optional[str]:
    # Shared, length-bounded, validated helper (see app.core.rate_limit).
    return normalize_client_ip(x_forwarded_for)


def _get_referral_or_404(db: Session, referral_id: UUID) -> Referral:
    ref = ReferralService.get_referral(db, referral_id)
    if not ref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Referral not found")
    return ref


@router.post("", response_model=ReferralOut, status_code=status.HTTP_201_CREATED)
def create_referral(
    payload: ReferralCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinician_or_admin),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
) -> ReferralOut:
    """
    Create a referral. Caller must have access to the patient. `from_facility` / `to_facility`
    are facility NAMES and must resolve to rows of the facility directory (400 "Unknown
    facility: X" otherwise); the referral stores their ids plus the canonical names. For
    non-admins `from_facility` must be the caller's own facility (400 otherwise).
    """
    try:
        ref = ReferralService.create_referral(
            db,
            payload=payload,
            actor=current_user,
            ip=_client_ip(x_forwarded_for),
            user_agent=user_agent,
        )
        return ref
    except ReferralAccessError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        detail = str(e)
        code = status.HTTP_404_NOT_FOUND if detail == "Patient not found" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=detail)


@router.get("", response_model=List[ReferralOut])
def list_referrals(
    patient_id: Optional[UUID] = Query(default=None),
    status_filter: Optional[ReferralStatus] = Query(default=None, alias="status"),
    received_status: Optional[ReferralStatus] = Query(default=None, description="Filter on received_facility_status"),
    direction: Optional[ReferralDirection] = Query(
        default=None, description="incoming = referred TO my facility, outgoing = referred FROM my facility"
    ),
    from_facility: Optional[str] = Query(default=None, description="Exact facility name (case-insensitive)"),
    to_facility: Optional[str] = Query(default=None, description="Exact facility name (case-insensitive)"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
) -> List[ReferralOut]:
    """
    List referrals. Non-admins only ever see referrals where their facility is the sender or the
    receiver (single query, correct pagination). Admins see everything unless filtered.
    """
    query = ReferralQuery(
        patient_id=patient_id,
        status=status_filter,
        received_status=received_status,
        direction=direction,
        from_facility=from_facility,
        to_facility=to_facility,
        limit=limit,
        offset=offset,
    )
    return ReferralService.list_referrals(db, query, user=current_user)


@router.get("/{referral_id}", response_model=ReferralOut)
def get_referral(
    referral_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
) -> ReferralOut:
    ref = _get_referral_or_404(db, referral_id)
    require_referral_party(current_user, ref)
    return ref


@router.get("/{referral_id}/history", response_model=List[ReferralHistoryOut])
def get_referral_history(
    referral_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
) -> List[ReferralHistoryOut]:
    """Append-only history (created / status / received_status / decision rows), oldest first."""
    ref = _get_referral_or_404(db, referral_id)
    require_referral_party(current_user, ref)
    return ReferralService.get_history(db, referral_id)


@router.patch("/{referral_id}", response_model=ReferralOut)
def update_referral(
    referral_id: UUID,
    payload: ReferralUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinician_or_admin),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
) -> ReferralOut:
    ref = _get_referral_or_404(db, referral_id)
    require_referral_party(current_user, ref)

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
    """Referring-side status transition — only the referring facility (from_facility) or admin."""
    ref = _get_referral_or_404(db, referral_id)
    require_referring_facility(current_user, ref)

    try:
        updated = ReferralService.transition_status(
            db,
            referral=ref,
            new_status=payload.status,
            note=payload.note,
            actor=current_user,
            ip=_client_ip(x_forwarded_for),
            user_agent=user_agent,
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{referral_id}/received-status", response_model=ReferralOut)
def update_received_facility_status(
    referral_id: UUID,
    payload: ReceivedFacilityStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinician_or_admin),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
) -> ReferralOut:
    """
    Receiving-side status — only the receiving facility (to_facility) or admin.
    Allowed: none -> received|cancelled ; received -> closed|cancelled ; closed/cancelled are final.
    """
    ref = _get_referral_or_404(db, referral_id)
    require_receiving_facility(current_user, ref)

    try:
        updated = ReferralService.update_received_facility_status(
            db,
            referral=ref,
            new_status=payload.received_facility_status,
            note=payload.note,
            actor=current_user,
            ip=_client_ip(x_forwarded_for),
            user_agent=user_agent,
        )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
