# backend/app/schemas/medical_data.py
"""
Pydantic schemas for structured medical data entry.
Validates clinical events against the medical schema definitions.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.medical_schema import FieldType, get_section_definition


class MedicalDataPoint(BaseModel):
    """Single field value within a clinical section."""
    field_name: str
    value: Any
    unit: Optional[str] = None  # Auto-filled from schema if not provided


class SectionDataCreate(BaseModel):
    """
    Create multiple data points for a section at once.
    Used for both static profile updates and event-based entries.
    """
    section_key: str
    data_points: Dict[str, Any]  # field_name -> value mapping
    event_time: Optional[datetime] = None  # For event-based sections
    note: Optional[str] = None
    
    @field_validator("data_points")
    @classmethod
    def validate_against_schema(cls, v, info):
        """Validate data points against medical schema."""
        section_key = info.data.get("section_key")
        if not section_key:
            return v
        
        section_def = get_section_definition(section_key)
        if not section_def:
            raise ValueError(f"Unknown section: {section_key}")
        
        # Build field map
        field_map = {f.name: f for f in section_def.fields}
        
        # Validate each data point
        for field_name, value in v.items():
            if field_name not in field_map:
                raise ValueError(f"Unknown field '{field_name}' in section '{section_key}'")
            
            field_def = field_map[field_name]
            
            # Check nullable
            if value is None and not field_def.nullable:
                raise ValueError(f"Field '{field_name}' is required")
            
            if value is not None:
                # Type validation
                if field_def.field_type == FieldType.INTEGER and not isinstance(value, int):
                    raise ValueError(f"Field '{field_name}' must be an integer")
                elif field_def.field_type == FieldType.FLOAT and not isinstance(value, (int, float)):
                    raise ValueError(f"Field '{field_name}' must be a number")
                elif field_def.field_type == FieldType.BOOLEAN and not isinstance(value, bool):
                    raise ValueError(f"Field '{field_name}' must be a boolean")
                elif field_def.field_type == FieldType.STRING and not isinstance(value, str):
                    raise ValueError(f"Field '{field_name}' must be a string")
                elif field_def.field_type == FieldType.ENUM:
                    if value not in field_def.enum_values:
                        raise ValueError(
                            f"Field '{field_name}' must be one of: {', '.join(field_def.enum_values)}"
                        )
        
        return v


class SectionDataWriteResult(BaseModel):
    """Response of POST /medical-data/patients/{id}/sections/{key}."""
    message: str
    section_key: str
    event_count: int
    event_time: datetime


class SectionDataOut(BaseModel):
    """Output of GET .../sections/{key}/latest (latest value per field)."""
    section_key: str
    section_label: str
    category: str
    data_points: Dict[str, Any]
    event_time: Optional[datetime] = None
    recorded_at: Optional[datetime] = None
    note: Optional[str] = None
    message: Optional[str] = None  # e.g. "No data recorded yet"


class PatientProfileData(BaseModel):
    """Complete patient profile with all static sections."""
    patient_particulars: Optional[Dict[str, Any]] = None
    menstrual_history: Optional[Dict[str, Any]] = None
    contraceptive_history: Optional[Dict[str, Any]] = None
    past_medical_history: Optional[Dict[str, Any]] = None
    family_history: Optional[Dict[str, Any]] = None
    present_pregnancy: Optional[Dict[str, Any]] = None
    obstetric_history: Optional[Dict[str, Any]] = None


class TimeSeriesDataPoint(BaseModel):
    """A single time-series data entry (for investigations, exams)."""
    event_id: UUID
    event_time: datetime
    data_points: Dict[str, Any]
    note: Optional[str] = None
    recorded_by: Optional[str] = None


class SectionTimeSeriesOut(BaseModel):
    """Time-series data for a section (e.g., all vitals records)."""
    section_key: str
    section_label: str
    entries: List[TimeSeriesDataPoint]
    total_entries: int = 0


class BulkSectionDataCreate(BaseModel):
    """Create data for multiple sections at once (e.g., full ANC visit)."""
    patient_id: UUID
    sections: List[SectionDataCreate]
    visit_note: Optional[str] = None


class BulkSectionDataResult(BaseModel):
    """Response of POST /medical-data/patients/{id}/bulk-entry."""
    message: str
    sections_processed: List[str]
    total_events: int
