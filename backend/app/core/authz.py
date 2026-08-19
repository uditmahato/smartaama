# backend/app/core/authz.py
"""
Object / facility-level authorization helpers.

Design (see documentation/ARCHITECTURE.md "Facility identity" and ACCESS_CONTROL.md §2/§3):
- Facilities are rows of the unified `facilities` table. Users, patients and referrals carry a
  facility FOREIGN KEY (`User.facility_id`, `Patient.registered_facility_id`,
  `Referral.from_facility_id` / `to_facility_id`) plus a name snapshot
  (`facility_name`, `registered_facility_name`, `from_facility` / `to_facility`).
- Matching is **id-first**: a row is "the user's" when its facility id equals the user's
  `facility_id`.
- **Legacy name fallback**: only when the ROW's facility id is NULL (rows written before
  revision 0002_facilities whose name matched no facility) the name snapshot is compared with
  the user's `facility_name` — case-insensitively, trimmed, exact (no substring matching).
  A row that HAS an id is never matched by name.
- Admins (role == admin) may access every patient and referral.
- A non-admin may access a patient if the patient was registered by their facility OR any
  referral for that patient lists their facility as sender or receiver.
- A non-admin may access a referral if their facility is the sender or the receiver.
- Users with neither `facility_id` nor `facility_name` can access nothing patient-related
  unless they are admins.

The Python checks and the SQL filters below implement exactly the same rule; keep them in sync.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import exists, false, func, or_, select, true
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models.patient import Patient
from app.models.referral import Referral
from app.models.user import User, UserRole


def _norm(name: Optional[str]) -> str:
    return (name or "").strip().lower()


def facility_matches(a: Optional[str], b: Optional[str]) -> bool:
    """Case-insensitive, trimmed, exact facility-name comparison. Empty never matches."""
    na, nb = _norm(a), _norm(b)
    return bool(na) and na == nb


def is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


def _norm_col(col) -> ColumnElement:
    return func.lower(func.trim(col))


def user_facility_key(user: User) -> tuple[Optional[UUID], str]:
    """(facility_id, normalised facility_name) of the caller; (None, "") means no facility."""
    return user.facility_id, _norm(user.facility_name)


def facility_ref_matches(row_id: Optional[UUID], row_name: Optional[str], user: User) -> bool:
    """
    Python side of the rule: does a (facility_id, facility_name) pair on a row belong to the
    user's facility? id-first; name only when the row's id is NULL.
    """
    fid, fname = user_facility_key(user)
    if row_id is not None:
        return fid is not None and row_id == fid
    return bool(fname) and _norm(row_name) == fname


def facility_ref_filter(id_col, name_col, user: User) -> ColumnElement:
    """
    SQL side of the rule for a (facility_id, facility_name) column pair. Returns a criterion that
    is true for rows belonging to the user's facility (id-first, name fallback for NULL-id rows).
    """
    fid, fname = user_facility_key(user)
    clauses = []
    if fid is not None:
        clauses.append(id_col == fid)
    if fname:
        clauses.append((id_col.is_(None)) & (_norm_col(name_col) == fname))
    if not clauses:
        return false()
    return or_(*clauses)


def referral_party_filter(user: User) -> ColumnElement:
    """Criterion: the user's facility is the referral's sender OR receiver (never true for no facility)."""
    return or_(
        facility_ref_filter(Referral.from_facility_id, Referral.from_facility, user),
        facility_ref_filter(Referral.to_facility_id, Referral.to_facility, user),
    )


def referral_sender_filter(user: User) -> ColumnElement:
    return facility_ref_filter(Referral.from_facility_id, Referral.from_facility, user)


def referral_receiver_filter(user: User) -> ColumnElement:
    return facility_ref_filter(Referral.to_facility_id, Referral.to_facility, user)


def _has_facility(user: User) -> bool:
    fid, fname = user_facility_key(user)
    return fid is not None or bool(fname)


def patient_access_filter(user: User) -> ColumnElement:
    """
    SQLAlchemy criterion selecting the patients `user` may access.
    Usable as: select(Patient).where(patient_access_filter(user)).
    """
    if is_admin(user):
        return true()
    if not _has_facility(user):
        return false()
    referral_link = exists(
        select(Referral.id).where(Referral.patient_id == Patient.id, referral_party_filter(user))
    )
    registered_here = facility_ref_filter(Patient.registered_facility_id, Patient.registered_facility_name, user)
    return registered_here | referral_link


def user_can_access_patient(db: Session, user: User, patient: Patient) -> bool:
    if is_admin(user):
        return True
    if not _has_facility(user):
        return False
    if facility_ref_matches(patient.registered_facility_id, patient.registered_facility_name, user):
        return True
    stmt = select(Referral.id).where(Referral.patient_id == patient.id, referral_party_filter(user)).limit(1)
    return db.execute(stmt).first() is not None


def get_accessible_patient_or_404(db: Session, user: User, patient_id: UUID) -> Patient:
    """
    Load a patient the caller may access.
    Raises 404 if the patient does not exist, 403 if it exists but the caller
    has no facility relationship with it.
    """
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    if not user_can_access_patient(db, user, patient):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this patient",
        )
    return patient


def user_is_referring_facility(user: User, referral: Referral) -> bool:
    return facility_ref_matches(referral.from_facility_id, referral.from_facility, user)


def user_is_receiving_facility(user: User, referral: Referral) -> bool:
    return facility_ref_matches(referral.to_facility_id, referral.to_facility, user)


def user_is_referral_party(user: User, referral: Referral) -> bool:
    if is_admin(user):
        return True
    return user_is_referring_facility(user, referral) or user_is_receiving_facility(user, referral)


def require_referral_party(user: User, referral: Referral) -> None:
    """403 unless the caller is admin or their facility is the referral's sender or receiver."""
    if not user_is_referral_party(user, referral):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this referral",
        )


def require_referring_facility(user: User, referral: Referral) -> None:
    """403 unless the caller is admin or belongs to the referral's sending facility."""
    if is_admin(user) or user_is_referring_facility(user, referral):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only the referring facility can perform this action",
    )


def require_receiving_facility(user: User, referral: Referral) -> None:
    """403 unless the caller is admin or belongs to the referral's receiving facility."""
    if is_admin(user) or user_is_receiving_facility(user, referral):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only the receiving facility can perform this action",
    )
