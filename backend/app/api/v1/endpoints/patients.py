# backend/app/api/v1/endpoints/patients.py

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.authz import get_accessible_patient_or_404
from app.core.permissions import require_any_authenticated, require_clinician_or_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.patient import PatientCreate, PatientOut, PatientSearchParams, PatientUpdate
from app.services.patient_service import PatientService, PatientServiceError
from app.core.rate_limit import normalize_client_ip

router = APIRouter()


def _client_ip(x_forwarded_for: Optional[str]) -> Optional[str]:
    # Shared, length-bounded, validated helper (see app.core.rate_limit).
    return normalize_client_ip(x_forwarded_for)


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinician_or_admin),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
) -> PatientOut:
    """
    Register a patient. The patient is registered under the caller's facility (FK + name/type
    snapshot); admins without a facility must supply `registered_facility_name`, which must name
    an existing facility (400 "Unknown facility: X" otherwise).
    """
    try:
        patient = PatientService.create_patient(
            db,
            payload=payload,
            actor=current_user,
            ip=_client_ip(x_forwarded_for),
            user_agent=user_agent,
        )
    except PatientServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return patient


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
) -> PatientOut:
    """404 if unknown, 403 if the caller's facility has no relationship with the patient."""
    return get_accessible_patient_or_404(db, current_user, patient_id)


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: UUID,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinician_or_admin),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
) -> PatientOut:
    """
    Demographic corrections. Only admins may re-home the patient via `registered_facility_name`
    (must name an existing facility, 400 "Unknown facility: X" otherwise).
    """
    patient = get_accessible_patient_or_404(db, current_user, patient_id)

    try:
        updated = PatientService.update_patient(
            db,
            patient=patient,
            payload=payload,
            actor=current_user,
            ip=_client_ip(x_forwarded_for),
            user_agent=user_agent,
        )
    except PatientServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return updated


@router.get("", response_model=List[PatientOut])
def search_patients(
    q: Optional[str] = Query(default=None, description="Name or identifier search term"),
    facility_mrn: Optional[str] = Query(default=None),
    national_id: Optional[str] = Query(default=None),
    phone_number: Optional[str] = Query(default=None),
    district: Optional[str] = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
) -> List[PatientOut]:
    """List/search patients. Results are scoped to the caller's facility (admins see all)."""
    params = PatientSearchParams(
        q=q,
        facility_mrn=facility_mrn,
        national_id=national_id,
        phone_number=phone_number,
        district=district,
        limit=limit,
        offset=offset,
    )
    return PatientService.search_patients(db, params, user=current_user)
