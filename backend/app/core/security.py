# backend/app/core/security.py
"""
Passwords, access JWTs and server-side refresh tokens.

Token model
- Access token: stateless HS256 JWT (`sub`, `username`, `role`, `iat`, `exp`), lifetime
  ACCESS_TOKEN_EXPIRE_MINUTES. It is NOT individually revocable: it stays valid until it expires
  (get_current_user still re-checks the user row on every request, so a disabled / rejected /
  deleted user is refused immediately — see user_is_login_eligible).
- Refresh token: opaque 32-byte urlsafe secret; only its SHA-256 digest is stored in
  `refresh_tokens` (app/models/refresh_token.py), lifetime REFRESH_TOKEN_EXPIRE_DAYS. Every use
  rotates it (old row revoked + linked to the new one via replaced_by_id). Presenting a token that
  was already revoked is treated as reuse (theft) and revokes ALL tokens of that user.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.refresh_token import RefreshToken
from app.models.user import User


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token endpoint (must match your router path)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Size of the random secret behind a refresh token (bytes before urlsafe-base64 encoding).
REFRESH_TOKEN_BYTES = 32


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    """SQLite hands back naive datetimes for DateTime(timezone=True); treat them as UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def hash_password(password: str) -> str:
    if not isinstance(password, str) or len(password) < 10:
        # Keep consistent with bootstrap-admin password constraints
        raise ValueError("Password must be at least 10 characters")
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    if not plain_password or not password_hash:
        return False
    return pwd_context.verify(plain_password, password_hash)


# --------------------------------------------------------------------------- access tokens (JWT)

def access_token_expires_in() -> int:
    """Access-token lifetime in seconds (the `expires_in` field of the token response)."""
    return int(settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60


def create_access_token(*, subject_user: User) -> str:
    """
    Create a JWT for the given user.
    Claims:
      - sub: user id (UUID string)
      - username, role: for convenience (authorization should still verify from DB)
      - exp: expiry time
      - iat: issued at
    """
    now = _utcnow()
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


def user_is_login_eligible(user: Optional[User]) -> bool:
    """
    Single source of truth for "may this account use the API right now":
    must exist, be active, be approved and not soft-deleted.
    """
    return bool(user) and user.is_active and user.is_approved and user.deleted_at is None


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Resolve the current authenticated user from the JWT token and DB.
    Rejects (401) tokens for users that are inactive, unapproved or soft-deleted, even if the
    token itself is still valid.
    """
    payload = decode_token(token)
    user_id = _get_user_id_from_payload(payload)

    stmt = select(User).where(User.id == user_id)
    user = db.execute(stmt).scalar_one_or_none()

    if not user_is_login_eligible(user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive, unapproved or invalid user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


# --------------------------------------------------------------------------- refresh tokens

class RefreshTokenReuseError(Exception):
    """A revoked refresh token was presented again (all tokens of `user_id` have been revoked)."""

    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"refresh token reuse detected for user {user_id}")
        self.user_id = user_id


def hash_refresh_token(secret: str) -> str:
    """SHA-256 hex digest of the opaque secret — the only form ever stored or looked up."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _refresh_token_401(detail: str = "Invalid or expired refresh token") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def issue_refresh_token(
    db: Session,
    *,
    user: User,
    user_agent: Optional[str] = None,
    ip: Optional[str] = None,
) -> Tuple[str, RefreshToken]:
    """
    Create a new refresh token row for `user` and return `(secret, row)`. The secret is returned
    to the client exactly once; it is never stored. Caller commits.
    """
    secret = secrets.token_urlsafe(REFRESH_TOKEN_BYTES)
    now = _utcnow()
    row = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(secret),
        expires_at=now + timedelta(days=int(settings.REFRESH_TOKEN_EXPIRE_DAYS)),
        created_at=now,
        user_agent=user_agent[:1024] if user_agent else None,
        ip=ip[:64] if ip else None,
    )
    db.add(row)
    db.flush()
    return secret, row


def find_refresh_token(db: Session, secret: str) -> Optional[RefreshToken]:
    """Look a presented secret up by hash (None if unknown)."""
    if not secret or not isinstance(secret, str):
        return None
    return db.execute(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(secret))).scalar_one_or_none()


def revoke_all_refresh_tokens(db: Session, user_id: UUID) -> int:
    """
    Revoke every live refresh token of `user_id` (admin reject / soft-delete / role change,
    reuse detection). Returns the number of tokens revoked. Caller commits.
    Access JWTs already issued stay valid until they expire (they are stateless), but
    get_current_user refuses users that are no longer login-eligible on the very next request.
    """
    result = db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_utcnow())
        .execution_options(synchronize_session="fetch")
    )
    return int(result.rowcount or 0)


def revoke_refresh_token(db: Session, secret: str) -> Optional[RefreshToken]:
    """
    Logout: revoke the presented token if it is live and return its row. Idempotent — unknown or
    already-revoked tokens are a no-op (returns None). Caller commits.
    """
    row = find_refresh_token(db, secret)
    if row is None or row.revoked_at is not None:
        return None
    row.revoked_at = _utcnow()
    db.flush()
    return row


def rotate_refresh_token(
    db: Session,
    *,
    secret: str,
    user_agent: Optional[str] = None,
    ip: Optional[str] = None,
) -> Tuple[User, str, RefreshToken]:
    """
    Validate a presented refresh token and rotate it.

    Returns `(user, new_secret, new_row)`; the old row is revoked and linked to the new one via
    `replaced_by_id`. Caller commits.

    Raises
    - HTTPException 401 when the token is unknown, expired, or its user is no longer
      login-eligible (rejected, soft-deleted, inactive, unapproved). An expired token is also
      marked revoked so it can never be "reused" later.
    - RefreshTokenReuseError when the token was ALREADY revoked (rotation, logout, admin action):
      this is reuse detection — every token of that user is revoked before raising (and the
      revocation is committed), so the legitimate holder is logged out too and must sign in again.
    """
    row = find_refresh_token(db, secret)
    if row is None:
        raise _refresh_token_401()

    now = _utcnow()
    if row.revoked_at is not None:
        revoke_all_refresh_tokens(db, row.user_id)
        db.commit()
        raise RefreshTokenReuseError(row.user_id)

    if _as_utc(row.expires_at) <= now:
        row.revoked_at = now
        db.commit()
        raise _refresh_token_401()

    user = db.get(User, row.user_id)
    if not user_is_login_eligible(user):
        raise _refresh_token_401()

    new_secret, new_row = issue_refresh_token(db, user=user, user_agent=user_agent, ip=ip)
    row.revoked_at = now
    row.replaced_by_id = new_row.id
    db.flush()
    return user, new_secret, new_row
