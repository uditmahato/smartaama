# backend/app/core/security.py

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token endpoint (must match your router path)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    if not isinstance(password, str) or len(password) < 10:
        # Keep consistent with bootstrap-admin password constraints
        raise ValueError("Password must be at least 10 characters")
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    if not plain_password or not password_hash:
        return False
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(*, subject_user: User) -> str:
    """
    Create a JWT for the given user.
    Claims:
      - sub: user id (UUID string)
      - username, role: for convenience (authorization should still verify from DB)
      - exp: expiry time
      - iat: issued at
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=int(settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    to_encode: Dict[str, Any] = {
        "sub": str(subject_user.id),
        "username": subject_user.username,
        "role": subject_user.role.value if hasattr(subject_user.role, "value") else str(subject_user.role),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def _get_user_id_from_payload(payload: Dict[str, Any]) -> UUID:
    sub = payload.get("sub")
    if not sub or not isinstance(sub, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token (missing subject)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return UUID(sub)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token (bad subject)",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Resolve the current authenticated user from the JWT token and DB.
    """
    payload = decode_token(token)
    user_id = _get_user_id_from_payload(payload)

    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive or invalid user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
