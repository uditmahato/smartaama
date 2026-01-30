from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User, UserRole
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.schemas.user import UserOut

router = APIRouter()


def _is_super_admin(user: User):
    return user.role == UserRole.ADMIN


@router.get("/users/pending")
def pending_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    stmt = select(User).where(
        User.is_approved == False,
         User.is_active == True
    )
    pending = db.execute(stmt).scalars().all()
    return pending



@router.patch("/users/{user_id}/approve")
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


@router.patch("/users/{user_id}/reject")
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


@router.get("/users", response_model=list[UserOut])
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _is_super_admin(current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    stmt = select(User).where(
        User.role != UserRole.ADMIN,
        User.is_approved == True
    )

    users = db.execute(stmt).scalars().all()
    return users



@router.delete("/users/{user_id}")
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
