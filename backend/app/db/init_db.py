from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import select, text

# Ensure these imports match your actual file structure
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.models.facility import PHCFacility, HospitalFacility


def init_db() -> None:
    """
    Creates all tables.

    NOTE:
    - In production, prefer Alembic migrations.
    - This is useful for local bootstrap in early development.
    """
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    print("Running DDL updates...")
    _ensure_user_facility_columns()
    _ensure_referral_received_status_column()
    
    print("Seeding facilities...")
    _seed_facilities()
    print("Database initialization complete.")


def _ensure_user_facility_columns() -> None:
    """Backfill facility columns on users table if missing (Postgres-safe)."""

    ddl = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS facility_type VARCHAR(32)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS facility_id UUID",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS facility_name VARCHAR(255)",
    ]

    with engine.begin() as conn:
        for statement in ddl:
            conn.execute(text(statement))


def _ensure_referral_received_status_column() -> None:
    """Add received_facility_status column to referrals table if missing."""
    
    ddl = [
        "ALTER TABLE referrals ADD COLUMN IF NOT EXISTS received_facility_status referral_status",
    ]
    
    with engine.begin() as conn:
        for statement in ddl:
            conn.execute(text(statement))


def _seed_facilities() -> None:
    """Insert default PHC and hospital facility names if missing."""

    phc_names = [
        "PHC Dhadingbesi",
        "PHC Charikot",
        "PHC Salleri",
        "PHC Jiri",
        "PHC Gorkha Bazaar",
        "PHC Syangja",
        "PHC Lamahi",
        "PHC Diktel",
        "PHC Manthali",
        "PHC Khalanga",
    ]

    hospital_names = [
        "Bir Hospital",
        "Teaching Hospital Maharajgunj",
        "Gandaki Medical College",
        "BP Koirala Memorial Hospital",
        "Lumbini Provincial Hospital",
        "Janakpur Zonal Hospital",
        "Seti Provincial Hospital",
        "Koshi Hospital",
        "Rapti Sub-Regional Hospital",
        "Dhulikhel Hospital",
    ]

    with SessionLocal() as session:
        _ensure_names(session, PHCFacility, phc_names)
        _ensure_names(session, HospitalFacility, hospital_names)
        session.commit()


def _ensure_names(session: Session, model, names: list[str]) -> None:
    existing = set(session.scalars(select(model.name)).all())
    missing = [name for name in names if name not in existing]
    for name in missing:
        session.add(model(name=name))

# --- THIS PART IS CRITICAL TO RUN THE SCRIPT ---
if __name__ == "__main__":
    init_db()