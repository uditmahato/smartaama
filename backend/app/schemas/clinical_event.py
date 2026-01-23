# backend/app/schemas/clinical_event.py

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


ALLOWED_VALUE_TYPES = {"string", "number", "boolean", "date", "datetime", "code", "object", "array"}


class ClinicalValue(BaseModel):
    """
    Typed value wrapper stored in JSONB.
    This enables explainability and consistent rendering in UI.
    """
    type: str = Field(..., description="One of: string, number, boolean, date, datetime, code, object, array")
    value: Any = Field(..., description="Actual value; type must match")
    unit: Optional[str] = Field(default=None, description="Optional unit, e.g., mmHg, kg, bpm")
    code_system: Optional[str] = Field(default=None, description="If type=code, coding system (e.g., SNOMED)")
    code: Optional[str] = Field(default=None, description="If type=code, code identifier")
    display: Optional[str] = Field(default=None, description="If type=code, human-readable label")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in ALLOWED_VALUE_TYPES:
            raise ValueError(f"Invalid value type '{v}'. Allowed: {sorted(ALLOWED_VALUE_TYPES)}")
        return v

    @field_validator("unit", "code_system", "code", "display", mode="before")
    @classmethod
    def strip_optional_strings(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


class ClinicalEventCreate(BaseModel):
    patient_id: UUID

    # Section -> factor model
    section: str = Field(..., min_length=1, max_length=64)
    factor: str = Field(..., min_length=1, max_length=128)

    value: ClinicalValue

    # Clinical timestamp (defaults to "now" at API if omitted)
    event_time: Optional[datetime] = Field(default=None)

    # Optional note for context/corrections
    note: Optional[str] = Field(default=None, max_length=2000)

    # Optional linkage to a referral workflow
    referral_id: Optional[UUID] = Field(default=None)

    @field_validator("section", "factor", mode="before")
    @classmethod
    def normalize_keys(cls, v):
        if not isinstance(v, str):
            return v
        # Keep lowercase snake-ish keys without forcing transformation that might break existing UI.
        v = v.strip()
        return v

    @field_validator("note", mode="before")
    @classmethod
    def strip_note(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


class ClinicalEventOut(BaseModel):
    id: UUID
    patient_id: UUID
    created_by_user_id: Optional[UUID] = None

    event_time: datetime
    section: str
    factor: str
    value: Dict[str, Any]
    note: Optional[str] = None
    referral_id: Optional[UUID] = None

    created_at: datetime

    class Config:
        from_attributes = True


class ClinicalEventQuery(BaseModel):
    patient_id: UUID
    section: Optional[str] = None
    factor: Optional[str] = None
    from_time: Optional[datetime] = None
    to_time: Optional[datetime] = None
    limit: int = Field(default=200, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class ClinicalEventBatchCreate(BaseModel):
    """
    Batch entry for section-wise selective updates (e.g., update vitals section with multiple factors).
    Each factor update becomes an immutable ClinicalEvent row.
    """
    patient_id: UUID
    section: str = Field(..., min_length=1, max_length=64)
    events: List["ClinicalEventBatchItem"] = Field(..., min_length=1)
    event_time: Optional[datetime] = Field(default=None)
    referral_id: Optional[UUID] = Field(default=None)
    note: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("section", mode="before")
    @classmethod
    def strip_section(cls, v):
        if isinstance(v, str):
            v = v.strip()
        return v


class ClinicalEventBatchItem(BaseModel):
    factor: str = Field(..., min_length=1, max_length=128)
    value: ClinicalValue

    @field_validator("factor", mode="before")
    @classmethod
    def strip_factor(cls, v):
        if isinstance(v, str):
            v = v.strip()
        return v


ClinicalEventBatchCreate.model_rebuild()
