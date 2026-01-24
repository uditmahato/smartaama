# backend/app/schemas/referral.py

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.referral import ReferralStatus


class ReferralBase(BaseModel):
    patient_id: UUID

    from_facility: str = Field(..., min_length=2, max_length=200)
    to_facility: str = Field(..., min_length=2, max_length=200)

    reason: str = Field(..., min_length=5, max_length=4000)
    reason_codes: Optional[List[str]] = Field(default=None, description="Optional structured reason codes")

    # AI advisory payload (explainable output)
    ai_recommendation: Optional[Dict[str, Any]] = Field(default=None)

    # Clinician decision overrides AI
    clinician_decision: Optional[str] = Field(default=None, max_length=64)
    clinician_note: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("from_facility", "to_facility", mode="before")
    @classmethod
    def strip_facilities(cls, v):
        if isinstance(v, str):
            v = " ".join(v.strip().split())
        return v

    @field_validator("reason", "clinician_note", mode="before")
    @classmethod
    def strip_text(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


class ReferralCreate(ReferralBase):
    status: Optional[ReferralStatus] = Field(default=None, description="Optional initial status (e.g., submitted for hospital referrals)")
    pass


class ReferralUpdate(BaseModel):
    """
    Updates are restricted to decision-making / notes and controlled status transitions.
    """
    clinician_decision: Optional[str] = Field(default=None, max_length=64)
    clinician_note: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("clinician_decision", "clinician_note", mode="before")
    @classmethod
    def strip_text(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


class ReferralStatusUpdate(BaseModel):
    status: ReferralStatus
    note: Optional[str] = Field(default=None, max_length=4000, description="Note about the status change")

    @field_validator("note", mode="before")
    @classmethod
    def strip_text(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


class ReceivedFacilityStatusUpdate(BaseModel):
    received_facility_status: ReferralStatus
    note: Optional[str] = Field(default=None, max_length=4000, description="Note about the status change")

    @field_validator("note", mode="before")
    @classmethod
    def strip_text(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


class ReferralOut(BaseModel):
    id: UUID
    patient_id: UUID

    created_by_user_id: Optional[UUID] = None

    from_facility: str
    to_facility: str

    status: ReferralStatus
    received_facility_status: Optional[ReferralStatus] = None

    reason: str
    reason_codes: Optional[List[str]] = None

    ai_recommendation: Optional[Dict[str, Any]] = None

    clinician_decision: Optional[str] = None
    clinician_note: Optional[str] = None

    submitted_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    created_at: datetime

    class Config:
        from_attributes = True


class ReferralQuery(BaseModel):
    patient_id: Optional[UUID] = None
    status: Optional[ReferralStatus] = None
    from_facility: Optional[str] = None
    to_facility: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
