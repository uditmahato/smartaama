# backend/tests/test_review_fixes.py
"""
Tests for the fixes made after the independent final review:
- admin-vs-admin lockout: approve/reject/role changes on admin-role users need a super admin
- role assignment endpoint (hospital / viewer / admin are reachable)
- registration role follows facility type
- cached advisory analyses from other engines are never served (service + init_db purge)
- receiving-facility status mirrors into the referring-side status when valid
- clinical events cannot be tagged with another patient's referral
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.models.ai_patient_analysis import AIPatientAnalysis
from app.models.audit_log import AuditLog
from app.models.user import UserRole
from app.services.advisory_rules import ENGINE_VERSION
from tests.conftest import FACILITY_A, FACILITY_B, HOSPITAL_X, bearer, create_patient, REGISTER_PASSWORD

ADMIN = "/api/v1/admin/users"
REFERRALS = "/api/v1/referrals"


# --------------------------------------------------------------------------- admin guards
def test_plain_admin_cannot_reject_or_approve_admin(client, admin_user, admin_user_plain):
    h = bearer(admin_user_plain)
    assert client.patch(f"{ADMIN}/{admin_user.id}/reject", headers=h).status_code == 403
    assert client.patch(f"{ADMIN}/{admin_user.id}/approve", headers=h).status_code == 403
    # super admin still logs in / is untouched
    assert client.get("/api/v1/auth/me", headers=bearer(admin_user)).status_code == 200


def test_super_admin_can_reject_admin(client, admin_user, admin_user_plain):
    assert client.patch(f"{ADMIN}/{admin_user_plain.id}/reject", headers=bearer(admin_user)).status_code == 200


def test_role_endpoint_rules(client, db, admin_user, admin_user_plain, clinician_a):
    # non-admin -> 403
    assert client.patch(f"{ADMIN}/{admin_user_plain.id}/role", json={"role": "viewer"}, headers=bearer(clinician_a)).status_code == 403
    # plain admin may assign viewer/hospital/clinician
    r = client.patch(f"{ADMIN}/{clinician_a.id}/role", json={"role": "viewer"}, headers=bearer(admin_user_plain))
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "viewer"
    # ... but not admin
    r = client.patch(f"{ADMIN}/{clinician_a.id}/role", json={"role": "admin"}, headers=bearer(admin_user_plain))
    assert r.status_code == 403
    # ... nor its own role
    r = client.patch(f"{ADMIN}/{admin_user_plain.id}/role", json={"role": "viewer"}, headers=bearer(admin_user_plain))
    assert r.status_code == 400
    # super admin may grant admin, and it is audited
    r = client.patch(f"{ADMIN}/{clinician_a.id}/role", json={"role": "admin"}, headers=bearer(admin_user))
    assert r.status_code == 200 and r.json()["role"] == "admin"
    rows = db.execute(select(AuditLog).where(AuditLog.action == "USER_ROLE_CHANGED")).scalars().all()
    assert len(rows) >= 2
    assert rows[-1].details["new_role"] == "admin"
    # invalid role value -> 422
    assert client.patch(f"{ADMIN}/{clinician_a.id}/role", json={"role": "root"}, headers=bearer(admin_user)).status_code == 422


def test_viewer_after_role_change_cannot_write(client, admin_user, clinician_a, patient_a):
    client.patch(f"{ADMIN}/{clinician_a.id}/role", json={"role": "viewer"}, headers=bearer(admin_user))
    r = client.post(
        f"/api/v1/medical-data/patients/{patient_a['id']}/sections/vitals",
        json={"section_key": "vitals", "data_points": {"pulse_rate": 80}},
        headers=bearer(clinician_a),
    )
    assert r.status_code == 403


# --------------------------------------------------------------------------- registration role
def test_register_hospital_facility_gets_hospital_role(client, seeded_facilities, db):
    form = {
        "email": "hosp.doc@example.test",
        "password": REGISTER_PASSWORD,
        "full_name": "Hospital Doctor",
        "phone_number": "9800000000",
        "nmc_number": "NMC-9",
        "working_hospital": HOSPITAL_X,
        "facility_type": "hospital",
        "facility_id": str(seeded_facilities[HOSPITAL_X]),
    }
    r = client.post("/api/v1/auth/register", data=form)
    assert r.status_code == 201, r.text
    assert r.json()["user"]["role"] == "hospital"

    form.update({"email": "phc.doc@example.test", "facility_type": "phc", "facility_id": str(seeded_facilities[FACILITY_A])})
    r = client.post("/api/v1/auth/register", data=form)
    assert r.status_code == 201, r.text
    assert r.json()["user"]["role"] == "clinician"


# --------------------------------------------------------------------------- foreign-engine analyses
def _insert_legacy_analysis(db, patient_id, model_used="gpt-4o-mini"):
    row = AIPatientAnalysis(
        patient_id=patient_id,
        summary="Legacy LLM text that must never be served by the rule engine.",
        model_used=model_used,
        last_analyzed_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    return row


def test_legacy_engine_analysis_is_not_served(client, db, clinician_a, patient_a):
    import uuid as _uuid

    _insert_legacy_analysis(db, _uuid.UUID(patient_a["id"]))
    r = client.get(f"/api/v1/ai-analysis/patients/{patient_a['id']}/analysis?auto_generate=true", headers=bearer(clinician_a))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["model_used"] == ENGINE_VERSION
    assert "Legacy LLM text" not in body["summary"]["summary"]


def test_legacy_engine_analysis_404_for_viewer(client, db, viewer_a, clinician_a, patient_a):
    import uuid as _uuid

    _insert_legacy_analysis(db, _uuid.UUID(patient_a["id"]))
    # viewer may not generate: the foreign row is discarded and nothing is served
    r = client.get(f"/api/v1/ai-analysis/patients/{patient_a['id']}/analysis?auto_generate=true", headers=bearer(viewer_a))
    assert r.status_code == 404


def test_init_db_purges_foreign_engine_rows(db, clinician_a, patient_a):
    import uuid as _uuid

    from app.db.init_db import _purge_foreign_engine_analyses

    pid = _uuid.UUID(patient_a["id"])
    _insert_legacy_analysis(db, pid)
    _purge_foreign_engine_analyses(db.get_bind())
    db.expire_all()
    assert db.execute(select(AIPatientAnalysis).where(AIPatientAnalysis.patient_id == pid)).scalar_one_or_none() is None

    # a current-engine row survives
    _insert_legacy_analysis(db, pid, model_used=ENGINE_VERSION)
    _purge_foreign_engine_analyses(db.get_bind())
    db.expire_all()
    assert db.execute(select(AIPatientAnalysis).where(AIPatientAnalysis.patient_id == pid)).scalar_one_or_none() is not None


# --------------------------------------------------------------------------- status mirroring
def _referral(client, headers, patient_id, to_facility=HOSPITAL_X):
    r = client.post(
        REFERRALS,
        json={"patient_id": patient_id, "from_facility": FACILITY_A, "to_facility": to_facility, "reason": "Severe hypertension", "status": "submitted"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_received_status_mirrors_into_status(client, clinician_a, hospital_x, patient_a):
    ref = _referral(client, bearer(clinician_a), patient_a["id"])
    assert ref["status"] == "submitted"

    r = client.post(f"{REFERRALS}/{ref['id']}/received-status", json={"received_facility_status": "received", "note": "Admitted"}, headers=bearer(hospital_x))
    assert r.status_code == 200, r.text
    assert r.json()["received_facility_status"] == "received"
    assert r.json()["status"] == "received"  # mirrored

    r = client.post(f"{REFERRALS}/{ref['id']}/received-status", json={"received_facility_status": "closed"}, headers=bearer(hospital_x))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "closed"
    assert r.json()["closed_at"] is not None

    # dashboard "Closed Case" filter now finds it for the sender
    r = client.get(f"{REFERRALS}?status=closed", headers=bearer(clinician_a))
    assert any(x["id"] == ref["id"] for x in r.json())

    hist = client.get(f"{REFERRALS}/{ref['id']}/history", headers=bearer(clinician_a)).json()
    kinds = [(h["kind"], h["to_status"]) for h in hist]
    assert ("received_status", "received") in kinds and ("status", "received") in kinds
    assert ("received_status", "closed") in kinds and ("status", "closed") in kinds


def test_received_cancelled_mirrors_only_when_valid(client, clinician_a, hospital_x, patient_a):
    ref = _referral(client, bearer(clinician_a), patient_a["id"])
    # submitted -> cancelled is a valid referring transition: mirrored
    r = client.post(f"{REFERRALS}/{ref['id']}/received-status", json={"received_facility_status": "cancelled"}, headers=bearer(hospital_x))
    assert r.status_code == 200 and r.json()["status"] == "cancelled"

    ref2 = _referral(client, bearer(clinician_a), patient_a["id"])
    client.post(f"{REFERRALS}/{ref2['id']}/received-status", json={"received_facility_status": "received"}, headers=bearer(hospital_x))
    # received -> cancelled is NOT a valid referring transition: received-side updates, sender status stays 'received'
    r = client.post(f"{REFERRALS}/{ref2['id']}/received-status", json={"received_facility_status": "cancelled"}, headers=bearer(hospital_x))
    assert r.status_code == 200
    assert r.json()["received_facility_status"] == "cancelled" and r.json()["status"] == "received"


# --------------------------------------------------------------------------- events referral link
def test_event_referral_id_must_belong_to_patient(client, clinician_a, patient_a):
    other = create_patient(client, bearer(clinician_a), first_name="Gita")
    ref_other = _referral(client, bearer(clinician_a), other["id"])
    payload = {
        "patient_id": patient_a["id"],
        "section": "vitals",
        "factor": "pulse_rate",
        "value": {"value": 80, "unit": "bpm", "type": "number"},
        "referral_id": ref_other["id"],
    }
    r = client.post("/api/v1/events", json=payload, headers=bearer(clinician_a))
    assert r.status_code == 400, r.text
    # same patient's referral is fine
    ref_own = _referral(client, bearer(clinician_a), patient_a["id"])
    payload["referral_id"] = ref_own["id"]
    r = client.post("/api/v1/events", json=payload, headers=bearer(clinician_a))
    assert r.status_code == 201, r.text


# --------------------------------------------------------------------------- phase-2 review fixes
def test_huge_x_forwarded_for_never_breaks_writes(client, admin_user, clinician_a, patient_a):
    """A hostile/huge X-Forwarded-For must not turn into a 500 on audit/rate-limit inserts."""
    xff = {"X-Forwarded-For": "x" * 300}
    # rate-limited auth endpoint (limiter disabled in tests, but the audit row on login is written)
    from tests.conftest import TEST_PASSWORD

    r = client.post("/api/v1/auth/login", data={"username": clinician_a.username, "password": TEST_PASSWORD}, headers=xff)
    assert r.status_code == 200, r.text
    # authenticated write that stores ip_address in audit_logs
    r = client.post(
        "/api/v1/patients",
        json={"first_name": "Xff", "last_name": "Test", "age_in_years": 30},
        headers={**bearer(clinician_a), **xff},
    )
    assert r.status_code == 201, r.text
    # admin action with a long but valid-looking first hop
    r = client.patch(f"{ADMIN}/{clinician_a.id}/role", json={"role": "viewer"}, headers={**bearer(admin_user), "X-Forwarded-For": "203.0.113.9, " + "10.0.0.1, " * 40})
    assert r.status_code == 200, r.text


def test_normalize_client_ip_bounds_and_validates():
    from app.core.rate_limit import MAX_IP_LEN, normalize_client_ip

    assert normalize_client_ip("203.0.113.9, 10.0.0.1") == "203.0.113.9"
    assert normalize_client_ip("not-an-ip", "127.0.0.1") == "127.0.0.1"
    assert normalize_client_ip("x" * 500, "::1") == "::1"
    assert normalize_client_ip(None, None) is None
    assert normalize_client_ip("2001:0db8:0000:0000:0000:0000:0000:0001") == "2001:db8::1"
    long_peer = "h" * 200
    assert len(normalize_client_ip(None, long_peer) or "") <= MAX_IP_LEN


def test_legacy_user_without_facility_id_is_self_healed_on_write(client, db, make_user, patient_a):
    """NULL facility_id + known facility name: writing links the FK so id-first reads see the rows."""
    from sqlalchemy import select

    from app.models.user import User

    u = make_user("legacy-clin", facility_name=FACILITY_A)
    u.facility_id = None
    db.add(u)
    db.commit()
    r = client.post("/api/v1/patients", json={"first_name": "Legacy", "last_name": "Write", "age_in_years": 22}, headers=bearer(u))
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    assert r.json()["registered_facility_id"] is not None
    # user row was healed
    db.expire_all()
    fresh = db.execute(select(User).where(User.id == u.id)).scalar_one()
    assert fresh.facility_id is not None and fresh.facility_name == FACILITY_A
    # and the user can read what it wrote (id-first rule)
    assert client.get(f"/api/v1/patients/{pid}", headers=bearer(fresh)).status_code == 200
    assert any(p["id"] == pid for p in client.get("/api/v1/patients?q=Legacy", headers=bearer(fresh)).json())


def test_referral_initial_status_restricted(client, clinician_a, patient_a):
    for bad in ("received", "closed", "cancelled"):
        r = client.post(
            REFERRALS,
            json={"patient_id": patient_a["id"], "from_facility": FACILITY_A, "to_facility": HOSPITAL_X, "reason": "Initial status test", "status": bad},
            headers=bearer(clinician_a),
        )
        assert r.status_code == 422, (bad, r.text)
    for ok in ("draft", "submitted"):
        r = client.post(
            REFERRALS,
            json={"patient_id": patient_a["id"], "from_facility": FACILITY_A, "to_facility": HOSPITAL_X, "reason": "Initial status test", "status": ok},
            headers=bearer(clinician_a),
        )
        assert r.status_code == 201, (ok, r.text)


def test_init_db_refuses_to_stamp_post_baseline_schema_without_alembic_version(db):
    """A create_all-built DB (has facilities but no alembic_version) must not be stamped at 0001."""
    import pytest

    from app.db.init_db import _is_legacy_database

    with pytest.raises(RuntimeError):
        _is_legacy_database(db.get_bind())
