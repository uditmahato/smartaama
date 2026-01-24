# backend/app/models/facility.py

from __future__ import annotations

from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PHCFacility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "phc_facilities"

    # Unique name of the primary health center
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)


class HospitalFacility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "hospital_facilities"

    # Unique name of the hospital
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
