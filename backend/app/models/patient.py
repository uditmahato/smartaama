# backend/app/models/patient.py

from __future__ import annotations

import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy import Date, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
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

    # Facility-scoped MRN / registration number (optional but common in PHCs)
    facility_mrn: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # National ID or other identifier (optional; do not assume universal availability)
    national_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # Core demographics
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    middle_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)

    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
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

    # Relationships (defined as strings to avoid circular imports)
    clinical_events: Mapped[List["ClinicalEvent"]] = relationship(
        "ClinicalEvent",
        back_populates="patient",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ClinicalEvent.event_time.asc()",
    )

    referrals: Mapped[List["Referral"]] = relationship(
        "Referral",
        back_populates="patient",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Referral.created_at.asc()",
    )

    __table_args__ = (
        # Composite search optimizations
        Index("ix_patients_name_dob", "last_name", "first_name", "date_of_birth"),
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
