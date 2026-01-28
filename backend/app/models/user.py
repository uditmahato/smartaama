# backend/app/models/user.py

from __future__ import annotations

import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CLINICIAN = "clinician"
    HOSPITAL = "hospital"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )

    username: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nmc_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    working_hospital: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Optional facility context for admins/clinicians
    facility_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    facility_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    facility_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        index=True,
        nullable=False,
        default=UserRole.CLINICIAN,
    )

    is_super_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False,index=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False,index=True)

    approved_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    id_card_image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    created_referrals: Mapped[list["Referral"]] = relationship(
        "Referral", back_populates="created_by", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username} role={self.role} active={self.is_active} approved={self.is_approved}>"
