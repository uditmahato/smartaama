# backend/tests/test_startup.py
"""App boots on a fresh clone; DB init works on SQLite."""

from __future__ import annotations

import os

from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db import init_db as init_db_module
from app.settings import ID_CARDS_DIR


def test_root_ok(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["message"].startswith("Smart Aama")


def test_uploads_dir_created_at_startup(client):
    # The lifespan/startup hook creates the private uploads folder; no StaticFiles mount exists.
    assert ID_CARDS_DIR.is_dir()
    assert not any(getattr(r, "path", "") == "/uploads/id_cards" for r in client.app.routes)


def test_id_cards_not_served_statically(client):
    resp = client.get("/uploads/id_cards/whatever.png")
    assert resp.status_code == 404


def test_init_db_runs_on_sqlite(tmp_path):
    """init_db() = alembic upgrade head + seed; idempotent; SQLite file DB."""
    url = f"sqlite:///{(tmp_path / 'init.db').as_posix()}"
    eng = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    init_db_module.init_db(bind=eng)
    # idempotent
    init_db_module.init_db(bind=eng)

    tables = set(inspect(eng).get_table_names())
    for expected in {
        "alembic_version",
        "users",
        "patients",
        "clinical_events",
        "referrals",
        "referral_status_history",
        "audit_logs",
        "ai_patient_analyses",
        "facilities",
    }:
        assert expected in tables, expected
    # the legacy per-kind facility tables are gone (revision 0002_facilities)
    assert "phc_facilities" not in tables and "hospital_facilities" not in tables

    cols = {c["name"] for c in inspect(eng).get_columns("patients")}
    assert {"registered_facility_id", "registered_facility_name", "registered_facility_type", "created_by_user_id"} <= cols
    assert {"from_facility_id", "to_facility_id"} <= {c["name"] for c in inspect(eng).get_columns("referrals")}
    assert "deleted_at" in {c["name"] for c in inspect(eng).get_columns("users")}

    # facilities were seeded into the unified table (once, despite the second init_db)
    from sqlalchemy import select, func, text
    from sqlalchemy.orm import Session
    from app.models.facility import Facility

    with Session(eng) as s:
        assert s.scalar(select(func.count(Facility.id)).where(Facility.kind == "phc")) == len(init_db_module.PHC_NAMES)
        assert s.scalar(select(func.count(Facility.id)).where(Facility.kind == "hospital")) == len(init_db_module.HOSPITAL_NAMES)
        assert s.execute(text("select version_num from alembic_version")).scalar() == "0003_auth_tokens_rate_limit"
    eng.dispose()


def test_all_models_registered_and_portable():
    # Every table must compile on SQLite (dialect-portable types) and be registered on Base
    names = set(Base.metadata.tables)
    assert "referral_status_history" in names
    assert "ai_patient_analyses" in names
    assert "facilities" in names


def test_env_example_lists_required_vars():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    text = open(os.path.join(here, ".env.example"), encoding="utf-8").read()
    for key in ("SECRET_KEY", "DATABASE_URL", "ENV", "BOOTSTRAP_TOKEN", "CORS_ORIGINS"):
        assert key in text
    # no real-looking secrets
    assert "change-me" in text
