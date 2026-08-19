# backend/app/db/init_db.py
"""
Database initialisation — "bring any database to the current schema", built on Alembic.

    python -m app.db.init_db          (run from backend/, with DATABASE_URL + SECRET_KEY set)

What it does (idempotent, safe to re-run):
1. Legacy detection: a database that already has the Phase-1 tables (created by the pre-Alembic
   `Base.metadata.create_all()` path) but no `alembic_version` table is brought up to the
   0001_baseline shape (PostgreSQL only: the old idempotent `ADD COLUMN IF NOT EXISTS` helpers)
   and then STAMPED at `0001_baseline` — nothing is re-created.
2. `alembic upgrade head` (programmatically, using backend/alembic.ini + alembic/env.py) creates
   a fresh schema or applies the pending revisions (0002_facilities, ...). Works on PostgreSQL and
   SQLite alike.
3. Seeds the default facility directory (unified `facilities` table) and backfills NULL facility
   FKs whose name snapshot matches a facility (legacy rows).
4. Purges cached advisory analyses produced by any other engine.

Developers evolve the schema with Alembic directly:
    alembic revision --autogenerate -m "..." --rev-id 000N_slug
    alembic upgrade head          # or: python -m app.db.init_db
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.db.session import engine
from app.services.facility_service import (  # re-exported: tests and docs refer to these names
    HOSPITAL_NAMES,
    PHC_NAMES,
    backfill_facility_ids,
    ensure_seed_facilities,
)

__all__ = ["init_db", "alembic_config", "upgrade_to_head", "PHC_NAMES", "HOSPITAL_NAMES"]

_BACKEND_DIR = Path(__file__).resolve().parents[2]  # backend/
ALEMBIC_INI = _BACKEND_DIR / "alembic.ini"
ALEMBIC_DIR = _BACKEND_DIR / "alembic"

# Revision every pre-Alembic database is stamped with (see alembic/versions/0001_baseline.py).
LEGACY_BASELINE_REVISION = "0001_baseline"


def init_db(bind: Engine | None = None) -> None:
    """Stamp legacy databases, upgrade to head, seed facilities, purge foreign-engine caches."""
    bind = bind or engine

    if _is_legacy_database(bind):
        print(f"Existing pre-Alembic schema detected: stamping {LEGACY_BASELINE_REVISION} ...")
        _stamp_legacy_database(bind)

    print("Applying Alembic migrations (upgrade head)...")
    upgrade_to_head(bind)

    print("Seeding facilities...")
    _seed_facilities(bind)

    print("Purging cached advisory analyses from other engines...")
    _purge_foreign_engine_analyses(bind)
    print("Database initialization complete.")


# ---------------------------------------------------------------------------
# Alembic plumbing
# ---------------------------------------------------------------------------

def alembic_config() -> Config:
    """Alembic Config pointing at backend/alembic.ini + backend/alembic (CWD-independent)."""
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_DIR))
    cfg.attributes["configure_logger"] = False  # keep the application's logging config
    return cfg


def _run_alembic(bind: Engine, fn, *args) -> None:
    """Run an alembic command on a connection from `bind` inside one transaction."""
    cfg = alembic_config()
    with bind.begin() as conn:
        cfg.attributes["connection"] = conn
        fn(cfg, *args)


def upgrade_to_head(bind: Engine | None = None) -> None:
    _run_alembic(bind or engine, command.upgrade, "head")


# Tables that only exist from revision 0002 / 0003 onwards. If any of them is present in a
# database that has no `alembic_version` table, the schema was NOT produced by the pre-Alembic
# create_all path (e.g. it came from Base.metadata.create_all of the CURRENT models) and stamping
# it at 0001_baseline would make the next upgrade fail half-way ("relation already exists").
_POST_BASELINE_TABLES = ("facilities", "refresh_tokens", "auth_rate_limit_hits")


def _is_legacy_database(bind: Engine) -> bool:
    """Tables from the pre-Alembic era exist but Alembic has never run here."""
    tables = set(inspect(bind).get_table_names())
    if "alembic_version" in tables or "users" not in tables:
        return False
    newer = sorted(t for t in _POST_BASELINE_TABLES if t in tables)
    if newer:
        raise RuntimeError(
            "This database has no alembic_version table but already contains post-baseline "
            f"tables {newer}. It was not created by the pre-Alembic init_db, so it cannot be stamped "
            "automatically. Either recreate it (drop schema, then `python -m app.db.init_db`) or, if "
            "you know it matches a specific revision, run `alembic stamp <revision>` yourself."
        )
    return True


def _stamp_legacy_database(bind: Engine) -> None:
    # NOTE: the legacy path creates any missing baseline tables from the CURRENT ORM models
    # (see _ensure_columns_postgresql). That is only correct while no revision after
    # 0001_baseline alters those tables (clinical_events, audit_logs, ai_patient_analyses,
    # referral_status_history). If you add such a migration, teach this path to create the
    # 0001 shape instead (raw SQL) or drop legacy-stamp support.
    if bind.dialect.name == "postgresql":
        _ensure_columns_postgresql(bind)
    _run_alembic(bind, command.stamp, LEGACY_BASELINE_REVISION)


# ---------------------------------------------------------------------------
# Advisory cache hygiene
# ---------------------------------------------------------------------------

def _purge_foreign_engine_analyses(bind: Engine) -> None:
    """
    `ai_patient_analyses` is a cache. Rows produced by any engine other than the current
    rule-based one (e.g. LLM-era rows on an upgraded database) must not be served as if they
    came from this engine, so they are deleted here (and defensively in
    AIPatientService.get_existing); they are regenerated on next access.
    """
    from sqlalchemy import delete, or_

    from app.models.ai_patient_analysis import AIPatientAnalysis
    from app.services.advisory_rules import ENGINE_VERSION

    with Session(bind) as session:
        result = session.execute(
            delete(AIPatientAnalysis).where(
                or_(
                    AIPatientAnalysis.model_used.is_(None),
                    AIPatientAnalysis.model_used != ENGINE_VERSION,
                )
            )
        )
        session.commit()
        removed = result.rowcount if result.rowcount is not None and result.rowcount >= 0 else 0
        if removed:
            print(f"  removed {removed} stale analysis row(s)")


# ---------------------------------------------------------------------------
# Legacy (pre-Alembic) PostgreSQL databases: bring them to the 0001_baseline shape
# ---------------------------------------------------------------------------

# (table, column, SQL type) — every column added after its table first shipped, up to the baseline.
_LATE_COLUMNS: list[tuple[str, str, str]] = [
    # users
    ("users", "facility_type", "VARCHAR(32)"),
    ("users", "facility_id", "UUID"),
    ("users", "facility_name", "VARCHAR(255)"),
    ("users", "deleted_at", "TIMESTAMP WITH TIME ZONE"),
    # patients (facility-level access control)
    ("patients", "registered_facility_name", "VARCHAR(255)"),
    ("patients", "registered_facility_type", "VARCHAR(32)"),
    ("patients", "created_by_user_id", "UUID REFERENCES users(id) ON DELETE SET NULL"),
    # referrals
    ("referrals", "received_facility_status", "referral_status"),
]

_LATE_INDEXES: list[tuple[str, str, str]] = [
    ("ix_users_deleted_at", "users", "deleted_at"),
    ("ix_patients_registered_facility_name", "patients", "registered_facility_name"),
    ("ix_patients_created_by_user_id", "patients", "created_by_user_id"),
    ("ix_referrals_received_facility_status", "referrals", "received_facility_status"),
]

# Baseline tables that a very old (pre-remediation) database may lack and that can be created
# straight from the ORM (they have no facility FK): `referral_status_history` was added in the
# Phase-1 remediation. The two legacy facility tables are created by raw SQL (they are no longer
# ORM models; revision 0002 copies and drops them).
_CREATABLE_BASELINE_TABLES = ("clinical_events", "referral_status_history", "audit_logs", "ai_patient_analyses")
_LEGACY_FACILITY_TABLES = ("phc_facilities", "hospital_facilities")


def _ensure_columns_postgresql(bind: Engine) -> None:
    """
    Bring a pre-Alembic PostgreSQL database to the 0001_baseline shape before it is stamped:
    create baseline tables that are missing, add late-added columns/indexes. Uses IF NOT EXISTS.
    """
    from app.db.base import Base

    existing_tables = set(inspect(bind).get_table_names())
    for required in ("users", "patients", "referrals"):
        if required not in existing_tables:
            raise RuntimeError(
                f"Table '{required}' is missing but 'users' exists: this database is not a supported "
                "pre-Alembic SmartAama schema. Restore it or start from an empty database."
            )

    missing_orm = [t for t in _CREATABLE_BASELINE_TABLES if t not in existing_tables]
    if missing_orm:
        Base.metadata.create_all(bind=bind, tables=[Base.metadata.tables[t] for t in missing_orm])
    with bind.begin() as conn:
        for legacy in _LEGACY_FACILITY_TABLES:
            if legacy in existing_tables:
                continue
            conn.execute(text(
                f"CREATE TABLE IF NOT EXISTS {legacy} (name VARCHAR(255) NOT NULL, id UUID NOT NULL, "
                f"created_at TIMESTAMP WITH TIME ZONE NOT NULL, PRIMARY KEY (id))"
            ))
            conn.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS ix_{legacy}_name ON {legacy} (name)"))
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{legacy}_id ON {legacy} (id)"))
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{legacy}_created_at ON {legacy} (created_at)"))
    existing_tables = set(inspect(bind).get_table_names())

    with bind.begin() as conn:
        for table, column, sql_type in _LATE_COLUMNS:
            if table not in existing_tables:
                continue
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {sql_type}"))
        for index_name, table, column in _LATE_INDEXES:
            if table not in existing_tables:
                continue
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table} ({column})"))


# ---------------------------------------------------------------------------
# Seed data (unified facilities table)
# ---------------------------------------------------------------------------

def _seed_facilities(bind: Engine) -> None:
    """Insert the default PHC / hospital directory if missing, then backfill NULL facility FKs."""
    with Session(bind=bind) as session:
        inserted = ensure_seed_facilities(session)
        counts = backfill_facility_ids(session)
        session.commit()
        if inserted:
            print(f"  inserted {inserted} facility row(s)")
        filled = sum(counts.values())
        if filled:
            print(f"  backfilled facility ids: {counts}")


if __name__ == "__main__":
    init_db()
