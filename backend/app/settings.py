# backend/app/settings.py
"""Filesystem locations (uploads). Configuration values live in app.core.config."""

from pathlib import Path

from app.core.config import settings

# Base backend folder (contains app/, requirements.txt, .env)
BASE_DIR = Path(__file__).resolve().parent.parent

# Private uploads root: UPLOADS_DIR env var if set, else backend/uploads
UPLOADS_DIR = Path(settings.UPLOADS_DIR).expanduser().resolve() if settings.UPLOADS_DIR else BASE_DIR / "uploads"
ID_CARDS_DIR = UPLOADS_DIR / "id_cards"
