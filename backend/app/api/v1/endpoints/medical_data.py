# backend/app/api/v1/endpoints/medical_data.py
"""
Endpoints for structured medical data entry.
Handles both static profile updates and time-series clinical data.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.clinical_event import ClinicalEvent
from app.models.medical_schema import get_section_definition
from app.models.patient import Patient
from app.models.user import User
from app.schemas.medical_data import (
    BulkSectionDataCreate,
    SectionDataCreate,
    SectionDataOut,
    SectionTimeSeriesOut,
    TimeSeriesDataPoint,
)

router = APIRouter()


@router.post("/patients/{patient_id}/sections/{section_key}")
def add_section_data(
    patient_id: UUID,
    section_key: str,
    data: SectionDataCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add data for a specific section.
    
    For static/profile sections: Updates or creates the latest entry.
    For event-based sections: Always creates a new time-stamped entry.
    """
    # Verify patient exists
    patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Verify section exists in schema
    section_def = get_section_definition(section_key)
    if not section_def:
        raise HTTPException(status_code=400, detail=f"Invalid section: {section_key}")
    
    # Validate section_key matches
    if data.section_key != section_key:
        raise HTTPException(
            status_code=400,
            detail=f"Section key mismatch: URL has '{section_key}', body has '{data.section_key}'",
        )
    
    # Determine event time
    event_time = data.event_time or datetime.utcnow()
    
    # Create clinical events for each field
    created_events = []
    for field_name, value in data.data_points.items():
        # Get field definition for unit
        field_def = next((f for f in section_def.fields if f.name == field_name), None)
        
        event = ClinicalEvent(
            patient_id=patient_id,
            created_by_user_id=current_user.id,
            event_time=event_time,
            section=section_key,
            factor=field_name,
            value={
                "value": value,
                "unit": field_def.unit if field_def else None,
                "type": field_def.field_type.value if field_def else "string",
            },
            note=data.note,
        )
        db.add(event)
        created_events.append(event)
    
    # Audit log
    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="MEDICAL_DATA_ADDED",
            entity_type="clinical_event",
            entity_id=patient_id,
            details={
                "section": section_key,
                "category": section_def.category,
                "field_count": len(data.data_points),
            },
        )
    )
    
    db.commit()
    
    return {
        "message": f"Added {len(created_events)} data points to {section_def.section_label}",
        "section_key": section_key,
        "event_count": len(created_events),
        "event_time": event_time,
    }


@router.get("/patients/{patient_id}/sections/{section_key}/latest")
def get_latest_section_data(
    patient_id: UUID,
    section_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the most recent data for a section.
    Useful for static profile sections or viewing latest exam results.
    """
    # Verify patient exists
    patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Verify section exists
    section_def = get_section_definition(section_key)
    if not section_def:
        raise HTTPException(status_code=400, detail=f"Invalid section: {section_key}")
    
    # Get latest events for this section
    stmt = (
        select(ClinicalEvent)
        .where(
            ClinicalEvent.patient_id == patient_id,
            ClinicalEvent.section == section_key,
        )
        .order_by(ClinicalEvent.event_time.desc())
        .limit(50)  # Get recent entries to find latest values
    )
    
    events = db.execute(stmt).scalars().all()
    
    if not events:
        return {
            "section_key": section_key,
            "section_label": section_def.section_label,
            "category": section_def.category,
            "data_points": {},
            "message": "No data recorded yet",
        }
    
    # Build latest data points (most recent value for each field)
    data_points = {}
    seen_fields = set()
    latest_time = None
    
    for event in events:
        if event.factor not in seen_fields:
            data_points[event.factor] = event.value.get("value")
            seen_fields.add(event.factor)
            if latest_time is None:
                latest_time = event.event_time
    
    return {
        "section_key": section_key,
        "section_label": section_def.section_label,
        "category": section_def.category,
        "data_points": data_points,
        "event_time": latest_time,
        "recorded_at": events[0].created_at if events else None,
    }


@router.get("/patients/{patient_id}/sections/{section_key}/history")
def get_section_history(
    patient_id: UUID,
    section_key: str,
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get time-series history for an event-based section.
    Returns multiple dated entries (e.g., all vitals records, all lab results).
    """
    # Verify patient exists
    patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Verify section exists
    section_def = get_section_definition(section_key)
    if not section_def:
        raise HTTPException(status_code=400, detail=f"Invalid section: {section_key}")
    
    # Get all events for this section
    stmt = (
        select(ClinicalEvent)
        .where(
            ClinicalEvent.patient_id == patient_id,
            ClinicalEvent.section == section_key,
        )
        .order_by(ClinicalEvent.event_time.desc())
    )
    
    events = db.execute(stmt).scalars().all()
    
    if not events:
        return {
            "section_key": section_key,
            "section_label": section_def.section_label,
            "entries": [],
        }
    
    # Group events by event_time to create time-series entries
    entries_map = {}
    for event in events:
        time_key = event.event_time.isoformat()
        if time_key not in entries_map:
            entries_map[time_key] = {
                "event_id": event.id,
                "event_time": event.event_time,
                "data_points": {},
                "note": event.note,
                "recorded_by": None,  # Add user lookup if needed
            }
        entries_map[time_key]["data_points"][event.factor] = event.value.get("value")
    
    # Convert to list and sort by time
    entries = sorted(entries_map.values(), key=lambda x: x["event_time"], reverse=True)
    
    return {
        "section_key": section_key,
        "section_label": section_def.section_label,
        "entries": entries[:limit],
        "total_entries": len(entries),
    }


@router.post("/patients/{patient_id}/bulk-entry")
def bulk_add_sections(
    patient_id: UUID,
    data: BulkSectionDataCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add data for multiple sections at once (e.g., complete ANC visit).
    Useful for forms that span multiple sections.
    """
    # Verify patient exists
    patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Verify patient_id matches
    if data.patient_id != patient_id:
        raise HTTPException(status_code=400, detail="Patient ID mismatch")
    
    total_events = 0
    sections_processed = []
    
    # Process each section
    for section_data in data.sections:
        section_def = get_section_definition(section_data.section_key)
        if not section_def:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid section: {section_data.section_key}",
            )
        
        event_time = section_data.event_time or datetime.utcnow()
        
        # Create events for this section
        for field_name, value in section_data.data_points.items():
            field_def = next((f for f in section_def.fields if f.name == field_name), None)
            
            event = ClinicalEvent(
                patient_id=patient_id,
                created_by_user_id=current_user.id,
                event_time=event_time,
                section=section_data.section_key,
                factor=field_name,
                value={
                    "value": value,
                    "unit": field_def.unit if field_def else None,
                    "type": field_def.field_type.value if field_def else "string",
                },
                note=section_data.note or data.visit_note,
            )
            db.add(event)
            total_events += 1
        
        sections_processed.append(section_data.section_key)
    
    # Audit log
    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="BULK_MEDICAL_DATA_ADDED",
            entity_type="clinical_event",
            entity_id=patient_id,
            details={
                "sections": sections_processed,
                "total_events": total_events,
                "visit_note": data.visit_note,
            },
        )
    )
    
    db.commit()
    
    return {
        "message": f"Bulk entry completed for {len(sections_processed)} sections",
        "sections_processed": sections_processed,
        "total_events": total_events,
    }
