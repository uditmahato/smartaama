# backend/app/main.py

from __future__ import annotations

from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api_router import api_router
from app.core.config import settings
from app.settings import ID_CARDS_DIR


def _ensure_upload_dirs() -> None:
    """Create the private uploads folder (ID cards) so a fresh clone starts cleanly."""
    ID_CARDS_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    _ensure_upload_dirs()
    # Dev-only convenience: if ENV=dev and AUTO_INIT_DB=true, run init_db() (bring the schema to
    # the Alembic head, seed facilities, purge stale analyses).
    # Production: run `python -m app.db.init_db` explicitly (see README).
    if settings.ENV == "dev" and settings.AUTO_INIT_DB:
        from app.db.init_db import init_db  # local import: keeps app import light

        init_db()
    yield


def _app_version() -> str:
    """Version from the repository's VERSION file (single source of truth), or 0.0.0-dev."""
    for candidate in (Path(__file__).resolve().parents[2] / "VERSION", Path(__file__).resolve().parents[1] / "VERSION"):
        try:
            text = candidate.read_text(encoding="utf-8").strip()
            if text:
                return text
        except OSError:
            continue
    return "0.0.0-dev"


APP_VERSION = _app_version()

app = FastAPI(title="Smart Aama API", version=APP_VERSION, lifespan=lifespan)

# CORS for React frontend (explicit allowlist from CORS_ORIGINS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

# NOTE: uploaded ID cards are NOT served statically. They are private and only available to
# admins via GET /api/v1/admin/users/{user_id}/id-card.
_ensure_upload_dirs()


@app.get("/")
def root():
    return {"message": "Smart Aama backend running"}
