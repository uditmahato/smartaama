# backend/app/models/refresh_token.py
"""
Server-side refresh tokens (one row per issued token).

The client receives an opaque secret (`secrets.token_urlsafe(32)`); only its SHA-256 hex digest
is stored here, so a database leak does not leak usable tokens. `POST /auth/refresh` rotates:
the presented row is revoked (`revoked_at`, `replaced_by_id` -> the successor) and a new pair is
issued. Presenting an already-revoked token is treated as token theft/reuse and revokes every
token of that user (see app/core/security.py). Access JWTs stay stateless and are NOT tracked
here — they simply expire after ACCESS_TOKEN_EXPIRE_MINUTES.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utcnow
from app.models.user import User  # noqa: F401  (FK target must be registered before RefreshToken)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE", name="fk_refresh_tokens_user_id"),
        nullable=False,
        index=True,
    )

    # sha256 hex digest (64 chars) of the opaque secret handed to the client. Never the secret.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    # Set on rotation (/auth/refresh), logout, admin action or reuse detection.
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # On rotation: the id of the token that superseded this one (audit trail of the chain).
    replaced_by_id: Mapped[Optional[UUID]] = mapped_column(Uuid(as_uuid=True), nullable=True)

    # Where the token was issued from (informational; shown nowhere yet, useful for forensics).
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    user: Mapped["User"] = relationship("User", lazy="select")

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def __repr__(self) -> str:
        return f"<RefreshToken id={self.id} user_id={self.user_id} revoked={self.is_revoked} expires_at={self.expires_at}>"
