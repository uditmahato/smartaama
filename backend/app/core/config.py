# backend/app/core/config.py

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env (next to requirements.txt), independent of the current working directory.
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """
    Application configuration.

    Every environment variable the backend reads is declared here (see backend/.env.example).
    - For local dev, put them in `backend/.env` or export them in your shell.
    - In production, set env vars in your runtime environment (systemd, k8s, etc.).
    Unknown keys in the .env file are ignored (`extra="ignore"`).
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Environment
    ENV: str = Field(default="dev", description="dev|staging|prod")

    # Security
    SECRET_KEY: str = Field(..., min_length=32, description="JWT signing secret (>= 32 chars)")
    JWT_ALGORITHM: str = Field(default="HS256")
    # Access JWTs are stateless (not revocable): keep them short and let clients renew them with
    # the refresh token. Refresh tokens are server-side rows (revocable, rotated on every use).
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=60 * 24 * 7)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=14, ge=1, le=365, description="Refresh-token lifetime in days")

    # Bootstrap (dev only): /auth/bootstrap-admin is refused unless ENV=dev AND this is non-empty
    BOOTSTRAP_TOKEN: str = Field(default="", description="Token required for /auth/bootstrap-admin in dev")

    # Database
    DATABASE_URL: str = Field(..., description="SQLAlchemy database URL")

    # Dev convenience: run init_db() on startup when ENV=dev (brings the schema to the Alembic
    # head, seeds facilities, purges stale advisory analyses). Production: python -m app.db.init_db
    AUTO_INIT_DB: bool = Field(default=False, description="dev only: initialise the DB schema on startup")

    # CORS - store as string, parse in property
    CORS_ORIGINS_STR: str = Field(
        default="http://localhost:5173,http://localhost:5174,http://localhost:3000",
        description="Comma-separated CORS origins",
        alias="CORS_ORIGINS",
    )

    # Uploads: root folder for private uploads (ID cards live in <UPLOADS_DIR>/id_cards).
    # Default: backend/uploads. Point it at a persistent volume in production.
    UPLOADS_DIR: Optional[str] = Field(default=None, description="Private uploads root (default backend/uploads)")
    MAX_ID_CARD_SIZE_MB: int = Field(default=5, ge=1, le=50, description="Max ID-card upload size in MB")

    # Database-backed sliding-window rate limiting for /auth/login, /auth/register and /auth/refresh
    # (per client IP; shared by every worker/process using the same database).
    RATE_LIMIT_DISABLED: bool = Field(default=False, description="Set to true to disable auth rate limiting (tests)")
    RATE_LIMIT_MAX_REQUESTS: int = Field(default=10, ge=1, description="Max auth requests per IP per window")
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, ge=1, description="Sliding window length in seconds")

    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if not self.CORS_ORIGINS_STR:
            return ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]
        return [x.strip() for x in self.CORS_ORIGINS_STR.split(",") if x.strip()]

    @field_validator("ENV", mode="before")
    @classmethod
    def normalize_env(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        v = v.strip().lower()
        if v not in {"dev", "staging", "prod"}:
            raise ValueError("ENV must be one of: dev, staging, prod")
        return v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("DATABASE_URL is required")
        return v.strip()

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret(cls, v: str) -> str:
        if not isinstance(v, str) or len(v.strip()) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v.strip()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
