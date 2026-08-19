# backend/tests/test_patients_access.py
"""Facility-level patient authorization: create/get/list/patch scoping."""

from __future__ import annotations

import uuid

from tests.conftest import FACILITY_A, FACILITY_B, HOSPITAL_X, bearer, create_patient

PATIENTS = "/api/v1/patients"


def test_create_sets_registered_facility_from_actor(client, clinician_a):
    p = create_patient(client, bearer(clinician_a), registered_facility_name="Somewhere Else")
    # non-admin: payload value ignored, actor's facility wins
    assert p["registered_facility_name"] == FACILITY_A
    assert p["registered_facility_type"] == "phc"
    assert p["created_by_user_id"] == str(clinician_a.id)
    assert p["patient_id"].startswith("PAT-")
    assert p["facility_mrn"]


def test_admin_without_facility_must_supply_facility(client, admin_user):
    resp = client.post(PATIENTS, json={"first_name": "A", "last_name": "B"}, headers=bearer(admin_user))
    assert resp.status_code == 400
    p = create_patient(client, bearer(admin_user), registered_facility_name="PHC B", registered_facility_type="phc")
    assert p["registered_facility_name"] == "PHC B"


def test_viewer_cannot_create_patient(client, viewer_a):
    resp = client.post(PATIENTS, json={"first_name": "A", "last_name": "B"}, headers=bearer(viewer_a))
    assert resp.status_code == 403


def test_user_without_facility_cannot_create(client, make_user):
    orphan = make_user("orphan")  # clinician, no facility
    resp = client.post(PATIENTS, json={"first_name": "A", "last_name": "B"}, headers=bearer(orphan))
    assert resp.status_code == 400


def test_get_patient_scoped_by_facility(client, patient_a, clinician_a, clinician_b, viewer_a, admin_user):
    url = f"{PATIENTS}/{patient_a['id']}"
    assert client.get(url, headers=bearer(clinician_a)).status_code == 200
    assert client.get(url, headers=bearer(viewer_a)).status_code == 200  # same facility, read-only role
    assert client.get(url, headers=bearer(clinician_b)).status_code == 403
    assert client.get(url, headers=bearer(admin_user)).status_code == 200


def test_get_patient_404_unknown(client, clinician_a):
    assert client.get(f"{PATIENTS}/{uuid.uuid4()}", headers=bearer(clinician_a)).status_code == 404


def test_facility_match_is_case_insensitive_exact(client, patient_a, make_user):
    same_lower = make_user("lower-a", facility_name=" phc a ")
    assert client.get(f"{PATIENTS}/{patient_a['id']}", headers=bearer(same_lower)).status_code == 200
    substring = make_user("phc-ab", facility_name="PHC AB")
    assert client.get(f"{PATIENTS}/{patient_a['id']}", headers=bearer(substring)).status_code == 403


def test_referral_grants_receiving_facility_access(client, patient_a, clinician_a, clinician_b, hospital_x):
    url = f"{PATIENTS}/{patient_a['id']}"
    assert client.get(url, headers=bearer(clinician_b)).status_code == 403
    assert client.get(url, headers=bearer(hospital_x)).status_code == 403

    resp = client.post(
        "/api/v1/referrals",
        json={
            "patient_id": patient_a["id"],
            "from_facility": FACILITY_A,
            "to_facility": FACILITY_B,
            "reason": "Needs specialist review",
        },
        headers=bearer(clinician_a),
    )
    assert resp.status_code == 201, resp.text

    assert client.get(url, headers=bearer(clinician_b)).status_code == 200
    assert client.get(url, headers=bearer(hospital_x)).status_code == 403


def test_list_patients_scoped(client, clinician_a, clinician_b, admin_user, viewer_a):
    pa = create_patient(client, bearer(clinician_a), first_name="Alpha")
    pb = create_patient(client, bearer(clinician_b), first_name="Beta")

    ids_a = {p["id"] for p in client.get(PATIENTS, headers=bearer(clinician_a)).json()}
    assert ids_a == {pa["id"]}
    ids_viewer = {p["id"] for p in client.get(PATIENTS, headers=bearer(viewer_a)).json()}
    assert ids_viewer == {pa["id"]}
    ids_b = {p["id"] for p in client.get(PATIENTS, headers=bearer(clinician_b)).json()}
    assert ids_b == {pb["id"]}
    ids_admin = {p["id"] for p in client.get(PATIENTS, headers=bearer(admin_user)).json()}
    assert ids_admin == {pa["id"], pb["id"]}

    # search term does not widen access
    found = client.get(PATIENTS, params={"q": "Beta"}, headers=bearer(clinician_a)).json()
    assert found == []
    found = client.get(PATIENTS, params={"q": "Alpha"}, headers=bearer(clinician_a)).json()
    assert [p["id"] for p in found] == [pa["id"]]


def test_list_patients_no_facility_sees_nothing(client, patient_a, make_user):
    orphan = make_user("orphan")
    assert client.get(PATIENTS, headers=bearer(orphan)).json() == []


def test_patch_patient_requires_access_and_role(client, patient_a, clinician_a, clinician_b, viewer_a, admin_user):
    url = f"{PATIENTS}/{patient_a['id']}"
    assert client.patch(url, json={"phone_number": "111"}, headers=bearer(clinician_b)).status_code == 403
    assert client.patch(url, json={"phone_number": "111"}, headers=bearer(viewer_a)).status_code == 403

    resp = client.patch(url, json={"phone_number": "222", "registered_facility_name": "PHC B"}, headers=bearer(clinician_a))
    assert resp.status_code == 200
    body = resp.json()
    assert body["phone_number"] == "222"
    assert body["registered_facility_name"] == FACILITY_A  # non-admin cannot re-home a patient

    resp = client.patch(url, json={"registered_facility_name": "PHC B"}, headers=bearer(admin_user))
    assert resp.status_code == 200
    assert resp.json()["registered_facility_name"] == "PHC B"
    # facility A lost access, facility B gained it
    assert client.get(url, headers=bearer(clinician_a)).status_code == 403
    assert client.get(url, headers=bearer(clinician_b)).status_code == 200


def test_patient_ids_are_unique_and_sequential(client, clinician_a):
    p1 = create_patient(client, bearer(clinician_a))
    p2 = create_patient(client, bearer(clinician_a))
    assert p1["patient_id"] != p2["patient_id"]
    assert int(p2["patient_id"].rsplit("-", 1)[1]) == int(p1["patient_id"].rsplit("-", 1)[1]) + 1
    assert p1["facility_mrn"] != p2["facility_mrn"]


def test_patient_id_collision_is_retried(client, clinician_a, monkeypatch):
    """If the generated patient_id collides (race), the service retries instead of returning 500."""
    from app.services import patient_service as ps

    p1 = create_patient(client, bearer(clinician_a))
    original = ps.PatientService._generate_patient_id
    calls = {"n": 0}

    def colliding(db, bump=0):
        calls["n"] += 1
        if calls["n"] == 1:
            return p1["patient_id"]  # force a unique-constraint collision on first attempt
        return original(db, bump=bump)

    monkeypatch.setattr(ps.PatientService, "_generate_patient_id", staticmethod(colliding))
    p2 = create_patient(client, bearer(clinician_a))
    assert p2["patient_id"] != p1["patient_id"]
    assert calls["n"] >= 2
