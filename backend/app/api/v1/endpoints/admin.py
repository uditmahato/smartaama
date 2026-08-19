# backend/app/api/v1/endpoints/admin.py

from __future__ import annotations

import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import require_admin
from app.core.security import revoke_all_refresh_tokens
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.schemas.user import ApproveUserResponse, UserOut, UserRoleUpdate
from app.settings import ID_CARDS_DIR
from app.core.rate_limit import normalize_client_ip

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _client_ip(x_forwarded_for: Optional[str]) -> Optional[str]:
    # Shared, length-bounded, validated helper (see app.core.rate_limit).
    return normalize_client_ip(x_forwarded_for)


def _get_live_user_or_404(db: Session, user_id: UUID) -> User:
    """Load a user that has not been soft-deleted (deleted users behave as if they don't exist)."""
    user = db.get(User, user_id)
    if not user or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _require_super_admin_for_admin_target(current_user: User, target: User, action: str) -> None:
    """Only a super admin may approve/reject/delete/re-role admin-role users (prevents admin-vs-admin lockout)."""
    if target.role == UserRole.ADMIN and not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only a super admin can {action} admin users",
        )


def _audit(
    db: Session,
    *,
    actor: User,
    action: str,
    target: User,
    ip: Optional[str],
    user_agent: Optional[str],
    extra: Optional[dict] = None,
) -> None:
    details = {"target_username": target.username, "target_role": target.role.value}
    if extra:
        details.update(extra)
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            action=action,
            entity_type="user",
            entity_id=target.id,
            ip_address=ip,
            user_agent=user_agent,
            details=details,
        )
    )


@router.get("/users/pending", response_model=List[UserOut])
def pending_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Users awaiting approval (excludes rejected and soft-deleted users)."""
    stmt = (
        select(User)
        .where(User.is_approved.is_(False), User.rejected_at.is_(None), User.deleted_at.is_(None))
        .order_by(User.created_at.desc())
    )
    return db.execute(stmt).scalars().all()


@router.get("/users/rejected", response_model=List[UserOut])
def rejected_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Registrations an admin rejected (excludes soft-deleted users); approve re-admits them."""
    stmt = (
        select(User)
        .where(User.rejected_at.is_not(None), User.deleted_at.is_(None))
        .order_by(User.rejected_at.desc())
    )
    return db.execute(stmt).scalars().all()


@router.get("/users", response_model=List[UserOut])
def list_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Approved non-admin users (excludes soft-deleted users)."""
    stmt = (
        select(User)
        .where(User.role != UserRole.ADMIN, User.is_approved.is_(True), User.deleted_at.is_(None))
        .order_by(User.created_at.desc())
    )
    return db.execute(stmt).scalars().all()


@router.patch("/users/{user_id}/approve", response_model=ApproveUserResponse)
def approve_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
):
    user = _get_live_user_or_404(db, user_id)
    _require_super_admin_for_admin_target(current_user, user, "approve")

    was_rejected = user.rejected_at is not None
    user.is_approved = True
    user.is_active = True
    user.approved_by = current_user.id
    user.approved_at = _utcnow()
    # Approving a previously rejected registration re-admits it.
    user.rejected_at = None
    user.rejected_by = None

    _audit(
        db,
        actor=current_user,
        action="USER_APPROVED",
        target=user,
        ip=_client_ip(x_forwarded_for),
        user_agent=user_agent,
        extra={"was_rejected": True} if was_rejected else None,
    )
    db.commit()
    return ApproveUserResponse(detail="User approved successfully")


@router.patch("/users/{user_id}/reject", response_model=ApproveUserResponse)
def reject_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
):
    """
    Reject a registration (or revoke an approved account): unapproved + inactive, `rejected_at/by`
    set, every refresh token revoked. Rejected users leave the pending list and appear under
    GET /admin/users/rejected; approve re-admits them.
    """
    user = _get_live_user_or_404(db, user_id)

    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot reject your own account")
    _require_super_admin_for_admin_target(current_user, user, "reject")

    user.is_approved = False
    user.is_active = False
    user.rejected_at = _utcnow()
    user.rejected_by = current_user.id
    revoked = revoke_all_refresh_tokens(db, user.id)

    _audit(
        db,
        actor=current_user,
        action="USER_REJECTED",
        target=user,
        ip=_client_ip(x_forwarded_for),
        user_agent=user_agent,
        extra={"refresh_tokens_revoked": revoked},
    )
    db.commit()
    return ApproveUserResponse(detail="User rejected successfully")


@router.delete("/users/{user_id}", response_model=ApproveUserResponse)
def delete_user(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
):
    """
    Soft delete: marks the user deleted (deleted_at), inactive and unapproved. The row is kept so
    audit logs / created records keep their author. Rules:
    - you cannot delete yourself (400)
    - only a super admin may delete admin-role users (403)
    """
    user = _get_live_user_or_404(db, user_id)

    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account")

    _require_super_admin_for_admin_target(current_user, user, "delete")

    user.deleted_at = _utcnow()
    user.is_active = False
    user.is_approved = False
    revoked = revoke_all_refresh_tokens(db, user.id)

    _audit(
        db,
        actor=current_user,
        action="USER_SOFT_DELETED",
        target=user,
        ip=_client_ip(x_forwarded_for),
        user_agent=user_agent,
        extra={"refresh_tokens_revoked": revoked},
    )
    db.commit()
    return ApproveUserResponse(detail="User deleted successfully")


@router.patch("/users/{user_id}/role", response_model=UserOut)
def set_user_role(
    user_id: UUID,
    payload: UserRoleUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    x_forwarded_for: Optional[str] = Header(default=None, alias="X-Forwarded-For"),
    user_agent: Optional[str] = Header(default=None, alias="User-Agent"),
):
    """
    Assign a role (admin | clinician | hospital | viewer). Rules:
    - you cannot change your own role (400)
    - only a super admin may grant the admin role or change an existing admin's role (403)
    Audited as USER_ROLE_CHANGED. Every refresh token of the user is revoked (their next refresh
    fails and they must sign in again); the still-valid access JWT already authorizes against the
    role stored in the DB, not the `role` claim, so the new role applies immediately.
    """
    user = _get_live_user_or_404(db, user_id)

    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot change your own role")
    _require_super_admin_for_admin_target(current_user, user, "change the role of")
    if payload.role == UserRole.ADMIN and not current_user.is_super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only a super admin can grant the admin role")

    old_role = user.role
    if old_role == payload.role:
        return user
    user.role = payload.role
    revoked = revoke_all_refresh_tokens(db, user.id)

    _audit(
        db,
        actor=current_user,
        action="USER_ROLE_CHANGED",
        target=user,
        ip=_client_ip(x_forwarded_for),
        user_agent=user_agent,
        extra={"old_role": old_role.value, "new_role": payload.role.value, "refresh_tokens_revoked": revoked},
    )
    db.commit()
    db.refresh(user)
    return user


@router.get("/users/{user_id}/id-card")
def get_user_id_card(
    user_id: UUID,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Serve a user's uploaded ID-card image (admin only). 404 if the user has none or the file is
    missing. The stored value is treated as a bare filename and resolved strictly inside
    ID_CARDS_DIR — anything that escapes the directory is rejected.
    """
    user = _get_live_user_or_404(db, user_id)
    if not user.id_card_image_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ID card not found")

    base = ID_CARDS_DIR.resolve()
    # Legacy rows stored "id_cards/<name>"; only the final component is ever used.
    filename = Path(user.id_card_image_path.replace("\\", "/")).name
    if not filename or filename in {".", ".."}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ID card not found")

    candidate = (base / filename).resolve()
    if candidate.parent != base or not candidate.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ID card not found")

    media_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
    return FileResponse(
        path=str(candidate),
        media_type=media_type,
        headers={"Cache-Control": "private, no-store"},
    )
