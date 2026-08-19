# backend/app/api/v1/endpoints/medical_data.py
"""
Endpoints for structured medical data entry.
Handles both static profile updates and time-series clinical data.

Authorization:
- every route requires patient access (facility / referral link) via get_accessible_patient_or_404
- writes require clinician/hospital/admin; viewers are read-only
- every write invalidates the stored advisory analysis for the patient
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authz import get_accessible_patient_or_404
from app.core.permissions import require_any_authenticated, require_clinician_or_admin
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.clinical_event import ClinicalEvent
from app.models.medical_schema import get_section_definition
from app.models.user import User
from app.schemas.medical_data import (
    BulkSectionDataCreate,
    BulkSectionDataResult,
    SectionDataCreate,
    SectionDataOut,
    SectionDataWriteResult,
    SectionTimeSeriesOut,
)
from app.services.event_service import invalidate_ai_analysis
from app.core.rate_limit import normalize_client_ip

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _client_ip(x_forwarded_for: Optional[str]) -> Optional[str]:
    # Shared, length-bounded, validated helper (see app.core.rate_limit).
    return normalize_client_ip(x_forwarded_for)


def _section_or_400(section_key: str):
    section_def = get_section_definition(section_key)
    if not section_def:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid section: {section_key}")
    return section_def


@router.post(
    "/patients/{patient_id}/sections/{section_key}",
    response_model=SectionDataWriteResult,
    status_code=status.HTTP_201_CREATED,
)
def add_section_data(
    patient_id: UUID,
    section_key: str,
    data: SectionDataCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinician_or_admin),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
):
    """
    Add data for a specific section.

    For static/profile sections: appends a new entry (the latest wins on read).
    For event-based sections: always creates a new time-stamped entry.
    """
    get_accessible_patient_or_404(db, current_user, patient_id)
    section_def = _section_or_400(section_key)

    if data.section_key != section_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Section key mismatch: URL has '{section_key}', body has '{data.section_key}'",
        )

    event_time = data.event_time or _utcnow()

    created_events = []
    for field_name, value in data.data_points.items():
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

    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="MEDICAL_DATA_ADDED",
            entity_type="patient",
            entity_id=patient_id,
            ip_address=_client_ip(x_forwarded_for),
            user_agent=user_agent,
            details={
                "section": section_key,
                "category": section_def.category,
                "field_count": len(data.data_points),
            },
        )
    )

    # Any clinical write invalidates the stored advisory analysis
    invalidate_ai_analysis(db, patient_id)

    db.commit()

    return SectionDataWriteResult(
        message=f"Added {len(created_events)} data points to {section_def.section_label}",
        section_key=section_key,
        event_count=len(created_events),
        event_time=event_time,
    )


@router.get("/patients/{patient_id}/sections/{section_key}/latest", response_model=SectionDataOut)
def get_latest_section_data(
    patient_id: UUID,
    section_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
):
    """
    Get the most recent data for a section.
    Useful for static profile sections or viewing latest exam results.
    """
    get_accessible_patient_or_404(db, current_user, patient_id)
    section_def = _section_or_400(section_key)

    stmt = (
        select(ClinicalEvent)
        .where(
            ClinicalEvent.patient_id == patient_id,
            ClinicalEvent.section == section_key,
        )
        .order_by(ClinicalEvent.event_time.desc(), ClinicalEvent.created_at.desc())
        .limit(50)  # recent entries are enough to find the latest value per field
    )
    events = db.execute(stmt).scalars().all()

    if not events:
        return SectionDataOut(
            section_key=section_key,
            section_label=section_def.section_label,
            category=section_def.category,
            data_points={},
            message="No data recorded yet",
        )

    data_points = {}
    latest_time = None
    for event in events:
        if event.factor not in data_points:
            data_points[event.factor] = (event.value or {}).get("value")
            if latest_time is None:
                latest_time = event.event_time

    return SectionDataOut(
        section_key=section_key,
        section_label=section_def.section_label,
        category=section_def.category,
        data_points=data_points,
        event_time=latest_time,
        recorded_at=events[0].created_at,
        note=events[0].note,
    )


@router.get("/patients/{patient_id}/sections/{section_key}/history", response_model=SectionTimeSeriesOut)
def get_section_history(
    patient_id: UUID,
    section_key: str,
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_authenticated),
):
    """
    Get time-series history for an event-based section.
    Returns multiple dated entries (e.g., all vitals records, all lab results).
    """
    get_accessible_patient_or_404(db, current_user, patient_id)
    section_def = _section_or_400(section_key)

    stmt = (
        select(ClinicalEvent)
        .where(
            ClinicalEvent.patient_id == patient_id,
            ClinicalEvent.section == section_key,
        )
        .order_by(ClinicalEvent.event_time.desc(), ClinicalEvent.created_at.desc())
    )
    events = db.execute(stmt).scalars().all()

    # Group events by event_time to create time-series entries
    entries_map: dict = {}
    for event in events:
        time_key = event.event_time.isoformat()
        if time_key not in entries_map:
            entries_map[time_key] = {
                "event_id": event.id,
                "event_time": event.event_time,
                "data_points": {},
                "note": event.note,
                "recorded_by": None,
            }
        entries_map[time_key]["data_points"][event.factor] = (event.value or {}).get("value")

    entries = sorted(entries_map.values(), key=lambda x: x["event_time"], reverse=True)

    return SectionTimeSeriesOut(
        section_key=section_key,
        section_label=section_def.section_label,
        entries=entries[:limit],
        total_entries=len(entries),
    )


@router.post("/patients/{patient_id}/bulk-entry", response_model=BulkSectionDataResult, status_code=status.HTTP_201_CREATED)
def bulk_add_sections(
    patient_id: UUID,
    data: BulkSectionDataCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_clinician_or_admin),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
):
    """
    Add data for multiple sections at once (e.g., complete ANC visit).
    Useful for forms that span multiple sections.
    """
    get_accessible_patient_or_404(db, current_user, patient_id)

    if data.patient_id != patient_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Patient ID mismatch")

    total_events = 0
    sections_processed = []

    for section_data in data.sections:
        section_def = _section_or_400(section_data.section_key)
        event_time = section_data.event_time or _utcnow()

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

    db.add(
        AuditLog(
            actor_user_id=current_user.id,
            action="BULK_MEDICAL_DATA_ADDED",
            entity_type="patient",
            entity_id=patient_id,
            ip_address=_client_ip(x_forwarded_for),
            user_agent=user_agent,
            details={
                "sections": sections_processed,
                "total_events": total_events,
                "visit_note": data.visit_note,
            },
        )
    )

    invalidate_ai_analysis(db, patient_id)

    db.commit()

    return BulkSectionDataResult(
        message=f"Bulk entry completed for {len(sections_processed)} sections",
        sections_processed=sections_processed,
        total_events=total_events,
    )
