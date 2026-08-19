# backend/app/schemas/user.py

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.user import UserRole


class UserOut(BaseModel):
    """
    Public representation of a user (used by /auth/me, /auth/register, bootstrap and /admin/users*).
    NEVER includes password_hash; id_card_image_path is only surfaced as the boolean `has_id_card`
    (the image itself is served to admins by GET /admin/users/{id}/id-card).
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    nmc_number: Optional[str] = None
    working_hospital: Optional[str] = None
    facility_type: Optional[str] = None
    facility_id: Optional[UUID] = None
    facility_name: Optional[str] = None
    role: str
    is_super_admin: bool = False
    is_active: bool
    is_approved: bool
    approved_at: Optional[datetime] = None
    # Set when an admin rejected the registration (cleared again by approve); see
    # GET /admin/users/rejected.
    rejected_at: Optional[datetime] = None
    created_at: datetime

    # Internal only: excluded from serialisation, used to compute has_id_card.
    id_card_image_path: Optional[str] = Field(default=None, exclude=True, repr=False)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_id_card(self) -> bool:
        return bool(self.id_card_image_path)


class RegisterResponse(BaseModel):
    detail: str
    user: UserOut


class ApproveUserResponse(BaseModel):
    detail: str


class UserRoleUpdate(BaseModel):
    """Body for PATCH /admin/users/{id}/role."""

    role: UserRole = Field(..., description="admin | clinician | hospital | viewer")
