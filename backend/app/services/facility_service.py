# backend/app/services/facility_service.py
"""
Facility directory helpers (unified `facilities` table, see app/models/facility.py).

- `normalize_name(name)`            -> trimmed, lower-cased key used for every name comparison
- `resolve_facility(db, ...)`       -> Facility | None (id first, then case-insensitive trimmed name)
- `resolve_user_facility(db, user)` -> the actor's Facility (by facility_id, else by facility_name)
- `ensure_seed_facilities(db)`      -> inserts the default PHC / hospital names if missing
- `backfill_facility_ids(db)`       -> fills NULL *_id columns whose name matches a facility

Names are matched case-insensitively after trimming; substring matching is deliberately not used.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.facility import FACILITY_KINDS, Facility
from app.models.patient import Patient
from app.models.referral import Referral
from app.models.user import User

# Default directory seeded by init_db (unified table; kind derives from the list).
PHC_NAMES: list[str] = [
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

HOSPITAL_NAMES: list[str] = [
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


class UnknownFacilityError(ValueError):
    """A facility name / id supplied by a client does not exist (surfaced as HTTP 400)."""

    def __init__(self, name: Optional[str] = None, facility_id: Optional[UUID] = None):
        label = name if name else str(facility_id)
        super().__init__(f"Unknown facility: {label}")
        self.name = name
        self.facility_id = facility_id


def normalize_name(name: Optional[str]) -> str:
    """Trimmed + lower-cased (exactly what the SQL side does: lower(trim(col)))."""
    return (name or "").strip().lower()


def _norm_col(col):
    return func.lower(func.trim(col))


def resolve_facility(
    db: Session,
    *,
    facility_id: Optional[UUID] = None,
    name: Optional[str] = None,
    kind: Optional[str] = None,
) -> Optional[Facility]:
    """
    Look a facility up by id (preferred) or by case-insensitive, trimmed name.
    `kind` ('phc' | 'hospital'), when given, must also match. Returns None when nothing matches
    (or when the id exists but has a different kind).
    """
    if kind is not None and kind not in FACILITY_KINDS:
        return None

    if facility_id is not None:
        facility = db.get(Facility, facility_id)
        if facility is None:
            return None
        if kind is not None and facility.kind != kind:
            return None
        return facility

    key = normalize_name(name)
    if not key:
        return None
    stmt = select(Facility).where(_norm_col(Facility.name) == key)
    if kind is not None:
        stmt = stmt.where(Facility.kind == kind)
    rows = list(db.execute(stmt.order_by(Facility.name.asc())).scalars().all())
    if not rows:
        return None
    if len(rows) > 1:
        # Case-variants should not exist (seed data is unique); prefer an exact-case match.
        wanted = (name or "").strip()
        for row in rows:
            if row.name == wanted:
                return row
    return rows[0]


def require_facility(
    db: Session, *, name: Optional[str] = None, facility_id: Optional[UUID] = None, kind: Optional[str] = None
) -> Facility:
    """`resolve_facility` that raises UnknownFacilityError instead of returning None."""
    facility = resolve_facility(db, facility_id=facility_id, name=name, kind=kind)
    if facility is None:
        raise UnknownFacilityError(name=name, facility_id=facility_id)
    return facility


def resolve_user_facility(db: Session, user: User) -> Optional[Facility]:
    """
    The actor's own facility: by `facility_id` first, otherwise (legacy accounts created before
    the FK existed) by `facility_name`. None when the user has no facility or it is unknown.
    """
    if user.facility_id is not None:
        facility = db.get(Facility, user.facility_id)
        if facility is not None:
            return facility
    if user.facility_name:
        facility = resolve_facility(db, name=user.facility_name)
        if facility is not None:
            # Self-heal legacy accounts: link the FK now so that reads (which are id-first)
            # see exactly what this user writes. Mirrors what init_db's backfill does.
            user.facility_id = facility.id
            user.facility_name = facility.name
            user.facility_type = facility.kind
            db.add(user)
            db.flush()
        return facility
    return None


def ensure_seed_facilities(db: Session) -> int:
    """Insert the default PHC / hospital directory entries that are missing. Returns #inserted."""
    existing = {normalize_name(n) for n in db.scalars(select(Facility.name)).all()}
    inserted = 0
    for kind, names in (("phc", PHC_NAMES), ("hospital", HOSPITAL_NAMES)):
        for name in names:
            key = normalize_name(name)
            if key in existing:
                continue
            db.add(Facility(name=name, kind=kind))
            existing.add(key)
            inserted += 1
    db.flush()
    return inserted


def backfill_facility_ids(db: Session) -> dict[str, int]:
    """
    Fill NULL facility FKs from the name snapshots (case-insensitive, trimmed match) on
    users / patients / referrals. Idempotent; run by init_db after seeding so legacy rows whose
    facility only appeared in the seed list still get an id. Rows whose name matches nothing keep
    a NULL id and stay reachable through the legacy name fallback in app/core/authz.py.
    """
    by_key: dict[str, UUID] = {}
    for fid, fname in db.execute(select(Facility.id, Facility.name)).all():
        by_key.setdefault(normalize_name(fname), fid)

    counts = {"users": 0, "patients": 0, "referrals": 0}
    if not by_key:
        return counts

    targets = [
        ("users", User.__table__, "facility_id", "facility_name"),
        ("patients", Patient.__table__, "registered_facility_id", "registered_facility_name"),
        ("referrals", Referral.__table__, "from_facility_id", "from_facility"),
        ("referrals", Referral.__table__, "to_facility_id", "to_facility"),
    ]
    for label, table, id_col, name_col in targets:
        idc, namec = table.c[id_col], table.c[name_col]
        pending = db.execute(select(namec).distinct().where(idc.is_(None), namec.is_not(None))).scalars().all()
        for raw in pending:
            fid = by_key.get(normalize_name(raw))
            if fid is None:
                continue
            res = db.execute(
                update(table).where(idc.is_(None), _norm_col(namec) == normalize_name(raw)).values({id_col: fid})
            )
            counts[label] += res.rowcount if res.rowcount and res.rowcount > 0 else 0

    # Keep users.facility_type / facility_name in step with the directory row they point to
    # (a legacy case-variant duplicate could have re-pointed a "hospital" user at a PHC row).
    kind_by_id = {fid: (fname, kind) for fid, fname, kind in db.execute(select(Facility.id, Facility.name, Facility.kind)).all()}
    users = db.execute(select(User).where(User.facility_id.is_not(None))).scalars().all()
    for u in users:
        canon = kind_by_id.get(u.facility_id)
        if canon and (u.facility_type != canon[1] or u.facility_name != canon[0]):
            u.facility_name, u.facility_type = canon
            db.add(u)
    db.flush()
    return counts
