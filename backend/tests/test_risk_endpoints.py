# backend/tests/test_risk_endpoints.py
"""
HTTP-level tests for the advisory endpoints (authorization + response shape):
  GET  /api/v1/ai-analysis/patients/{id}/analysis
  POST /api/v1/ai-analysis/generate
  GET  /api/v1/ai-analysis/patients/{id}/status
  DELETE /api/v1/ai-analysis/patients/{id}
  POST /api/v1/ai/risk

Uses the shared fixtures from tests/conftest.py (client, db, users, auth).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.models.clinical_event import ClinicalEvent
from app.models.patient import Patient
from app.services.advisory_rules import ENGINE_VERSION
from tests.conftest import FACILITY_A

API = "/api/v1"
T0 = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)


def _patient(db, facility: str = FACILITY_A) -> Patient:
    p = Patient(
        patient_id=f"PAT-{uuid.uuid4().hex[:8].upper()}",
        first_name="Ana",
        last_name="Test",
        age_in_years=29,
        sex="female",
        registered_facility_name=facility,
        registered_facility_type="phc",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _event(db, patient: Patient, section: str, factor: str, value, unit=None) -> None:
    db.add(
        ClinicalEvent(
            patient_id=patient.id,
            event_time=T0,
            section=section,
            factor=factor,
            value={"value": value, "unit": unit, "type": "integer"},
        )
    )
    db.commit()


# --------------------------------------------------------------------------- GET analysis

def test_viewer_cannot_trigger_generation_gets_404(client, db, viewer_a, auth):
    p = _patient(db)
    r = client.get(f"{API}/ai-analysis/patients/{p.id}/analysis?auto_generate=true", headers=auth(viewer_a))
    assert r.status_code == 404
    assert "clinician" in r.json()["detail"].lower()


def test_clinician_generates_then_viewer_can_read(client, db, clinician_a, viewer_a, auth):
    p = _patient(db)
    _event(db, p, "vitals", "blood_pressure_systolic", 165, "mmHg")
    _event(db, p, "urine_examination", "dipstick_protein", "++")

    r = client.get(f"{API}/ai-analysis/patients/{p.id}/analysis?auto_generate=true", headers=auth(clinician_a))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["model_used"] == ENGINE_VERSION
    assert body["summary"]["risk_level"] == "critical"
    assert body["referral_recommendation"]["urgency"] == "critical"
    assert body["referral_recommendation"]["referral_needed"] is True
    assert "disclaimer" in body and "advisory" in body["disclaimer"].lower()
    assert "rag_used" not in body

    # viewer of the same facility may read the stored analysis
    r2 = client.get(f"{API}/ai-analysis/patients/{p.id}/analysis", headers=auth(viewer_a))
    assert r2.status_code == 200
    assert r2.json()["data_version"] == 1

    # viewer may NOT force regeneration
    r3 = client.get(f"{API}/ai-analysis/patients/{p.id}/analysis?force_regenerate=true", headers=auth(viewer_a))
    assert r3.status_code == 403

    # clinician may
    r4 = client.get(f"{API}/ai-analysis/patients/{p.id}/analysis?force_regenerate=true", headers=auth(clinician_a))
    assert r4.status_code == 200 and r4.json()["data_version"] == 2


def test_other_facility_gets_403_and_missing_patient_404(client, db, clinician_b, auth):
    p = _patient(db)  # registered at PHC A
    r = client.get(f"{API}/ai-analysis/patients/{p.id}/analysis", headers=auth(clinician_b))
    assert r.status_code == 403
    r = client.get(f"{API}/ai-analysis/patients/{uuid.uuid4()}/analysis", headers=auth(clinician_b))
    assert r.status_code == 404


def test_unauthenticated_is_401(client, db):
    p = _patient(db)
    assert client.get(f"{API}/ai-analysis/patients/{p.id}/analysis").status_code == 401
    assert client.post(f"{API}/ai/risk", json={"patient_id": str(p.id)}).status_code == 401


# --------------------------------------------------------------------------- generate / status / delete

def test_generate_status_delete_flow(client, db, clinician_a, viewer_a, auth):
    p = _patient(db)
    _event(db, p, "blood_investigations", "hemoglobin", 6.5, "g/dL")

    # status before: nothing stored
    s0 = client.get(f"{API}/ai-analysis/patients/{p.id}/status", headers=auth(viewer_a))
    assert s0.status_code == 200
    assert s0.json()["has_analysis"] is False and s0.json()["needs_update"] is True

    # viewer cannot generate
    assert client.post(f"{API}/ai-analysis/generate", json={"patient_id": str(p.id)}, headers=auth(viewer_a)).status_code == 403

    g = client.post(f"{API}/ai-analysis/generate", json={"patient_id": str(p.id)}, headers=auth(clinician_a))
    assert g.status_code == 200, g.text
    assert g.json()["summary"]["risk_level"] == "high"

    s1 = client.get(f"{API}/ai-analysis/patients/{p.id}/status", headers=auth(viewer_a))
    assert s1.json()["has_analysis"] is True
    assert s1.json()["needs_update"] is False
    assert s1.json()["model_used"] == ENGINE_VERSION

    # viewer cannot delete; clinician can
    assert client.delete(f"{API}/ai-analysis/patients/{p.id}", headers=auth(viewer_a)).status_code == 403
    assert client.delete(f"{API}/ai-analysis/patients/{p.id}", headers=auth(clinician_a)).status_code == 200
    assert client.delete(f"{API}/ai-analysis/patients/{p.id}", headers=auth(clinician_a)).status_code == 404


# --------------------------------------------------------------------------- /ai/risk

def test_ai_risk_requires_clinician_and_patient_access(client, db, clinician_a, clinician_b, viewer_a, auth):
    p = _patient(db)
    _event(db, p, "vitals", "pulse_rate", 122, "bpm")
    _event(db, p, "per_abdominal_examination", "fetal_heart_rate", 140, "bpm")

    assert client.post(f"{API}/ai/risk", json={"patient_id": str(p.id)}, headers=auth(viewer_a)).status_code == 403
    assert client.post(f"{API}/ai/risk", json={"patient_id": str(p.id)}, headers=auth(clinician_b)).status_code == 403

    r = client.post(f"{API}/ai/risk", json={"patient_id": str(p.id)}, headers=auth(clinician_a))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["model_version"] == ENGINE_VERSION
    assert "rag_used" not in body
    rec = body["recommendation"]
    assert rec["overall_risk_level"] == "high"
    assert rec["referral_urgency"] == "high"
    assert rec["citations"] == []
    codes = {e["code"] for e in rec["evidence"]}
    assert "maternal_tachycardia_severe" in codes
    assert not any("fetal" in c for c in codes)  # normal fetal HR must not appear as evidence
    assert rec["engine"] == ENGINE_VERSION
