# backend/app/models/patient.py

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import ForeignKey, Integer, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Patient(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Patient master record.
    - Stores stable identifiers and demographics for search/registration.
    - Clinical history and updates are stored as immutable ClinicalEvent rows.
    - No deletion/overwriting of clinical data is allowed at model/service layer.
    """

    __tablename__ = "patients"

    # Auto-generated patient ID (e.g., PAT-2025-00001)
    patient_id: Mapped[str] = mapped_column(String(20), nullable=False, unique=True, index=True)

    # Facility-scoped MRN / registration number (optional but common in PHCs)
    facility_mrn: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # National ID or other identifier (optional; do not assume universal availability)
    national_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # Core demographics
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    middle_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)

    age_in_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    # Sex is typically female for maternal system, but do not hard-code; keep explicit
    sex: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # Contact info (optional)
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)

    # Address / geography (optional but useful in Nepal referral context)
    address_line: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ward: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    municipality: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    province: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Facility that registered the patient (drives facility-level access control).
    # `registered_facility_id` is the authoritative FK (id-first matching in app/core/authz.py);
    # `registered_facility_name` / `_type` are display snapshots and the legacy fallback used
    # only when the FK is NULL (rows created before revision 0002_facilities whose name did
    # not match any facility). NULL id AND NULL name -> admin-only until an admin assigns one.
    registered_facility_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("facilities.id", ondelete="SET NULL", name="fk_patients_registered_facility_id"),
        nullable=True,
        index=True,
    )
    registered_facility_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    registered_facility_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships (defined as strings to avoid circular imports)
    clinical_events: Mapped[List["ClinicalEvent"]] = relationship(
        "ClinicalEvent",
        back_populates="patient",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    referrals: Mapped[List["Referral"]] = relationship(
        "Referral",
        back_populates="patient",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    registered_facility: Mapped[Optional["Facility"]] = relationship("Facility", lazy="select")

    ai_analysis: Mapped[Optional["AIPatientAnalysis"]] = relationship(
        "AIPatientAnalysis",
        back_populates="patient",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        # Composite search optimizations
        Index("ix_patients_name_age", "last_name", "first_name", "age_in_years"),
        Index("ix_patients_facility_mrn_uniqueish", "facility_mrn"),
        Index("ix_patients_national_id_uniqueish", "national_id"),
    )

    @property
    def full_name(self) -> str:
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return " ".join([p for p in parts if p])
