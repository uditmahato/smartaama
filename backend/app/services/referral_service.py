# backend/app/services/referral_service.py

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, false, func, or_, select
from sqlalchemy.orm import Session

from app.core.authz import (
    is_admin,
    referral_party_filter,
    referral_receiver_filter,
    referral_sender_filter,
    user_can_access_patient,
    user_facility_key,
)
from app.models.audit_log import AuditLog
from app.models.patient import Patient
from app.models.referral import Referral, ReferralStatus
from app.models.referral_status_history import ReferralHistoryKind, ReferralStatusHistory
from app.models.user import User
from app.schemas.referral import ReferralCreate, ReferralQuery, ReferralUpdate
from app.services.facility_service import UnknownFacilityError, resolve_facility, resolve_user_facility


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ReferralAccessError(PermissionError):
    """Raised when the actor's facility may not perform the requested referral action (HTTP 403)."""


# Referring-side state machine (unchanged)
_ALLOWED_TRANSITIONS = {
    ReferralStatus.DRAFT: {ReferralStatus.SUBMITTED, ReferralStatus.CANCELLED},
    ReferralStatus.SUBMITTED: {ReferralStatus.RECEIVED, ReferralStatus.CANCELLED},
    ReferralStatus.RECEIVED: {ReferralStatus.CLOSED},
    ReferralStatus.CLOSED: set(),
    ReferralStatus.CANCELLED: set(),
}

# Receiving-side state machine: None -> received|cancelled ; received -> closed|cancelled ; terminal immutable
_ALLOWED_RECEIVED_TRANSITIONS = {
    None: {ReferralStatus.RECEIVED, ReferralStatus.CANCELLED},
    ReferralStatus.RECEIVED: {ReferralStatus.CLOSED, ReferralStatus.CANCELLED},
    ReferralStatus.CLOSED: set(),
    ReferralStatus.CANCELLED: set(),
}


def _norm_col(col):
    return func.lower(func.trim(col))


def _norm(name: Optional[str]) -> str:
    return (name or "").strip().lower()


def _actor_name(actor: User) -> Optional[str]:
    return (actor.full_name or actor.username or "")[:200] or None


def _history(
    db: Session,
    *,
    referral: Referral,
    kind: ReferralHistoryKind,
    actor: User,
    from_status: Optional[str] = None,
    to_status: Optional[str] = None,
    note: Optional[str] = None,
) -> ReferralStatusHistory:
    row = ReferralStatusHistory(
        referral_id=referral.id,
        kind=kind.value,
        from_status=from_status,
        to_status=to_status,
        note=note,
        actor_user_id=actor.id,
        actor_name=_actor_name(actor),
    )
    db.add(row)
    return row


class ReferralService:
    # ------------------------------------------------------------------ create
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

        # Caller must have access to the patient (facility / existing referral link)
        if not user_can_access_patient(db, actor, patient):
            raise ReferralAccessError("You do not have access to this patient")

        # Both parties must be real facilities (400 "Unknown facility: X" otherwise).
        from_facility = resolve_facility(db, name=payload.from_facility)
        if from_facility is None:
            raise UnknownFacilityError(name=payload.from_facility)
        to_facility = resolve_facility(db, name=payload.to_facility)
        if to_facility is None:
            raise UnknownFacilityError(name=payload.to_facility)

        # Non-admins can only refer FROM their own facility (compared by id).
        if not is_admin(actor):
            actor_facility = resolve_user_facility(db, actor)
            if actor_facility is None or actor_facility.id != from_facility.id:
                raise ValueError("from_facility must match your facility")

        # If AI recommendation is provided, it must be explainable.
        if payload.ai_recommendation is not None:
            if "explanation" not in payload.ai_recommendation:
                raise ValueError("AI recommendation must include 'explanation'")

        initial_status = payload.status or ReferralStatus.SUBMITTED
        now = _utcnow()

        referral = Referral(
            patient_id=payload.patient_id,
            created_by_user_id=actor.id,
            # FKs are authoritative; the name columns are display snapshots of the facility rows.
            from_facility_id=from_facility.id,
            to_facility_id=to_facility.id,
            from_facility=from_facility.name,
            to_facility=to_facility.name,
            status=initial_status,
            reason=payload.reason,
            reason_codes=payload.reason_codes,
            ai_recommendation=payload.ai_recommendation,
            clinician_decision=payload.clinician_decision,
            clinician_note=payload.clinician_note,
            submitted_at=now if initial_status == ReferralStatus.SUBMITTED else None,
        )
        db.add(referral)
        db.flush()

        _history(
            db,
            referral=referral,
            kind=ReferralHistoryKind.CREATED,
            actor=actor,
            from_status=None,
            to_status=initial_status.value,
            note=payload.clinician_note,
        )

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
                    "from_facility_id": str(referral.from_facility_id),
                    "to_facility": referral.to_facility,
                    "to_facility_id": str(referral.to_facility_id),
                    "status": referral.status.value,
                },
            )
        )

        # A new referral changes the patient's advisory picture (referral count / context):
        # drop the stored analysis so it is regenerated on next access.
        from app.services.event_service import invalidate_ai_analysis

        invalidate_ai_analysis(db, referral.patient_id)

        db.commit()
        db.refresh(referral)
        return referral

    @staticmethod
    def get_referral(db: Session, referral_id: UUID) -> Optional[Referral]:
        return db.get(Referral, referral_id)

    # ---------------------------------------------------------------- decision
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

        _history(
            db,
            referral=referral,
            kind=ReferralHistoryKind.DECISION,
            actor=actor,
            from_status=before["clinician_decision"],
            to_status=after["clinician_decision"],
            note=after["clinician_note"] if after["clinician_note"] != before["clinician_note"] else None,
        )

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

    # ------------------------------------------------- referring-side status
    @staticmethod
    def transition_status(
        db: Session,
        *,
        referral: Referral,
        new_status: ReferralStatus,
        note: Optional[str] = None,
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

        # Notes live in the history table (no longer appended to clinician_note)
        _history(
            db,
            referral=referral,
            kind=ReferralHistoryKind.STATUS,
            actor=actor,
            from_status=current.value,
            to_status=new_status.value,
            note=note,
        )

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
                    "note": note,
                },
            )
        )

        db.commit()
        db.refresh(referral)
        return referral

    # ------------------------------------------------- receiving-side status
    @staticmethod
    def update_received_facility_status(
        db: Session,
        *,
        referral: Referral,
        new_status: ReferralStatus,
        note: Optional[str] = None,
        actor: User,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Referral:
        current = referral.received_facility_status
        allowed = _ALLOWED_RECEIVED_TRANSITIONS.get(current, set())
        if new_status not in allowed:
            cur = current.value if current else "none"
            raise ValueError(f"Invalid received-status transition: {cur} -> {new_status.value}")

        referral.received_facility_status = new_status

        now = _utcnow()
        if new_status == ReferralStatus.RECEIVED and referral.received_at is None:
            referral.received_at = now
        elif new_status == ReferralStatus.CLOSED and referral.closed_at is None:
            referral.closed_at = now

        _history(
            db,
            referral=referral,
            kind=ReferralHistoryKind.RECEIVED_STATUS,
            actor=actor,
            from_status=current.value if current else None,
            to_status=new_status.value,
            note=note,
        )

        # Mirror into the referring-side lifecycle when the receiving facility's fact
        # (admitted / closed / declined) is a valid next step for `status`. The receiver is
        # the authority on arrival and case closure, so the sender's view stays truthful
        # without a second manual step; the sender keeps `/status` for its own transitions.
        mirrored_from = referral.status
        if new_status in _ALLOWED_TRANSITIONS.get(mirrored_from, set()):
            referral.status = new_status
            if new_status == ReferralStatus.CLOSED and referral.closed_at is None:
                referral.closed_at = now
            _history(
                db,
                referral=referral,
                kind=ReferralHistoryKind.STATUS,
                actor=actor,
                from_status=mirrored_from.value,
                to_status=new_status.value,
                note="Updated automatically from the receiving facility's status",
            )

        db.add(
            AuditLog(
                actor_user_id=actor.id,
                action="REFERRAL_RECEIVED_FACILITY_STATUS_UPDATE",
                entity_type="referral",
                entity_id=referral.id,
                ip_address=ip,
                user_agent=user_agent,
                details={
                    "from": current.value if current else None,
                    "to": new_status.value,
                    "patient_id": str(referral.patient_id),
                    "from_facility": referral.from_facility,
                    "to_facility": referral.to_facility,
                    "note": note,
                },
            )
        )

        db.commit()
        db.refresh(referral)
        return referral

    # ------------------------------------------------------------------ history
    @staticmethod
    def get_history(db: Session, referral_id: UUID) -> List[ReferralStatusHistory]:
        stmt = (
            select(ReferralStatusHistory)
            .where(ReferralStatusHistory.referral_id == referral_id)
            .order_by(ReferralStatusHistory.created_at.asc(), ReferralStatusHistory.id.asc())
        )
        return list(db.execute(stmt).scalars().all())

    # --------------------------------------------------------------------- list
    @staticmethod
    def list_referrals(db: Session, query: ReferralQuery, *, user: User) -> List[Referral]:
        """
        Single-query listing with proper pagination.
        - Non-admins are always constrained to referrals where their facility is sender OR receiver
          (by facility id; name fallback only for legacy rows with a NULL id).
        - `direction=incoming|outgoing` is relative to the caller's facility (admins without a
          facility get no rows for direction filters, since "here" is undefined).
        - Explicit `from_facility` / `to_facility` filters match the stored name exactly,
          case-insensitively (trimmed).
        """
        stmt = select(Referral)
        filters = []

        fid, fname = user_facility_key(user)
        has_facility = fid is not None or bool(fname)
        # id-first, legacy name fallback for NULL-id rows (same rule as app/core/authz.py)
        is_from_me = referral_sender_filter(user)
        is_to_me = referral_receiver_filter(user)

        if not is_admin(user):
            if not has_facility:
                return []  # no facility -> nothing visible
            filters.append(referral_party_filter(user))

        if query.direction == "incoming":
            filters.append(is_to_me if has_facility else false())
        elif query.direction == "outgoing":
            filters.append(is_from_me if has_facility else false())

        if query.patient_id:
            filters.append(Referral.patient_id == query.patient_id)
        if query.status:
            filters.append(Referral.status == query.status)
        if query.received_status:
            filters.append(Referral.received_facility_status == query.received_status)
        if query.from_facility:
            filters.append(_norm_col(Referral.from_facility) == _norm(query.from_facility))
        if query.to_facility:
            filters.append(_norm_col(Referral.to_facility) == _norm(query.to_facility))

        if filters:
            stmt = stmt.where(and_(*filters))

        stmt = stmt.order_by(Referral.created_at.desc()).limit(query.limit).offset(query.offset)
        return list(db.execute(stmt).scalars().all())
