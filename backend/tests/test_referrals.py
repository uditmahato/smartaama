# backend/tests/test_referrals.py
"""Referral party checks, state machines, listing filters/direction and history."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import FACILITY_A, FACILITY_B, HOSPITAL_X, bearer, create_patient

REFERRALS = "/api/v1/referrals"


def _create(client, headers, patient_id, from_facility=FACILITY_A, to_facility=FACILITY_B, **extra):
    payload = {
        "patient_id": patient_id,
        "from_facility": from_facility,
        "to_facility": to_facility,
        "reason": "High blood pressure at 32 weeks",
    }
    payload.update(extra)
    return client.post(REFERRALS, json=payload, headers=headers)


@pytest.fixture()
def referral_ab(client, patient_a, clinician_a) -> dict:
    resp = _create(client, bearer(clinician_a), patient_a["id"])
    assert resp.status_code == 201, resp.text
    return resp.json()


# ------------------------------------------------------------------ create
def test_create_requires_patient_access(client, patient_a, clinician_b):
    resp = _create(client, bearer(clinician_b), patient_a["id"], from_facility=FACILITY_B, to_facility=HOSPITAL_X)
    assert resp.status_code == 403


def test_create_from_facility_must_match_caller(client, patient_a, clinician_a):
    resp = _create(client, bearer(clinician_a), patient_a["id"], from_facility=FACILITY_B, to_facility=HOSPITAL_X)
    assert resp.status_code == 400
    # case/whitespace-insensitive match is fine
    resp = _create(client, bearer(clinician_a), patient_a["id"], from_facility="  phc a ", to_facility=HOSPITAL_X)
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "submitted"
    assert resp.json()["submitted_at"] is not None


def test_create_admin_may_use_any_from_facility(client, patient_a, admin_user):
    resp = _create(client, bearer(admin_user), patient_a["id"], from_facility=HOSPITAL_X, to_facility=FACILITY_B)
    assert resp.status_code == 201


def test_create_viewer_forbidden(client, patient_a, viewer_a):
    assert _create(client, bearer(viewer_a), patient_a["id"]).status_code == 403


def test_create_unknown_patient_404(client, clinician_a):
    assert _create(client, bearer(clinician_a), str(uuid.uuid4())).status_code == 404


def test_create_writes_history_row(client, referral_ab, clinician_a):
    hist = client.get(f"{REFERRALS}/{referral_ab['id']}/history", headers=bearer(clinician_a))
    assert hist.status_code == 200
    rows = hist.json()
    assert len(rows) == 1
    assert rows[0]["kind"] == "created"
    assert rows[0]["to_status"] == "submitted"
    assert rows[0]["actor_user_id"] == str(clinician_a.id)
    assert rows[0]["actor_name"]


# ------------------------------------------------------------------ get / party
def test_get_referral_party_only(client, referral_ab, clinician_a, clinician_b, hospital_x, admin_user, viewer_a):
    url = f"{REFERRALS}/{referral_ab['id']}"
    assert client.get(url, headers=bearer(clinician_a)).status_code == 200
    assert client.get(url, headers=bearer(clinician_b)).status_code == 200
    assert client.get(url, headers=bearer(viewer_a)).status_code == 200
    assert client.get(url, headers=bearer(admin_user)).status_code == 200
    assert client.get(url, headers=bearer(hospital_x)).status_code == 403
    assert client.get(f"{url}/history", headers=bearer(hospital_x)).status_code == 403


def test_get_referral_404(client, clinician_a):
    assert client.get(f"{REFERRALS}/{uuid.uuid4()}", headers=bearer(clinician_a)).status_code == 404


def test_patch_decision_party_only_and_history(client, referral_ab, clinician_b, hospital_x, clinician_a):
    url = f"{REFERRALS}/{referral_ab['id']}"
    body = {"clinician_decision": "accept", "clinician_note": "Admit for observation"}
    assert client.patch(url, json=body, headers=bearer(hospital_x)).status_code == 403
    resp = client.patch(url, json=body, headers=bearer(clinician_b))
    assert resp.status_code == 200
    assert resp.json()["clinician_decision"] == "accept"
    assert resp.json()["clinician_note"] == "Admit for observation"

    rows = client.get(f"{url}/history", headers=bearer(clinician_a)).json()
    kinds = [r["kind"] for r in rows]
    assert kinds == ["created", "decision"]
    assert rows[-1]["to_status"] == "accept"
    assert rows[-1]["note"] == "Admit for observation"


# ------------------------------------------------------------------ status (referring side)
def test_status_only_referring_facility_or_admin(client, referral_ab, clinician_a, clinician_b, admin_user):
    url = f"{REFERRALS}/{referral_ab['id']}/status"
    # B (receiving) cannot drive the referring-side status
    assert client.post(url, json={"status": "received"}, headers=bearer(clinician_b)).status_code == 403
    # A can
    resp = client.post(url, json={"status": "received", "note": "Ack by phone"}, headers=bearer(clinician_a))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "received"
    assert body["received_at"] is not None
    # note is NOT appended into clinician_note anymore
    assert not body["clinician_note"]
    # admin can
    resp = client.post(url, json={"status": "closed"}, headers=bearer(admin_user))
    assert resp.status_code == 200
    assert resp.json()["closed_at"] is not None


def test_status_invalid_transition_400(client, referral_ab, clinician_a):
    url = f"{REFERRALS}/{referral_ab['id']}/status"
    assert client.post(url, json={"status": "closed"}, headers=bearer(clinician_a)).status_code == 400
    assert client.post(url, json={"status": "draft"}, headers=bearer(clinician_a)).status_code == 400


def test_status_history_rows(client, referral_ab, clinician_a):
    url = f"{REFERRALS}/{referral_ab['id']}"
    client.post(f"{url}/status", json={"status": "received", "note": "Ack"}, headers=bearer(clinician_a))
    rows = client.get(f"{url}/history", headers=bearer(clinician_a)).json()
    assert [r["kind"] for r in rows] == ["created", "status"]
    assert rows[1]["from_status"] == "submitted" and rows[1]["to_status"] == "received"
    assert rows[1]["note"] == "Ack"


# ------------------------------------------------------------------ received-status (receiving side)
def test_received_status_only_receiving_facility_or_admin(client, referral_ab, clinician_a, clinician_b, hospital_x, admin_user):
    url = f"{REFERRALS}/{referral_ab['id']}/received-status"
    assert client.post(url, json={"received_facility_status": "received"}, headers=bearer(clinician_a)).status_code == 403
    assert client.post(url, json={"received_facility_status": "received"}, headers=bearer(hospital_x)).status_code == 403

    resp = client.post(url, json={"received_facility_status": "received", "note": "Admitted"}, headers=bearer(clinician_b))
    assert resp.status_code == 200, resp.text
    assert resp.json()["received_facility_status"] == "received"
    assert not resp.json()["clinician_note"]

    resp = client.post(url, json={"received_facility_status": "closed"}, headers=bearer(admin_user))
    assert resp.status_code == 200
    assert resp.json()["received_facility_status"] == "closed"


def test_received_status_transitions(client, referral_ab, clinician_b):
    url = f"{REFERRALS}/{referral_ab['id']}/received-status"
    h = bearer(clinician_b)
    # None -> closed is invalid
    assert client.post(url, json={"received_facility_status": "closed"}, headers=h).status_code == 400
    # None -> submitted invalid
    assert client.post(url, json={"received_facility_status": "submitted"}, headers=h).status_code == 400
    # None -> received ok
    assert client.post(url, json={"received_facility_status": "received"}, headers=h).status_code == 200
    # received -> received invalid (no self transition)
    assert client.post(url, json={"received_facility_status": "received"}, headers=h).status_code == 400
    # received -> closed ok, then terminal
    assert client.post(url, json={"received_facility_status": "closed"}, headers=h).status_code == 200
    assert client.post(url, json={"received_facility_status": "cancelled"}, headers=h).status_code == 400
    assert client.post(url, json={"received_facility_status": "received"}, headers=h).status_code == 400


def test_received_status_none_to_cancelled(client, referral_ab, clinician_b):
    url = f"{REFERRALS}/{referral_ab['id']}/received-status"
    assert client.post(url, json={"received_facility_status": "cancelled"}, headers=bearer(clinician_b)).status_code == 200
    assert client.post(url, json={"received_facility_status": "received"}, headers=bearer(clinician_b)).status_code == 400


def test_full_history(client, referral_ab, clinician_a, clinician_b):
    rid = referral_ab["id"]
    client.post(f"{REFERRALS}/{rid}/received-status", json={"received_facility_status": "received", "note": "in"}, headers=bearer(clinician_b))
    client.post(f"{REFERRALS}/{rid}/status", json={"status": "received"}, headers=bearer(clinician_a))
    client.patch(f"{REFERRALS}/{rid}", json={"clinician_decision": "accept"}, headers=bearer(clinician_b))
    rows = client.get(f"{REFERRALS}/{rid}/history", headers=bearer(clinician_b)).json()
    assert [r["kind"] for r in rows] == ["created", "received_status", "status", "decision"]
    assert rows[1]["from_status"] is None and rows[1]["to_status"] == "received" and rows[1]["note"] == "in"


# ------------------------------------------------------------------ list
def test_list_direction_and_scoping(client, clinician_a, clinician_b, hospital_x, admin_user, viewer_a):
    pa = create_patient(client, bearer(clinician_a))
    pb = create_patient(client, bearer(clinician_b))
    r_ab = _create(client, bearer(clinician_a), pa["id"], FACILITY_A, FACILITY_B).json()
    r_bx = _create(client, bearer(clinician_b), pb["id"], FACILITY_B, HOSPITAL_X).json()
    r_ax = _create(client, bearer(clinician_a), pa["id"], FACILITY_A, HOSPITAL_X).json()

    def ids(headers, **params):
        resp = client.get(REFERRALS, params=params, headers=headers)
        assert resp.status_code == 200, resp.text
        return {r["id"] for r in resp.json()}

    # B sees only referrals where B is a party
    assert ids(bearer(clinician_b)) == {r_ab["id"], r_bx["id"]}
    assert ids(bearer(clinician_b), direction="incoming") == {r_ab["id"]}
    assert ids(bearer(clinician_b), direction="outgoing") == {r_bx["id"]}
    # A
    assert ids(bearer(clinician_a)) == {r_ab["id"], r_ax["id"]}
    assert ids(bearer(clinician_a), direction="incoming") == set()
    assert ids(bearer(viewer_a), direction="outgoing") == {r_ab["id"], r_ax["id"]}
    # Hospital X
    assert ids(bearer(hospital_x)) == {r_bx["id"], r_ax["id"]}
    assert ids(bearer(hospital_x), direction="incoming") == {r_bx["id"], r_ax["id"]}
    # admin sees all
    assert ids(bearer(admin_user)) == {r_ab["id"], r_bx["id"], r_ax["id"]}
    # explicit facility filters do not widen access for non-admins
    assert ids(bearer(clinician_b), from_facility=FACILITY_A, to_facility=HOSPITAL_X) == set()
    assert ids(bearer(admin_user), from_facility="phc a", to_facility="hospital x") == {r_ax["id"]}
    # exact match: substring must not match
    assert ids(bearer(admin_user), from_facility="PHC") == set()
    # patient filter
    assert ids(bearer(clinician_a), patient_id=pa["id"]) == {r_ab["id"], r_ax["id"]}


def test_list_status_and_received_status_filters(client, clinician_a, clinician_b, patient_a):
    r1 = _create(client, bearer(clinician_a), patient_a["id"]).json()
    r2 = _create(client, bearer(clinician_a), patient_a["id"]).json()
    client.post(f"{REFERRALS}/{r2['id']}/received-status", json={"received_facility_status": "received"}, headers=bearer(clinician_b))
    client.post(f"{REFERRALS}/{r1['id']}/status", json={"status": "received"}, headers=bearer(clinician_a))
    client.post(f"{REFERRALS}/{r1['id']}/status", json={"status": "closed"}, headers=bearer(clinician_a))

    def ids(headers, **params):
        return {r["id"] for r in client.get(REFERRALS, params=params, headers=headers).json()}

    # "Admitted Case" -> direction=incoming&received_status=received (for B)
    assert ids(bearer(clinician_b), direction="incoming", received_status="received") == {r2["id"]}
    # "Closed Case" -> status=closed
    assert ids(bearer(clinician_a), status="closed") == {r1["id"]}
    # the receiver's acknowledgement is mirrored into the referring-side status (submitted -> received)
    assert ids(bearer(clinician_b), status="submitted") == set()
    assert ids(bearer(clinician_b), status="received") == {r2["id"]}


def test_list_pagination_single_query(client, clinician_a, clinician_b, patient_a):
    for _ in range(5):
        _create(client, bearer(clinician_a), patient_a["id"], FACILITY_A, FACILITY_B)
    page1 = client.get(REFERRALS, params={"limit": 2, "offset": 0}, headers=bearer(clinician_b)).json()
    page2 = client.get(REFERRALS, params={"limit": 2, "offset": 2}, headers=bearer(clinician_b)).json()
    page3 = client.get(REFERRALS, params={"limit": 2, "offset": 4}, headers=bearer(clinician_b)).json()
    assert len(page1) == 2 and len(page2) == 2 and len(page3) == 1
    seen = {r["id"] for r in page1 + page2 + page3}
    assert len(seen) == 5


def test_list_no_facility_non_admin_sees_nothing(client, referral_ab, make_user):
    orphan = make_user("orphan")
    assert client.get(REFERRALS, headers=bearer(orphan)).json() == []


def test_list_invalid_direction_422(client, clinician_a):
    assert client.get(REFERRALS, params={"direction": "sideways"}, headers=bearer(clinician_a)).status_code == 422
