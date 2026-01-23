# backend/app/services/referral_service.py

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.patient import Patient
from app.models.referral import Referral, ReferralStatus
from app.models.user import User
from app.schemas.referral import ReferralCreate, ReferralQuery, ReferralUpdate


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


_ALLOWED_TRANSITIONS = {
    ReferralStatus.DRAFT: {ReferralStatus.SUBMITTED, ReferralStatus.CANCELLED},
    ReferralStatus.SUBMITTED: {ReferralStatus.RECEIVED, ReferralStatus.CANCELLED},
    ReferralStatus.RECEIVED: {ReferralStatus.CLOSED},
    ReferralStatus.CLOSED: set(),
    ReferralStatus.CANCELLED: set(),
}


class ReferralService:
    @staticmethod
    def create_referral(
        db: Session,
        *,
        payload: ReferralCreate,
        actor: User,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Referral:
        patient = db.get(Patient, payload.patient_id)
        if not patient:
            raise ValueError("Patient not found")

        # If AI recommendation is provided, it must be explainable.
        if payload.ai_recommendation is not None:
            # Require an explanation field (can be nested if you want later; keep simple now)
            if "explanation" not in payload.ai_recommendation:
                raise ValueError("AI recommendation must include 'explanation'")

        referral = Referral(
            patient_id=payload.patient_id,
            created_by_user_id=actor.id,
            from_facility=payload.from_facility,
            to_facility=payload.to_facility,
            status=ReferralStatus.DRAFT,
            reason=payload.reason,
            reason_codes=payload.reason_codes,
            ai_recommendation=payload.ai_recommendation,
            clinician_decision=payload.clinician_decision,
            clinician_note=payload.clinician_note,
        )
        db.add(referral)
        db.flush()

        db.add(
            AuditLog(
                actor_user_id=actor.id,
                action="REFERRAL_CREATED",
                entity_type="referral",
                entity_id=referral.id,
                ip_address=ip,
                user_agent=user_agent,
                details={
                    "patient_id": str(referral.patient_id),
                    "from_facility": referral.from_facility,
                    "to_facility": referral.to_facility,
                    "status": referral.status.value,
                },
            )
        )

        db.commit()
        db.refresh(referral)
        return referral

    @staticmethod
    def get_referral(db: Session, referral_id: UUID) -> Optional[Referral]:
        return db.get(Referral, referral_id)

    @staticmethod
    def update_referral_decision(
        db: Session,
        *,
        referral: Referral,
        payload: ReferralUpdate,
        actor: User,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Referral:
        before = {
            "clinician_decision": referral.clinician_decision,
            "clinician_note": referral.clinician_note,
        }

        data = payload.model_dump(exclude_unset=True)
        if "clinician_decision" in data and data["clinician_decision"] is not None:
            referral.clinician_decision = data["clinician_decision"]
        if "clinician_note" in data and data["clinician_note"] is not None:
            referral.clinician_note = data["clinician_note"]

        after = {
            "clinician_decision": referral.clinician_decision,
            "clinician_note": referral.clinician_note,
        }

        db.add(
            AuditLog(
                actor_user_id=actor.id,
                action="REFERRAL_UPDATED",
                entity_type="referral",
                entity_id=referral.id,
                ip_address=ip,
                user_agent=user_agent,
                details={"before": before, "after": after},
            )
        )

        db.commit()
        db.refresh(referral)
        return referral

    @staticmethod
    def transition_status(
        db: Session,
        *,
        referral: Referral,
        new_status: ReferralStatus,
        actor: User,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Referral:
        current = referral.status
        allowed = _ALLOWED_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            raise ValueError(f"Invalid status transition: {current.value} -> {new_status.value}")

        referral.status = new_status

        now = _utcnow()
        if new_status == ReferralStatus.SUBMITTED:
            referral.submitted_at = now
        elif new_status == ReferralStatus.RECEIVED:
            referral.received_at = now
        elif new_status == ReferralStatus.CLOSED:
            referral.closed_at = now

        db.add(
            AuditLog(
                actor_user_id=actor.id,
                action=f"REFERRAL_STATUS_{new_status.value.upper()}",
                entity_type="referral",
                entity_id=referral.id,
                ip_address=ip,
                user_agent=user_agent,
                details={
                    "from": current.value,
                    "to": new_status.value,
                    "patient_id": str(referral.patient_id),
                    "from_facility": referral.from_facility,
                    "to_facility": referral.to_facility,
                },
            )
        )

        db.commit()
        db.refresh(referral)
        return referral

    @staticmethod
    def list_referrals(db: Session, query: ReferralQuery) -> List[Referral]:
        stmt = select(Referral)
        filters = []

        if query.patient_id:
            filters.append(Referral.patient_id == query.patient_id)
        if query.status:
            filters.append(Referral.status == query.status)
        if query.from_facility:
            filters.append(Referral.from_facility.ilike(f"%{query.from_facility}%"))
        if query.to_facility:
            filters.append(Referral.to_facility.ilike(f"%{query.to_facility}%"))

        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.order_by(Referral.created_at.desc()).limit(query.limit).offset(query.offset)
        return list(db.execute(stmt).scalars().all())
