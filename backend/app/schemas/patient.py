# backend/app/schemas/patient.py

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PatientBase(BaseModel):
    facility_mrn: Optional[str] = Field(default=None, max_length=64)
    national_id: Optional[str] = Field(default=None, max_length=64)

    first_name: str = Field(..., min_length=1, max_length=120)
    middle_name: Optional[str] = Field(default=None, max_length=120)
    last_name: str = Field(..., min_length=1, max_length=120)

    age_in_years: Optional[int] = Field(default=None, ge=0, le=150)
    sex: Optional[str] = Field(default=None, max_length=32)

    phone_number: Optional[str] = Field(default=None, max_length=32)

    address_line: Optional[str] = None
    ward: Optional[str] = Field(default=None, max_length=64)
    municipality: Optional[str] = Field(default=None, max_length=128)
    district: Optional[str] = Field(default=None, max_length=128)
    province: Optional[str] = Field(default=None, max_length=128)

    @field_validator("facility_mrn", "national_id", "phone_number", mode="before")
    @classmethod
    def strip_strings(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v

    @field_validator("first_name", "middle_name", "last_name", "sex", "ward", "municipality", "district", "province", mode="before")
    @classmethod
    def strip_names(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            v = " ".join(v.strip().split())
            return v or None
        return v


class PatientCreate(PatientBase):
    """
    Create a patient master record.
    Note: clinical data is not created here; use clinical events for clinical history.
    """
    pass


class PatientUpdate(PatientBase):
    """
    Patient updates should be rare and limited to demographics/identity corrections.
    If you want strict non-overwrite even for demographics, handle corrections as events
    instead and keep Patient immutable; for now, allow controlled updates via RBAC.
    """
    first_name: Optional[str] = Field(default=None, max_length=120)
    last_name: Optional[str] = Field(default=None, max_length=120)


class PatientOut(BaseModel):
    id: UUID
    patient_id: str
    facility_mrn: Optional[str] = None
    national_id: Optional[str] = None

    first_name: str
    middle_name: Optional[str] = None
    last_name: str

    age_in_years: Optional[int] = None
    sex: Optional[str] = None

    phone_number: Optional[str] = None

    address_line: Optional[str] = None
    ward: Optional[str] = None
    municipality: Optional[str] = None
    district: Optional[str] = None
    province: Optional[str] = None

    created_at: datetime

    class Config:
        from_attributes = True


class PatientSearchParams(BaseModel):
    """
    Search parameters for patient lookup in PHCs.
    This is used by the service layer; endpoint accepts query params.
    """
    q: Optional[str] = Field(default=None, description="Name or identifier search term")
    facility_mrn: Optional[str] = None
    national_id: Optional[str] = None
    phone_number: Optional[str] = None
    district: Optional[str] = None
    age_in_years: Optional[int] = None
    limit: int = Field(default=25, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
