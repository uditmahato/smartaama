# backend/app/core/config.py

from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration.

    Note:
    - For local dev, set environment variables in your shell or a root `.env`.
    - In production, set env vars in your runtime environment (systemd, k8s, etc.).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        json_schema_extra={"parse_env_var": False},
    )

    # Environment
    ENV: str = Field(default="dev", description="dev|staging|prod")

    # Security
    SECRET_KEY: str = Field(..., min_length=32, description="JWT signing secret")
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60, ge=5, le=60 * 24 * 7)

    # Bootstrap (dev only)
    BOOTSTRAP_TOKEN: str = Field(default="", description="Token required for /auth/bootstrap-admin in dev")

    # Database
    DATABASE_URL: str = Field(..., description="SQLAlchemy database URL")

    # CORS - store as string, parse in property
    CORS_ORIGINS_STR: str = Field(
        default="http://localhost:5173,http://localhost:5174,http://localhost:3000",
        description="Comma-separated CORS origins",
        alias="CORS_ORIGINS",
    )

    @property
    def CORS_ORIGINS(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if not self.CORS_ORIGINS_STR:
            return ["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"]
        return [x.strip() for x in self.CORS_ORIGINS_STR.split(",") if x.strip()]

    # Optional: vector DB settings (not used until you implement ingestion/retrieval)
    VECTOR_DB: str = Field(default="qdrant", description="qdrant|weaviate")
    QDRANT_URL: Optional[str] = Field(default=None)
    WEAVIATE_URL: Optional[str] = Field(default=None)

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
