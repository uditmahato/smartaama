from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None
    phone_number: str | None = None
    nmc_number: str | None = None
    working_hospital: str | None = None
    facility_type: str | None = None
    facility_id: UUID | None = None


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: UUID
    role: str
    is_active: Optional[bool]
    is_approved: Optional[bool]
    full_name: Optional[str]
    email: Optional[EmailStr]
    is_active: bool
    is_approved: bool
    created_at: datetime
    facility_name: Optional[str]
    facility_type: Optional[str]
    facility_id: Optional[UUID]
    working_hospital: Optional[str]
    id_card_image_path: Optional[str]


    class Config:
        orm_mode = True


class ApproveUserResponse(BaseModel):
    detail: str
