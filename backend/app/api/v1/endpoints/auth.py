from __future__ import annotations
from app.core.config import settings
from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID

from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.facility import HospitalFacility, PHCFacility
from app.models.user import User, UserRole
from fastapi import  Form, Header, APIRouter, Body, Depends, File, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
import os
import shutil

router = APIRouter()

class BootstrapAdminPayload(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    facility_kind: Literal["phc", "hospital"]
    facility_id: UUID


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    OAuth2-compatible login endpoint.
    """
    stmt = select(User).where(User.username == form_data.username)
    user = db.execute(stmt).scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    token = create_access_token(subject_user=user)

    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="USER_LOGIN",
            entity_type="user",
            entity_id=user.id,
            details={"username": user.username},
        )
    )
    db.commit()

    return {
        "access_token": token,
        "token_type": "bearer",
    }


@router.post("/bootstrap-admin", response_model=dict)
def bootstrap_admin(
    payload: BootstrapAdminPayload = Body(...),
    x_bootstrap_token: Optional[str] = Header(default=None, alias="X-Bootstrap-Token"),
    db: Session = Depends(get_db),
):
    """
    DEV-ONLY endpoint to create the first admin user.
    Disabled unless ENV=dev and BOOTSTRAP_TOKEN matches.
    """
    if settings.ENV != "dev":
        raise HTTPException(status_code=403, detail="Bootstrap disabled")

    if not x_bootstrap_token or x_bootstrap_token != settings.BOOTSTRAP_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid bootstrap token")

    username = payload.username
    password = payload.password
    full_name = payload.full_name
    facility_kind = (payload.facility_kind or "").lower().strip()

    if facility_kind not in {"phc", "hospital"}:
        raise HTTPException(status_code=400, detail="facility_kind must be 'phc' or 'hospital'")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")

    exists = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="User already exists")

    model = PHCFacility if facility_kind == "phc" else HospitalFacility
    facility = db.execute(select(model).where(model.id == payload.facility_id)).scalar_one_or_none()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")

    user = User(
        username=username.strip(),
        email=username.strip(),
        full_name=full_name.strip() if isinstance(full_name, str) else None,
        role=UserRole.ADMIN,
        password_hash=hash_password(password),
        is_active=True,
        is_approved=True,
        facility_type=facility_kind,
        facility_id=facility.id,
        facility_name=facility.name,
        is_super_admin=True,
    )
    db.add(user)
    db.flush()

    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="BOOTSTRAP_ADMIN_CREATED",
            entity_type="user",
            entity_id=user.id,
            details={
                "username": user.username,
                "role": user.role.value,
                "facility_type": user.facility_type,
                "facility_id": str(user.facility_id) if user.facility_id else None,
                "facility_name": user.facility_name,
            },
        )
    )

    db.commit()
    db.refresh(user)

    return {
        "id": str(user.id),
        "username": user.username,
        "role": user.role.value,
        "is_active": user.is_active,
        "facility_type": user.facility_type,
        "facility_id": str(user.facility_id) if user.facility_id else None,
        "facility_name": user.facility_name,
    }


UPLOAD_DIR = "uploads/id_cards"

@router.post("/register")
def register(
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    phone_number: str = Form(...),
    nmc_number: str = Form(...),
    working_hospital: str = Form(...),
    facility_type: Literal["phc", "hospital"] = Form(...),
    facility_id: UUID = Form(...),
    id_card_image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    exists = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if exists:
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        username=email.strip(),
        email=email.strip(),
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        phone_number=phone_number.strip(),
        nmc_number=nmc_number.strip(),
        working_hospital=working_hospital.strip(),
        facility_type=facility_type,
        facility_id=facility_id,
        role=UserRole.CLINICIAN,
        is_active=False,
        is_approved=False,
    )

    db.add(user)
    db.flush()

    if id_card_image:
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        filename = f"{user.id}_{id_card_image.filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(id_card_image.file, buffer)

        user.id_card_image_path = file_path

    db.commit()
    db.refresh(user)

    return {"detail": "Registration successful. Awaiting approval"}

@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    """
    Return current authenticated user profile.
    """
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
        "is_approved": current_user.is_approved,
        "facility_type": current_user.facility_type,
        "facility_id": str(current_user.facility_id) if current_user.facility_id else None,
        "facility_name": current_user.facility_name,
    }


# -------------------------
# ADMIN APIs
# -------------------------
def _is_super_admin(user: User):
    return user.role == UserRole.ADMIN


@router.get("/admin/users/pending")
def pending_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    stmt = select(User).where(User.is_approved == False)
    return db.execute(stmt).scalars().all()


@router.patch("/admin/users/{user_id}/approve")
def approve_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_approved = True
    user.is_active = True
    user.approved_by = current_user.id
    user.approved_at = datetime.now(timezone.utc)

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"detail": "User approved successfully"}


@router.patch("/admin/users/{user_id}/reject")
def reject_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_approved = False
    user.is_active = False

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"detail": "User rejected successfully"}


@router.get("/admin/users")
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    stmt = select(User)
    return db.execute(stmt).scalars().all()


@router.delete("/admin/users/{user_id}")
def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()

    return {"detail": "User deleted successfully"}
