"""0002_facilities: unified facility directory + facility foreign keys.

Revision ID: 0002_facilities
Revises: 0001_baseline
Create Date: 2026-08-18

Upgrade
1. Create `facilities` (id Uuid PK, name String(255) UNIQUE, kind 'phc'|'hospital', created_at).
2. Copy every row of `phc_facilities` (kind='phc') and `hospital_facilities` (kind='hospital')
   into it, PRESERVING ids (users.facility_id already points at them). A hospital whose name is a
   case-insensitive duplicate of a copied PHC name is skipped (the unified directory must resolve
   names unambiguously); user rows pointing at a skipped id are NULLed and then backfilled by name.
3. `users.facility_id` (existing column): NULL out values that reference no facility, then add the
   FK + index. Rows with a NULL id and a matching `facility_name` are backfilled.
4. `patients.registered_facility_id` (new, FK, NULL) backfilled from `registered_facility_name`
   by case-insensitive, trimmed name match.
5. `referrals.from_facility_id` / `to_facility_id` (new, FK, NULL) backfilled likewise.
6. Drop `phc_facilities` / `hospital_facilities`.

Rows whose name matches nothing keep a NULL id; app/core/authz.py falls back to the name for
NULL-id rows only. All ALTERs use batch mode so the migration also runs on SQLite.

Downgrade recreates the two legacy tables from `facilities` by kind (ids preserved) and drops
the FKs / new columns / `facilities`.
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_facilities"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Lightweight table handles for data operations (never import ORM models into migrations:
# they describe the *current* code, not the schema at this revision).
def _t_facilities() -> sa.Table:
    return sa.table(
        "facilities",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String(255)),
        sa.column("kind", sa.String(16)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )


def _t_legacy(name: str) -> sa.Table:
    return sa.table(
        name,
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String(255)),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def _norm_col(col):
    return sa.func.lower(sa.func.trim(col))


def _backfill_by_name(conn, table: str, id_col: str, name_col: str, by_key: dict[str, uuid.UUID]) -> None:
    """UPDATE <table> SET <id_col> = <facility id> WHERE <id_col> IS NULL AND lower(trim(<name_col>)) = key."""
    t = sa.table(table, sa.column(id_col, sa.Uuid()), sa.column(name_col, sa.String(255)))
    idc, namec = t.c[id_col], t.c[name_col]
    pending = conn.execute(sa.select(namec).distinct().where(idc.is_(None), namec.is_not(None))).scalars().all()
    for raw in pending:
        fid = by_key.get(_norm(raw))
        if fid is None:
            continue
        conn.execute(sa.update(t).where(idc.is_(None), _norm_col(namec) == _norm(raw)).values({id_col: fid}))


def upgrade() -> None:
    conn = op.get_bind()

    # 1. unified table --------------------------------------------------------------------
    op.create_table(
        "facilities",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('phc', 'hospital')", name="ck_facilities_kind"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_facilities_created_at"), "facilities", ["created_at"], unique=False)
    op.create_index(op.f("ix_facilities_id"), "facilities", ["id"], unique=False)
    op.create_index(op.f("ix_facilities_kind"), "facilities", ["kind"], unique=False)
    op.create_index(op.f("ix_facilities_name"), "facilities", ["name"], unique=True)

    # 2. copy legacy rows, ids preserved -------------------------------------------------------
    facilities = _t_facilities()
    by_key: dict[str, uuid.UUID] = {}
    for kind, legacy_name in (("phc", "phc_facilities"), ("hospital", "hospital_facilities")):
        legacy = _t_legacy(legacy_name)
        rows = conn.execute(sa.select(legacy.c.id, legacy.c.name, legacy.c.created_at).order_by(legacy.c.name)).all()
        for fid, fname, created_at in rows:
            key = _norm(fname)
            if not key or key in by_key:
                continue  # blank or case-insensitive duplicate: skip (its id becomes dangling -> NULLed below)
            conn.execute(sa.insert(facilities).values(id=fid, name=fname.strip(), kind=kind, created_at=created_at))
            by_key[key] = fid

    # 3. users.facility_id: NULL dangling values, then FK + index, then backfill by name --------
    users = sa.table("users", sa.column("facility_id", sa.Uuid()), sa.column("facility_name", sa.String(255)))
    conn.execute(
        sa.update(users)
        .where(users.c.facility_id.is_not(None), users.c.facility_id.not_in(sa.select(facilities.c.id)))
        .values(facility_id=None)
    )
    with op.batch_alter_table("users") as batch:
        batch.create_index(op.f("ix_users_facility_id"), ["facility_id"], unique=False)
        batch.create_foreign_key("fk_users_facility_id", "facilities", ["facility_id"], ["id"], ondelete="SET NULL")
    _backfill_by_name(conn, "users", "facility_id", "facility_name", by_key)

    # 4. patients.registered_facility_id ------------------------------------------------------
    with op.batch_alter_table("patients") as batch:
        batch.add_column(sa.Column("registered_facility_id", sa.Uuid(), nullable=True))
        batch.create_index(op.f("ix_patients_registered_facility_id"), ["registered_facility_id"], unique=False)
        batch.create_foreign_key(
            "fk_patients_registered_facility_id", "facilities", ["registered_facility_id"], ["id"], ondelete="SET NULL"
        )
    _backfill_by_name(conn, "patients", "registered_facility_id", "registered_facility_name", by_key)

    # 5. referrals.from_facility_id / to_facility_id ---------------------------------------------
    with op.batch_alter_table("referrals") as batch:
        batch.add_column(sa.Column("from_facility_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("to_facility_id", sa.Uuid(), nullable=True))
        batch.create_index(op.f("ix_referrals_from_facility_id"), ["from_facility_id"], unique=False)
        batch.create_index(op.f("ix_referrals_to_facility_id"), ["to_facility_id"], unique=False)
        batch.create_index("ix_referrals_route_ids", ["from_facility_id", "to_facility_id"], unique=False)
        batch.create_foreign_key(
            "fk_referrals_from_facility_id", "facilities", ["from_facility_id"], ["id"], ondelete="SET NULL"
        )
        batch.create_foreign_key(
            "fk_referrals_to_facility_id", "facilities", ["to_facility_id"], ["id"], ondelete="SET NULL"
        )
    _backfill_by_name(conn, "referrals", "from_facility_id", "from_facility", by_key)
    _backfill_by_name(conn, "referrals", "to_facility_id", "to_facility", by_key)

    # 6. drop the legacy tables ---------------------------------------------------------------
    for legacy_name in ("phc_facilities", "hospital_facilities"):
        op.drop_index(op.f(f"ix_{legacy_name}_name"), table_name=legacy_name)
        op.drop_index(op.f(f"ix_{legacy_name}_id"), table_name=legacy_name)
        op.drop_index(op.f(f"ix_{legacy_name}_created_at"), table_name=legacy_name)
        op.drop_table(legacy_name)


def downgrade() -> None:
    conn = op.get_bind()

    # recreate the legacy tables (same shape as 0001_baseline) and split `facilities` by kind
    for legacy_name in ("phc_facilities", "hospital_facilities"):
        op.create_table(
            legacy_name,
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f(f"ix_{legacy_name}_created_at"), legacy_name, ["created_at"], unique=False)
        op.create_index(op.f(f"ix_{legacy_name}_id"), legacy_name, ["id"], unique=False)
        op.create_index(op.f(f"ix_{legacy_name}_name"), legacy_name, ["name"], unique=True)

    facilities = _t_facilities()
    for kind, legacy_name in (("phc", "phc_facilities"), ("hospital", "hospital_facilities")):
        legacy = _t_legacy(legacy_name)
        conn.execute(
            sa.insert(legacy).from_select(
                ["id", "name", "created_at"],
                sa.select(facilities.c.id, facilities.c.name, facilities.c.created_at).where(facilities.c.kind == kind),
            )
        )

    with op.batch_alter_table("referrals") as batch:
        batch.drop_constraint("fk_referrals_to_facility_id", type_="foreignkey")
        batch.drop_constraint("fk_referrals_from_facility_id", type_="foreignkey")
        batch.drop_index("ix_referrals_route_ids")
        batch.drop_index(op.f("ix_referrals_to_facility_id"))
        batch.drop_index(op.f("ix_referrals_from_facility_id"))
        batch.drop_column("to_facility_id")
        batch.drop_column("from_facility_id")

    with op.batch_alter_table("patients") as batch:
        batch.drop_constraint("fk_patients_registered_facility_id", type_="foreignkey")
        batch.drop_index(op.f("ix_patients_registered_facility_id"))
        batch.drop_column("registered_facility_id")

    # users.facility_id itself belongs to the baseline: only the FK + index go away.
    with op.batch_alter_table("users") as batch:
        batch.drop_constraint("fk_users_facility_id", type_="foreignkey")
        batch.drop_index(op.f("ix_users_facility_id"))

    op.drop_index(op.f("ix_facilities_name"), table_name="facilities")
    op.drop_index(op.f("ix_facilities_kind"), table_name="facilities")
    op.drop_index(op.f("ix_facilities_id"), table_name="facilities")
    op.drop_index(op.f("ix_facilities_created_at"), table_name="facilities")
    op.drop_table("facilities")
