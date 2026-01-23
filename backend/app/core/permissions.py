# backend/app/core/permissions.py

from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.user import User, UserRole


def require_any_authenticated(current_user: User = Depends(get_current_user)) -> User:
    """
    Any valid authenticated user.
    """
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions (admin required)",
        )
    return current_user


def require_clinician_or_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in {UserRole.ADMIN, UserRole.CLINICIAN, UserRole.HOSPITAL}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions (clinician/admin required)",
        )
    return current_user
