# backend/app/models/user.py

from __future__ import annotations

import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.facility import Facility  # noqa: F401  (FK target must be registered before User)


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
        Uuid(as_uuid=True), primary_key=True, default=uuid4
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

    # Facility membership (drives facility-level access, see app/core/authz.py).
    # `facility_id` is the authoritative FK (set by registration / bootstrap / init_db backfill);
    # `facility_name` / `facility_type` are display snapshots and the legacy fallback for
    # rows created before the FK existed. Admins may have no facility at all.
    facility_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    facility_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("facilities.id", ondelete="SET NULL", name="fk_users_facility_id"),
        nullable=True,
        index=True,
    )
    facility_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        index=True,
        nullable=False,
        default=UserRole.CLINICIAN,
    )

    is_super_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    approved_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Rejected registration: set by PATCH /admin/users/{id}/reject (which also revokes the user's
    # refresh tokens), cleared by approve. Rejected users are unapproved/inactive, excluded from
    # GET /admin/users/pending and listed by GET /admin/users/rejected.
    rejected_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Soft delete: set by DELETE /admin/users/{id}; deleted users are inactive, unapproved,
    # excluded from admin lists and rejected by get_current_user.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Filename (relative to ID_CARDS_DIR) of the uploaded ID card, e.g. "<uuid4>.png".
    # Never exposed directly; served via GET /admin/users/{id}/id-card.
    id_card_image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    created_referrals: Mapped[list["Referral"]] = relationship(
        "Referral", back_populates="created_by", lazy="noload"
    )
    facility: Mapped[Facility | None] = relationship("Facility", lazy="select")

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def is_rejected(self) -> bool:
        return self.rejected_at is not None

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username} role={self.role} active={self.is_active} approved={self.is_approved}>"
