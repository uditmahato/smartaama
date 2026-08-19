# backend/app/api/v1/endpoints/clinical_events.py

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.authz import get_accessible_patient_or_404
from app.core.permissions import require_any_authenticated, require_clinician_or_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.clinical_event import (
    ClinicalEventBatchCreate,
    ClinicalEventCreate,
    ClinicalEventOut,
    ClinicalEventQuery,
)
from app.services.event_service import EventService
from app.core.rate_limit import normalize_client_ip

router = APIRouter()


def _client_ip(x_forwarded_for: Optional[str]) -> Optional[str]:
    # Shared, length-bounded, validated helper (see app.core.rate_limit).
    return normalize_client_ip(x_forwarded_for)


def _value_error_status(exc: ValueError) -> int:
    """Service ValueErrors: 'not found' -> 404, anything else (bad linkage, bad input) -> 400."""
    return status.HTTP_404_NOT_FOUND if "not found" in str(exc).lower() else status.HTTP_400_BAD_REQUEST


@router.post("", response_model=ClinicalEventOut, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: ClinicalEventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinician_or_admin),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
) -> ClinicalEventOut:
    # 404 if patient unknown, 403 if caller's facility has no access
    get_accessible_patient_or_404(db, current_user, payload.patient_id)
    try:
        evt = EventService.create_event(
            db,
            payload=payload,
            actor=current_user,
            ip=_client_ip(x_forwarded_for),
            user_agent=user_agent,
        )
        return evt
    except ValueError as e:
        raise HTTPException(status_code=_value_error_status(e), detail=str(e))


@router.post("/batch", response_model=List[ClinicalEventOut], status_code=status.HTTP_201_CREATED)
def create_events_batch(
    payload: ClinicalEventBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinician_or_admin),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
) -> List[ClinicalEventOut]:
    get_accessible_patient_or_404(db, current_user, payload.patient_id)
    try:
        events = EventService.create_events_batch(
            db,
            payload=payload,
            actor=current_user,
            ip=_client_ip(x_forwarded_for),
            user_agent=user_agent,
        )
        return events
    except ValueError as e:
        raise HTTPException(status_code=_value_error_status(e), detail=str(e))


@router.get("", response_model=List[ClinicalEventOut])
def query_events(
    patient_id: UUID = Query(..., description="Patient UUID"),
    section: Optional[str] = Query(default=None),
    factor: Optional[str] = Query(default=None),
    from_time: Optional[datetime] = Query(default=None),
    to_time: Optional[datetime] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
) -> List[ClinicalEventOut]:
    get_accessible_patient_or_404(db, current_user, patient_id)
    q = ClinicalEventQuery(
        patient_id=patient_id,
        section=section,
        factor=factor,
        from_time=from_time,
        to_time=to_time,
        limit=limit,
        offset=offset,
    )
    return EventService.query_events(db, q)
