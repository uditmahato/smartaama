# backend/tests/test_migrations.py
"""
Alembic is the schema mechanism: the migration chain must (a) produce exactly the schema the ORM
models describe, (b) round-trip, and (c) be what init_db() drives — including stamping a
pre-Alembic ("legacy") database at 0001_baseline and backfilling facility ids.

These tests use their own SQLite file databases (never the shared test engine).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from app.db import init_db as init_db_module
from app.db.base import Base
from app.db.init_db import alembic_config, init_db

HEAD_REVISION = "0003_auth_tokens_rate_limit"


def _engine(tmp_path, name="mig.db"):
    url = f"sqlite:///{(tmp_path / name).as_posix()}"
    return create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)


def _alembic(eng, fn, *args):
    cfg = alembic_config()
    with eng.begin() as conn:
        cfg.attributes["connection"] = conn
        fn(cfg, *args)


def _schema_diff(eng):
    with eng.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"compare_type": True, "render_as_batch": True})
        return compare_metadata(ctx, Base.metadata)


def _current_revision(eng):
    with eng.connect() as conn:
        return conn.execute(text("select version_num from alembic_version")).scalar()


# --------------------------------------------------------------------------- parity / round trip
def test_upgrade_head_matches_models(tmp_path):
    eng = _engine(tmp_path)
    _alembic(eng, command.upgrade, "head")
    assert _current_revision(eng) == HEAD_REVISION
    tables = set(inspect(eng).get_table_names())
    assert set(Base.metadata.tables) <= tables
    assert "phc_facilities" not in tables and "hospital_facilities" not in tables
    # autogenerate against the migrated schema finds nothing to do
    assert _schema_diff(eng) == []
    eng.dispose()


def test_downgrade_round_trip(tmp_path):
    eng = _engine(tmp_path)
    _alembic(eng, command.upgrade, "head")
    _alembic(eng, command.downgrade, "0001_baseline")
    tables = set(inspect(eng).get_table_names())
    assert {"phc_facilities", "hospital_facilities"} <= tables and "facilities" not in tables
    assert "registered_facility_id" not in {c["name"] for c in inspect(eng).get_columns("patients")}
    _alembic(eng, command.downgrade, "base")
    assert set(inspect(eng).get_table_names()) == {"alembic_version"}
    _alembic(eng, command.upgrade, "head")
    assert _schema_diff(eng) == []
    eng.dispose()


def test_init_db_on_fresh_sqlite_is_head_and_seeded(tmp_path):
    eng = _engine(tmp_path)
    init_db(bind=eng)
    assert _current_revision(eng) == HEAD_REVISION
    assert _schema_diff(eng) == []
    with eng.connect() as conn:
        n_phc = conn.execute(text("select count(*) from facilities where kind='phc'")).scalar()
        n_hosp = conn.execute(text("select count(*) from facilities where kind='hospital'")).scalar()
    assert n_phc == len(init_db_module.PHC_NAMES) and n_hosp == len(init_db_module.HOSPITAL_NAMES)
    eng.dispose()


# --------------------------------------------------------------------------- legacy database
def _legacy_rows(eng):
    """Insert Phase-1 style rows (facility NAMES only) into a 0001_baseline schema."""
    now = datetime.now(timezone.utc)
    phc = sa.table("phc_facilities", sa.column("id", sa.Uuid()), sa.column("name", sa.String()), sa.column("created_at", sa.DateTime(timezone=True)))
    hosp = sa.table("hospital_facilities", sa.column("id", sa.Uuid()), sa.column("name", sa.String()), sa.column("created_at", sa.DateTime(timezone=True)))
    users = sa.table(
        "users",
        sa.column("id", sa.Uuid()), sa.column("username", sa.String()), sa.column("email", sa.String()),
        sa.column("role", sa.String()), sa.column("is_super_admin", sa.Boolean()), sa.column("password_hash", sa.String()),
        sa.column("is_active", sa.Boolean()), sa.column("is_approved", sa.Boolean()), sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("facility_id", sa.Uuid()), sa.column("facility_name", sa.String()), sa.column("facility_type", sa.String()),
    )
    patients = sa.table(
        "patients",
        sa.column("id", sa.Uuid()), sa.column("patient_id", sa.String()), sa.column("first_name", sa.String()),
        sa.column("last_name", sa.String()), sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("registered_facility_name", sa.String()), sa.column("registered_facility_type", sa.String()),
    )
    referrals = sa.table(
        "referrals",
        sa.column("id", sa.Uuid()), sa.column("patient_id", sa.Uuid()), sa.column("from_facility", sa.String()),
        sa.column("to_facility", sa.String()), sa.column("status", sa.String()), sa.column("reason", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    ids = {
        "phc": uuid.uuid4(), "hosp": uuid.uuid4(), "u_named": uuid.uuid4(), "u_dangling": uuid.uuid4(),
        "u_unknown": uuid.uuid4(), "p1": uuid.uuid4(), "p2": uuid.uuid4(), "p3": uuid.uuid4(), "r1": uuid.uuid4(), "r2": uuid.uuid4(),
    }
    with eng.begin() as conn:
        conn.execute(sa.insert(phc).values(id=ids["phc"], name="PHC Legacy", created_at=now))
        conn.execute(sa.insert(hosp).values(id=ids["hosp"], name="Legacy Hospital", created_at=now))
        base_user = dict(role="CLINICIAN", is_super_admin=False, password_hash="x", is_active=True, is_approved=True, created_at=now)
        conn.execute(sa.insert(users).values(id=ids["u_named"], username="named", email="named@x", facility_id=None, facility_name="PHC Legacy", facility_type="phc", **base_user))
        conn.execute(sa.insert(users).values(id=ids["u_dangling"], username="dangling", email="dangling@x", facility_id=uuid.uuid4(), facility_name=" legacy hospital ", facility_type="hospital", **base_user))
        conn.execute(sa.insert(users).values(id=ids["u_unknown"], username="unknown", email="unknown@x", facility_id=None, facility_name="Unknown Clinic", facility_type="phc", **base_user))
        conn.execute(sa.insert(patients).values(id=ids["p1"], patient_id="PAT-1", first_name="a", last_name="b", created_at=now, registered_facility_name="PHC Legacy", registered_facility_type="phc"))
        conn.execute(sa.insert(patients).values(id=ids["p2"], patient_id="PAT-2", first_name="a", last_name="b", created_at=now, registered_facility_name="  phc legacy", registered_facility_type="phc"))
        conn.execute(sa.insert(patients).values(id=ids["p3"], patient_id="PAT-3", first_name="a", last_name="b", created_at=now, registered_facility_name="Unknown Clinic", registered_facility_type="phc"))
        conn.execute(sa.insert(referrals).values(id=ids["r1"], patient_id=ids["p1"], from_facility="PHC Legacy", to_facility="LEGACY HOSPITAL", status="SUBMITTED", reason="r", created_at=now))
        conn.execute(sa.insert(referrals).values(id=ids["r2"], patient_id=ids["p3"], from_facility="Unknown Clinic", to_facility="Legacy Hospital", status="SUBMITTED", reason="r", created_at=now))
    return ids


def test_init_db_stamps_and_upgrades_legacy_database(tmp_path):
    """
    A database created by the pre-Alembic init_db (Phase-1 create_all: tables present, no
    alembic_version) is stamped 0001_baseline, upgraded to head, and its facility ids are
    backfilled by case-insensitive trimmed name; unknown names keep NULL ids.
    """
    eng = _engine(tmp_path, "legacy.db")
    _alembic(eng, command.upgrade, "0001_baseline")
    with eng.begin() as conn:
        conn.execute(text("DROP TABLE alembic_version"))  # exactly what a create_all-built DB looks like
    ids = _legacy_rows(eng)
    assert init_db_module._is_legacy_database(eng)

    init_db(bind=eng)

    assert _current_revision(eng) == HEAD_REVISION
    assert _schema_diff(eng) == []
    with eng.connect() as conn:
        fac = {name: (fid, kind) for fid, name, kind in conn.execute(text("select id, name, kind from facilities")).all()}
        # legacy rows copied with their ids preserved, seed rows added next to them
        assert uuid.UUID(hex=fac["PHC Legacy"][0]) == ids["phc"] and fac["PHC Legacy"][1] == "phc"
        assert uuid.UUID(hex=fac["Legacy Hospital"][0]) == ids["hosp"] and fac["Legacy Hospital"][1] == "hospital"
        assert set(init_db_module.PHC_NAMES) <= set(fac)
        assert "phc_facilities" not in inspect(eng).get_table_names()

        users = {u: (fid, name) for u, fid, name in conn.execute(text("select username, facility_id, facility_name from users")).all()}
        assert uuid.UUID(hex=users["named"][0]) == ids["phc"]            # backfilled by name
        assert uuid.UUID(hex=users["dangling"][0]) == ids["hosp"]        # dangling id NULLed, then backfilled by name
        assert users["unknown"][0] is None                               # unknown name stays NULL

        pats = {p: fid for p, fid in conn.execute(text("select patient_id, registered_facility_id from patients")).all()}
        assert uuid.UUID(hex=pats["PAT-1"]) == ids["phc"]
        assert uuid.UUID(hex=pats["PAT-2"]) == ids["phc"]                # '  phc legacy' -> trimmed, case-insensitive
        assert pats["PAT-3"] is None

        refs = {f: (fi, ti) for f, fi, ti in conn.execute(text("select from_facility, from_facility_id, to_facility_id from referrals")).all()}
        assert uuid.UUID(hex=refs["PHC Legacy"][0]) == ids["phc"] and uuid.UUID(hex=refs["PHC Legacy"][1]) == ids["hosp"]
        assert refs["Unknown Clinic"][0] is None and uuid.UUID(hex=refs["Unknown Clinic"][1]) == ids["hosp"]

    # a second run is a no-op (already stamped + at head)
    assert not init_db_module._is_legacy_database(eng)
    init_db(bind=eng)
    assert _current_revision(eng) == HEAD_REVISION
    eng.dispose()
