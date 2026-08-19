# backend/tests/test_events_medical_data.py
"""Clinical events + medical-data routes: role + facility checks, advisory invalidation."""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.ai_patient_analysis import AIPatientAnalysis
from app.models.clinical_event import ClinicalEvent
from tests.conftest import bearer

EVENTS = "/api/v1/events"


def _event_payload(patient_id, factor="blood_pressure_systolic", value=120):
    return {
        "patient_id": patient_id,
        "section": "vitals",
        "factor": factor,
        "value": {"type": "number", "value": value, "unit": "mmHg"},
        "note": "test",
    }


def _seed_analysis(db, patient_id: str) -> None:
    db.add(AIPatientAnalysis(patient_id=uuid.UUID(patient_id), summary="stale", data_version=1))
    db.commit()


def _analysis_exists(db, patient_id: str) -> bool:
    return db.execute(select(AIPatientAnalysis).where(AIPatientAnalysis.patient_id == uuid.UUID(patient_id))).first() is not None


# ------------------------------------------------------------------ /events
def test_viewer_cannot_post_event_clinician_can(client, patient_a, viewer_a, clinician_a):
    resp = client.post(EVENTS, json=_event_payload(patient_a["id"]), headers=bearer(viewer_a))
    assert resp.status_code == 403
    resp = client.post(EVENTS, json=_event_payload(patient_a["id"]), headers=bearer(clinician_a))
    assert resp.status_code == 201, resp.text
    assert resp.json()["section"] == "vitals"


def test_event_write_requires_patient_access(client, patient_a, clinician_b, hospital_x, admin_user):
    resp = client.post(EVENTS, json=_event_payload(patient_a["id"]), headers=bearer(clinician_b))
    assert resp.status_code == 403
    resp = client.post(EVENTS, json=_event_payload(patient_a["id"]), headers=bearer(hospital_x))
    assert resp.status_code == 403
    resp = client.post(EVENTS, json=_event_payload(patient_a["id"]), headers=bearer(admin_user))
    assert resp.status_code == 201


def test_event_write_unknown_patient_404(client, clinician_a):
    resp = client.post(EVENTS, json=_event_payload(str(uuid.uuid4())), headers=bearer(clinician_a))
    assert resp.status_code == 404


def test_event_read_requires_patient_access(client, patient_a, clinician_a, viewer_a, clinician_b):
    client.post(EVENTS, json=_event_payload(patient_a["id"]), headers=bearer(clinician_a))
    ok = client.get(EVENTS, params={"patient_id": patient_a["id"]}, headers=bearer(viewer_a))
    assert ok.status_code == 200 and len(ok.json()) == 1
    denied = client.get(EVENTS, params={"patient_id": patient_a["id"]}, headers=bearer(clinician_b))
    assert denied.status_code == 403


def test_event_batch_role_and_invalidation(client, patient_a, viewer_a, clinician_a, db):
    payload = {
        "patient_id": patient_a["id"],
        "section": "vitals",
        "events": [
            {"factor": "blood_pressure_systolic", "value": {"type": "number", "value": 130}},
            {"factor": "blood_pressure_diastolic", "value": {"type": "number", "value": 85}},
        ],
    }
    assert client.post(f"{EVENTS}/batch", json=payload, headers=bearer(viewer_a)).status_code == 403

    _seed_analysis(db, patient_a["id"])
    resp = client.post(f"{EVENTS}/batch", json=payload, headers=bearer(clinician_a))
    assert resp.status_code == 201, resp.text
    assert len(resp.json()) == 2
    assert not _analysis_exists(db, patient_a["id"])  # advisory analysis invalidated


def test_single_event_invalidates_analysis(client, patient_a, clinician_a, db):
    _seed_analysis(db, patient_a["id"])
    assert client.post(EVENTS, json=_event_payload(patient_a["id"]), headers=bearer(clinician_a)).status_code == 201
    assert not _analysis_exists(db, patient_a["id"])


# ------------------------------------------------------------------ /medical-data
MD = "/api/v1/medical-data/patients/{pid}"


def test_medical_data_section_write_roles(client, patient_a, viewer_a, clinician_a, hospital_x, clinician_b, db):
    body = {"section_key": "vitals", "data_points": {"blood_pressure_systolic": 118, "blood_pressure_diastolic": 76}}
    url = MD.format(pid=patient_a["id"]) + "/sections/vitals"

    assert client.post(url, json=body, headers=bearer(viewer_a)).status_code == 403
    assert client.post(url, json=body, headers=bearer(clinician_b)).status_code == 403  # other facility
    assert client.post(url, json=body, headers=bearer(hospital_x)).status_code == 403

    _seed_analysis(db, patient_a["id"])
    resp = client.post(url, json=body, headers=bearer(clinician_a))
    assert resp.status_code == 201, resp.text
    out = resp.json()
    assert out["event_count"] == 2 and out["section_key"] == "vitals"
    assert not _analysis_exists(db, patient_a["id"])

    n = db.execute(select(ClinicalEvent).where(ClinicalEvent.patient_id == uuid.UUID(patient_a["id"]))).scalars().all()
    assert len(n) == 2


def test_medical_data_section_key_mismatch_400(client, patient_a, clinician_a):
    url = MD.format(pid=patient_a["id"]) + "/sections/vitals"
    body = {"section_key": "menstrual_history", "data_points": {}}
    assert client.post(url, json=body, headers=bearer(clinician_a)).status_code == 400


def test_medical_data_invalid_section_400(client, patient_a, clinician_a):
    url = MD.format(pid=patient_a["id"]) + "/sections/not_a_section"
    assert client.get(url + "/latest", headers=bearer(clinician_a)).status_code == 400


def test_medical_data_reads(client, patient_a, clinician_a, viewer_a, clinician_b):
    url = MD.format(pid=patient_a["id"]) + "/sections/vitals"
    body = {"section_key": "vitals", "data_points": {"blood_pressure_systolic": 118}}
    assert client.post(url, json=body, headers=bearer(clinician_a)).status_code == 201
    body = {"section_key": "vitals", "data_points": {"blood_pressure_systolic": 140}, "event_time": "2030-01-01T10:00:00Z"}
    assert client.post(url, json=body, headers=bearer(clinician_a)).status_code == 201

    latest = client.get(url + "/latest", headers=bearer(viewer_a))
    assert latest.status_code == 200
    assert latest.json()["data_points"]["blood_pressure_systolic"] == 140

    hist = client.get(url + "/history", headers=bearer(viewer_a))
    assert hist.status_code == 200
    assert hist.json()["total_entries"] == 2
    assert len(hist.json()["entries"]) == 2

    assert client.get(url + "/latest", headers=bearer(clinician_b)).status_code == 403
    assert client.get(url + "/history", headers=bearer(clinician_b)).status_code == 403


def test_medical_data_latest_empty(client, patient_a, clinician_a):
    url = MD.format(pid=patient_a["id"]) + "/sections/vitals/latest"
    resp = client.get(url, headers=bearer(clinician_a))
    assert resp.status_code == 200
    assert resp.json()["data_points"] == {}
    assert resp.json()["message"]


def test_bulk_entry_roles_and_invalidation(client, patient_a, viewer_a, clinician_a, clinician_b, db):
    url = MD.format(pid=patient_a["id"]) + "/bulk-entry"
    body = {
        "patient_id": patient_a["id"],
        "sections": [
            {"section_key": "vitals", "data_points": {"blood_pressure_systolic": 118}},
        ],
        "visit_note": "ANC visit",
    }
    assert client.post(url, json=body, headers=bearer(viewer_a)).status_code == 403
    assert client.post(url, json=body, headers=bearer(clinician_b)).status_code == 403

    _seed_analysis(db, patient_a["id"])
    resp = client.post(url, json=body, headers=bearer(clinician_a))
    assert resp.status_code == 201, resp.text
    assert resp.json()["total_events"] == 1
    assert not _analysis_exists(db, patient_a["id"])

    # patient id mismatch
    body["patient_id"] = str(uuid.uuid4())
    assert client.post(url, json=body, headers=bearer(clinician_a)).status_code == 400
