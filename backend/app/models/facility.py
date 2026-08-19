# backend/app/models/facility.py
"""
Unified facility directory (PHCs and hospitals in ONE table, distinguished by `kind`).

Replaces the Phase-1 `phc_facilities` / `hospital_facilities` tables (Alembic revision
0002_facilities copies their rows, preserving ids, and drops them). Users, patients and
referrals reference facilities by foreign key (`users.facility_id`,
`patients.registered_facility_id`, `referrals.from_facility_id` / `to_facility_id`); the
name columns next to those FKs are display snapshots and the legacy fallback for rows that
were created before the FKs existed (see app/core/authz.py).
"""

from __future__ import annotations

import enum

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FacilityKind(str, enum.Enum):
    PHC = "phc"
    HOSPITAL = "hospital"


FACILITY_KINDS: tuple[str, ...] = tuple(k.value for k in FacilityKind)


class Facility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "facilities"

    # Display name; unique (exact). Lookups are case-insensitive + trimmed
    # (app/services/facility_service.py), so seed data must not contain case-variants.
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    # 'phc' | 'hospital' — stored as a plain string (portable; no enum type to migrate).
    kind: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    __table_args__ = (
        CheckConstraint("kind IN ('phc', 'hospital')", name="ck_facilities_kind"),
    )

    def __repr__(self) -> str:
        return f"<Facility id={self.id} kind={self.kind} name={self.name!r}>"
