# backend/app/api/v1/endpoints/patients.py

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.permissions import require_any_authenticated, require_clinician_or_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.patient import PatientCreate, PatientOut, PatientSearchParams, PatientUpdate
from app.services.patient_service import PatientService

router = APIRouter()


def _client_ip(x_forwarded_for: Optional[str]) -> Optional[str]:
    if not x_forwarded_for:
        return None
    return x_forwarded_for.split(",")[0].strip() or None


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinician_or_admin),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
) -> PatientOut:
    patient = PatientService.create_patient(
        db,
        payload=payload,
        actor=current_user,
        ip=_client_ip(x_forwarded_for),
        user_agent=user_agent,
    )
    return patient


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(
    patient_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
) -> PatientOut:
    patient = PatientService.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


@router.patch("/{patient_id}", response_model=PatientOut)
def update_patient(
    patient_id: UUID,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinician_or_admin),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
) -> PatientOut:
    patient = PatientService.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    updated = PatientService.update_patient(
        db,
        patient=patient,
        payload=payload,
        actor=current_user,
        ip=_client_ip(x_forwarded_for),
        user_agent=user_agent,
    )
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
    params = PatientSearchParams(
        q=q,
        facility_mrn=facility_mrn,
        national_id=national_id,
        phone_number=phone_number,
        district=district,
        limit=limit,
        offset=offset,
    )
    return PatientService.search_patients(db, params)
