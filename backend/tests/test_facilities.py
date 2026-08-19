# backend/tests/test_facilities.py
"""
Facility identity by foreign key (unified `facilities` table):
- GET /facilities shape
- names sent by clients must resolve to a facility (400 / 404 otherwise)
- new patients / referrals carry facility ids
- authorization is id-first; the name snapshot is only consulted for legacy rows whose id is NULL
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.facility import Facility
from app.models.patient import Patient
from app.models.referral import Referral, ReferralStatus
from app.models.user import User
from tests.conftest import FACILITY_A, FACILITY_B, HOSPITAL_X, bearer, create_patient, REGISTER_PASSWORD, BOOTSTRAP_PASSWORD

FACILITIES = "/api/v1/facilities"
PATIENTS = "/api/v1/patients"
REFERRALS = "/api/v1/referrals"
REGISTER = "/api/v1/auth/register"
BOOTSTRAP = "/api/v1/auth/bootstrap-admin"


def _referral(client, headers, patient_id, from_facility=FACILITY_A, to_facility=FACILITY_B, **extra):
    payload = {"patient_id": patient_id, "from_facility": from_facility, "to_facility": to_facility, "reason": "Needs specialist review"}
    payload.update(extra)
    return client.post(REFERRALS, json=payload, headers=headers)


def _legacy_patient(db, name, **overrides) -> Patient:
    """A row as written before revision 0002: name snapshot only, NULL facility id."""
    p = Patient(
        patient_id=f"PAT-LEG-{uuid.uuid4().hex[:6].upper()}",
        first_name="Legacy",
        last_name="Row",
        registered_facility_id=None,
        registered_facility_name=name,
        registered_facility_type="phc",
        **overrides,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _legacy_referral(db, patient_id, from_name, to_name) -> Referral:
    r = Referral(
        patient_id=patient_id,
        from_facility_id=None,
        to_facility_id=None,
        from_facility=from_name,
        to_facility=to_name,
        status=ReferralStatus.SUBMITTED,
        reason="legacy referral",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


# --------------------------------------------------------------------------- GET /facilities
def test_list_facilities_shape_and_filters(client, seeded_facilities):
    resp = client.get(FACILITIES, params={"kind": "phc"})
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert items and all(set(i) == {"id", "name", "kind"} for i in items)
    assert all(i["kind"] == "phc" for i in items)
    by_name = {i["name"]: i for i in items}
    assert by_name[FACILITY_A]["id"] == str(seeded_facilities[FACILITY_A])
    assert FACILITY_B in by_name and HOSPITAL_X not in by_name

    hosp = client.get(FACILITIES, params={"kind": "hospital"}).json()
    assert {i["name"] for i in hosp} == {HOSPITAL_X}
    assert hosp[0]["id"] == str(seeded_facilities[HOSPITAL_X]) and hosp[0]["kind"] == "hospital"

    # q is a case-insensitive substring filter; kind is optional (all facilities)
    assert {i["name"] for i in client.get(FACILITIES, params={"kind": "phc", "q": "phc b"}).json()} == {FACILITY_B}
    assert {i["name"] for i in client.get(FACILITIES).json()} == {FACILITY_A, FACILITY_B, HOSPITAL_X}
    assert client.get(FACILITIES, params={"kind": "clinic"}).status_code == 422


# --------------------------------------------------------------------------- registration / bootstrap
def test_register_requires_matching_kind(client, seeded_facilities):
    form = {
        "email": "kind.mismatch@example.test",
        "password": REGISTER_PASSWORD,
        "full_name": "Kind Mismatch",
        "phone_number": "9800000000",
        "nmc_number": "NMC-2",
        "working_hospital": HOSPITAL_X,
        "facility_type": "phc",  # Hospital X is a hospital
        "facility_id": str(seeded_facilities[HOSPITAL_X]),
    }
    assert client.post(REGISTER, data=form).status_code == 404
    form["facility_type"] = "hospital"
    resp = client.post(REGISTER, data=form)
    assert resp.status_code == 201, resp.text
    user = resp.json()["user"]
    assert user["facility_id"] == str(seeded_facilities[HOSPITAL_X])
    assert user["facility_name"] == HOSPITAL_X and user["facility_type"] == "hospital"


def test_bootstrap_requires_matching_kind(client, seeded_facilities):
    payload = {"username": "boot", "password": BOOTSTRAP_PASSWORD, "facility_kind": "phc", "facility_id": str(seeded_facilities[HOSPITAL_X])}
    assert client.post(BOOTSTRAP, json=payload, headers={"X-Bootstrap-Token": "test-bootstrap-token"}).status_code == 404
    payload["facility_kind"] = "hospital"
    resp = client.post(BOOTSTRAP, json=payload, headers={"X-Bootstrap-Token": "test-bootstrap-token"})
    assert resp.status_code == 201, resp.text
    assert resp.json()["facility_id"] == str(seeded_facilities[HOSPITAL_X])


# --------------------------------------------------------------------------- patients
def test_patient_create_sets_facility_id_and_canonical_name(client, clinician_a, seeded_facilities, make_user):
    p = create_patient(client, bearer(clinician_a))
    assert p["registered_facility_id"] == str(seeded_facilities[FACILITY_A])
    assert p["registered_facility_name"] == FACILITY_A and p["registered_facility_type"] == "phc"

    # a user whose stored name differs in case/whitespace still registers under the same facility id
    odd = make_user("odd-a", facility_name="  phc a ")
    p2 = create_patient(client, bearer(odd))
    assert p2["registered_facility_id"] == str(seeded_facilities[FACILITY_A])
    assert p2["registered_facility_name"] == FACILITY_A  # canonical snapshot from the directory


def test_admin_patient_facility_must_exist(client, admin_user, seeded_facilities, patient_a):
    resp = client.post(PATIENTS, json={"first_name": "A", "last_name": "B", "registered_facility_name": "Nowhere Clinic"}, headers=bearer(admin_user))
    assert resp.status_code == 400
    assert "Unknown facility: Nowhere Clinic" in resp.json()["detail"]

    p = create_patient(client, bearer(admin_user), registered_facility_name="hospital x")  # case-insensitive
    assert p["registered_facility_id"] == str(seeded_facilities[HOSPITAL_X])
    assert p["registered_facility_name"] == HOSPITAL_X and p["registered_facility_type"] == "hospital"

    # PATCH: unknown -> 400, known -> FK + snapshots follow
    url = f"{PATIENTS}/{patient_a['id']}"
    assert client.patch(url, json={"registered_facility_name": "Nowhere Clinic"}, headers=bearer(admin_user)).status_code == 400
    resp = client.patch(url, json={"registered_facility_name": FACILITY_B}, headers=bearer(admin_user))
    assert resp.status_code == 200, resp.text
    assert resp.json()["registered_facility_id"] == str(seeded_facilities[FACILITY_B])
    assert resp.json()["registered_facility_name"] == FACILITY_B


def test_user_with_unknown_facility_cannot_register_patients(client, make_user, db):
    """Legacy account whose facility name resolves to nothing: no id can be assigned -> 400."""
    ghost = make_user("ghost", facility_name="PHC Ghost")
    u = db.get(User, ghost.id)
    u.facility_id = None
    db.execute(Facility.__table__.delete().where(Facility.name == "PHC Ghost"))
    db.commit()
    resp = client.post(PATIENTS, json={"first_name": "A", "last_name": "B"}, headers=bearer(ghost))
    assert resp.status_code == 400
    assert "not in the facility directory" in resp.json()["detail"]


# --------------------------------------------------------------------------- referrals
def test_referral_unknown_facility_400(client, patient_a, clinician_a):
    resp = _referral(client, bearer(clinician_a), patient_a["id"], to_facility="Nowhere Hospital")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Unknown facility: Nowhere Hospital"
    resp = _referral(client, bearer(clinician_a), patient_a["id"], from_facility="Nowhere PHC", to_facility=FACILITY_B)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Unknown facility: Nowhere PHC"


def test_referral_ids_populated_on_create(client, patient_a, clinician_a, seeded_facilities, admin_user):
    resp = _referral(client, bearer(clinician_a), patient_a["id"], from_facility="  phc a ", to_facility="hospital x")
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["from_facility_id"] == str(seeded_facilities[FACILITY_A])
    assert body["to_facility_id"] == str(seeded_facilities[HOSPITAL_X])
    # names are stored as the directory spells them
    assert body["from_facility"] == FACILITY_A and body["to_facility"] == HOSPITAL_X

    # non-admin from_facility check is by id: another real facility -> 400
    assert _referral(client, bearer(clinician_a), patient_a["id"], from_facility=FACILITY_B, to_facility=HOSPITAL_X).status_code == 400
    # admin may send from any facility
    assert _referral(client, bearer(admin_user), patient_a["id"], from_facility=HOSPITAL_X, to_facility=FACILITY_B).status_code == 201


# --------------------------------------------------------------------------- authorization: id-first
def test_access_is_by_facility_id_even_if_names_differ(client, db, patient_a, make_user, seeded_facilities, clinician_a):
    """The user's facility_id decides; the user's name snapshot is irrelevant when ids exist."""
    renamed = make_user("renamed", facility_name=FACILITY_A)
    u = db.get(User, renamed.id)
    u.facility_name = "PHC A (renamed in the directory later)"
    db.commit()
    assert u.facility_id == seeded_facilities[FACILITY_A]
    url = f"{PATIENTS}/{patient_a['id']}"
    assert client.get(url, headers=bearer(renamed)).status_code == 200
    assert [p["id"] for p in client.get(PATIENTS, headers=bearer(renamed)).json()] == [patient_a["id"]]

    # a user with a matching NAME but a different facility id gets nothing (row has an id -> no name fallback)
    impostor = make_user("impostor", facility_name=FACILITY_B)
    u2 = db.get(User, impostor.id)
    u2.facility_name = FACILITY_A
    db.commit()
    assert client.get(url, headers=bearer(impostor)).status_code == 403
    assert client.get(PATIENTS, headers=bearer(impostor)).json() == []

    # referral party checks follow the same rule
    ref = _referral(client, bearer(clinician_a), patient_a["id"], to_facility=HOSPITAL_X).json()
    assert client.get(f"{REFERRALS}/{ref['id']}", headers=bearer(renamed)).status_code == 200
    assert client.get(f"{REFERRALS}/{ref['id']}", headers=bearer(impostor)).status_code == 403
    assert {r["id"] for r in client.get(REFERRALS, params={"direction": "outgoing"}, headers=bearer(renamed)).json()} == {ref["id"]}
    assert client.get(REFERRALS, headers=bearer(impostor)).json() == []


def test_legacy_rows_fall_back_to_name_only_when_id_is_null(client, db, clinician_a, clinician_b, hospital_x, viewer_a, admin_user):
    """
    Rows written before 0002 (NULL facility id) are matched by name; a NULL-id row whose name
    matches nobody is admin-only. Referral party checks and list scoping behave the same way.
    """
    legacy_a = _legacy_patient(db, FACILITY_A)              # exact
    legacy_a2 = _legacy_patient(db, "  phc a ")             # trimmed / case-insensitive
    legacy_zzz = _legacy_patient(db, "PHC ZZZ")             # matches no user
    for p in (legacy_a, legacy_a2):
        assert client.get(f"{PATIENTS}/{p.id}", headers=bearer(clinician_a)).status_code == 200
        assert client.get(f"{PATIENTS}/{p.id}", headers=bearer(viewer_a)).status_code == 200
        assert client.get(f"{PATIENTS}/{p.id}", headers=bearer(clinician_b)).status_code == 403
    assert client.get(f"{PATIENTS}/{legacy_zzz.id}", headers=bearer(clinician_a)).status_code == 403
    assert client.get(f"{PATIENTS}/{legacy_zzz.id}", headers=bearer(admin_user)).status_code == 200
    listed = {p["id"] for p in client.get(PATIENTS, headers=bearer(clinician_a)).json()}
    assert listed == {str(legacy_a.id), str(legacy_a2.id)}

    # legacy referral (NULL ids, names only): B is the receiver by name -> B gains access to the patient
    ref = _legacy_referral(db, legacy_a.id, FACILITY_A, "phc b")
    assert client.get(f"{PATIENTS}/{legacy_a.id}", headers=bearer(clinician_b)).status_code == 200
    assert client.get(f"{REFERRALS}/{ref.id}", headers=bearer(clinician_b)).status_code == 200
    assert client.get(f"{REFERRALS}/{ref.id}", headers=bearer(hospital_x)).status_code == 403
    assert {r["id"] for r in client.get(REFERRALS, params={"direction": "incoming"}, headers=bearer(clinician_b)).json()} == {str(ref.id)}
    assert {r["id"] for r in client.get(REFERRALS, params={"direction": "outgoing"}, headers=bearer(clinician_a)).json()} == {str(ref.id)}
    # only the receiving facility (by name, legacy) may set the received status
    assert client.post(f"{REFERRALS}/{ref.id}/received-status", json={"received_facility_status": "received"}, headers=bearer(clinician_a)).status_code == 403
    assert client.post(f"{REFERRALS}/{ref.id}/received-status", json={"received_facility_status": "received"}, headers=bearer(clinician_b)).status_code == 200

    # a user with a NULL facility id and a matching name still reaches legacy rows...
    u = db.get(User, clinician_a.id)
    u.facility_id = None
    db.commit()
    assert client.get(f"{PATIENTS}/{legacy_a.id}", headers=bearer(clinician_a)).status_code == 200
    # ...but not rows that carry an id (a real patient of facility A): the name is never used for those
    real = create_patient(client, bearer(admin_user), registered_facility_name=FACILITY_A)
    assert client.get(f"{PATIENTS}/{real['id']}", headers=bearer(clinician_a)).status_code == 403


def test_user_without_any_facility_sees_nothing_even_for_legacy_rows(client, db, make_user):
    _legacy_patient(db, FACILITY_A)
    orphan = make_user("orphan")
    assert client.get(PATIENTS, headers=bearer(orphan)).json() == []
    assert client.get(REFERRALS, headers=bearer(orphan)).json() == []


def test_seed_and_backfill_helpers(db, seeded_facilities, clinician_a):
    """ensure_seed_facilities is idempotent; backfill_facility_ids fills NULL ids by name."""
    from app.services.facility_service import backfill_facility_ids, ensure_seed_facilities, resolve_facility

    first = ensure_seed_facilities(db)
    assert first > 0
    assert ensure_seed_facilities(db) == 0
    assert resolve_facility(db, name=" bir hospital ").kind == "hospital"
    assert resolve_facility(db, name="Bir Hospital", kind="phc") is None
    assert resolve_facility(db, facility_id=seeded_facilities[FACILITY_A], kind="hospital") is None
    assert resolve_facility(db, facility_id=seeded_facilities[FACILITY_A]).name == FACILITY_A

    legacy = _legacy_patient(db, "phc a")
    ref = _legacy_referral(db, legacy.id, FACILITY_A, "Nowhere")
    counts = backfill_facility_ids(db)
    db.commit()
    db.refresh(legacy)
    db.refresh(ref)
    assert counts["patients"] == 1 and counts["referrals"] == 1
    assert legacy.registered_facility_id == seeded_facilities[FACILITY_A]
    assert ref.from_facility_id == seeded_facilities[FACILITY_A] and ref.to_facility_id is None
    assert db.execute(select(Facility.id).where(Facility.name == "Nowhere")).first() is None
