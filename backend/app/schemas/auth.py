# backend/app/schemas/auth.py

from __future__ import annotations

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """
    Body of POST /auth/login and POST /auth/refresh.
    - access_token: short-lived JWT (Bearer), valid for `expires_in` seconds
    - refresh_token: opaque, single-use secret; exchange it at /auth/refresh for a new pair
    """

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access-token lifetime in seconds")
    refresh_token: str


class RefreshRequest(BaseModel):
    """Body of POST /auth/refresh."""

    refresh_token: str = Field(..., min_length=16, max_length=512)


class LogoutRequest(BaseModel):
    """Body of POST /auth/logout (revokes the presented refresh token; idempotent)."""

    refresh_token: str = Field(..., min_length=1, max_length=512)
