# backend/app/main.py

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api_router import api_router
from app.core.config import settings
from app.db.init_db import init_db

app = FastAPI(title="Smart Aama API", version="1.0.0")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
def _startup() -> None:
    """
    Dev-only convenience:
    - If ENV=dev and AUTO_INIT_DB=true, create tables if missing.
    - In production, use Alembic migrations instead.
    """
    if settings.ENV == "dev" and os.getenv("AUTO_INIT_DB", "false").lower() == "true":
        init_db()


@app.get("/")
def root():
    return {"message": "Smart Aama backend running"}
