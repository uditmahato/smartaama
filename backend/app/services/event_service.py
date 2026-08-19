# backend/app/services/event_service.py

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.clinical_event import ClinicalEvent
from app.models.patient import Patient
from app.models.user import User
from app.schemas.clinical_event import ClinicalEventBatchCreate, ClinicalEventCreate, ClinicalEventQuery


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def invalidate_ai_analysis(db: Session, patient_id: UUID) -> None:
    """
    Invalidate the stored advisory analysis for a patient (it is regenerated on next access).
    Called on every clinical write path. Imported lazily to keep the AI service optional.
    """
    from app.services.ai_update_service import mark_ai_analysis_for_update

    mark_ai_analysis_for_update(db, patient_id)


def _validate_referral_link(db: Session, patient_id, referral_id) -> None:
    """A referral tag on an event must belong to the same patient (prevents cross-patient linkage)."""
    if referral_id is None:
        return
    from app.models.referral import Referral

    ref = db.get(Referral, referral_id)
    if not ref or ref.patient_id != patient_id:
        raise ValueError("referral_id does not belong to this patient")


class EventService:
    @staticmethod
    def create_event(
        db: Session,
        *,
        payload: ClinicalEventCreate,
        actor: User,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ClinicalEvent:
        """
        Append one immutable clinical event. Callers are responsible for authorization
        (patient access is checked in the endpoint via get_accessible_patient_or_404).
        """
        patient = db.get(Patient, payload.patient_id)
        if not patient:
            raise ValueError("Patient not found")
        _validate_referral_link(db, payload.patient_id, payload.referral_id)

        evt = ClinicalEvent(
            patient_id=payload.patient_id,
            created_by_user_id=actor.id,
            event_time=payload.event_time or _utcnow(),
            section=payload.section,
            factor=payload.factor,
            value=payload.value.model_dump(),
            note=payload.note,
            referral_id=payload.referral_id,
        )
        db.add(evt)
        db.flush()

        db.add(
            AuditLog(
                actor_user_id=actor.id,
                action="CLINICAL_EVENT_CREATED",
                entity_type="clinical_event",
                entity_id=evt.id,
                ip_address=ip,
                user_agent=user_agent,
                details={
                    "patient_id": str(evt.patient_id),
                    "section": evt.section,
                    "factor": evt.factor,
                    "referral_id": str(evt.referral_id) if evt.referral_id else None,
                },
            )
        )

        invalidate_ai_analysis(db, payload.patient_id)

        db.commit()
        db.refresh(evt)
        return evt

    @staticmethod
    def create_events_batch(
        db: Session,
        *,
        payload: ClinicalEventBatchCreate,
        actor: User,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> List[ClinicalEvent]:
        patient = db.get(Patient, payload.patient_id)
        if not patient:
            raise ValueError("Patient not found")
        _validate_referral_link(db, payload.patient_id, payload.referral_id)

        event_time = payload.event_time or _utcnow()

        events: List[ClinicalEvent] = []
        for item in payload.events:
            evt = ClinicalEvent(
                patient_id=payload.patient_id,
                created_by_user_id=actor.id,
                event_time=event_time,
                section=payload.section,
                factor=item.factor,
                value=item.value.model_dump(),
                note=payload.note,
                referral_id=payload.referral_id,
            )
            db.add(evt)
            events.append(evt)

        db.flush()  # assigns ids

        db.add(
            AuditLog(
                actor_user_id=actor.id,
                action="CLINICAL_EVENT_BATCH_CREATED",
                entity_type="patient",
                entity_id=payload.patient_id,
                ip_address=ip,
                user_agent=user_agent,
                details={
                    "patient_id": str(payload.patient_id),
                    "section": payload.section,
                    "count": len(events),
                    "referral_id": str(payload.referral_id) if payload.referral_id else None,
                },
            )
        )

        invalidate_ai_analysis(db, payload.patient_id)

        db.commit()
        for e in events:
            db.refresh(e)
        return events

    @staticmethod
    def query_events(db: Session, query: ClinicalEventQuery) -> List[ClinicalEvent]:
        stmt = select(ClinicalEvent).where(ClinicalEvent.patient_id == query.patient_id)

        filters = []
        if query.section:
            filters.append(ClinicalEvent.section == query.section)
        if query.factor:
            filters.append(ClinicalEvent.factor == query.factor)
        if query.from_time:
            filters.append(ClinicalEvent.event_time >= query.from_time)
        if query.to_time:
            filters.append(ClinicalEvent.event_time <= query.to_time)

        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.order_by(ClinicalEvent.event_time.asc(), ClinicalEvent.created_at.asc())
        stmt = stmt.limit(query.limit).offset(query.offset)

        return list(db.execute(stmt).scalars().all())
