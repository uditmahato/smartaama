# backend/tests/test_risk_engine_service.py
"""
Service-level tests for the advisory engine against an in-memory SQLite DB:
- RiskEngine.assess (POST /ai/risk shape)
- AIPatientService.get_or_generate_analysis (/ai-analysis shape) + persistence
- mark_ai_analysis_for_update invalidation and needs_update detection
- model portability (JSON/Uuid columns create on SQLite)

Uses plain SQLAlchemy sessions; no FastAPI TestClient or conftest fixtures.
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-chars-long")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("ENV", "dev")

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.db.base  # noqa: E402,F401  (registers all models on Base.metadata)
from app.models.ai_patient_analysis import AIPatientAnalysis  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.clinical_event import ClinicalEvent  # noqa: E402
from app.models.patient import Patient  # noqa: E402
from app.schemas.ai import AiRiskRequest  # noqa: E402
from app.services.advisory_rules import DISCLAIMER, ENGINE_VERSION  # noqa: E402
from app.services.ai_patient_service import AIPatientService  # noqa: E402
from app.services.ai_update_service import mark_ai_analysis_for_update  # noqa: E402
from app.services.risk_engine import RiskEngine, load_latest_events  # noqa: E402


@pytest.fixture()
def db() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _mk_patient(db: Session, age: int = 28) -> Patient:
    p = Patient(
        patient_id=f"PAT-{uuid.uuid4().hex[:8].upper()}",
        first_name="Test",
        last_name="Mother",
        age_in_years=age,
        sex="female",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _add(db: Session, patient: Patient, section: str, factor: str, value, when: datetime, unit=None) -> ClinicalEvent:
    ev = ClinicalEvent(
        patient_id=patient.id,
        event_time=when,
        section=section,
        factor=factor,
        value={"value": value, "unit": unit, "type": "integer"},
    )
    db.add(ev)
    db.commit()
    return ev


T0 = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)


def test_model_creates_on_sqlite(db: Session):
    assert "ai_patient_analyses" in Base.metadata.tables
    cols = {c.name for c in AIPatientAnalysis.__table__.columns}
    assert {"patient_id", "summary", "summary_metadata", "risk_factors", "model_used"} <= cols
    assert "tokens_used" not in cols


def test_risk_engine_assess_uses_latest_values_and_correct_keys(db: Session):
    p = _mk_patient(db)
    # old severe reading, newer normal reading -> must NOT flag
    _add(db, p, "vitals", "blood_pressure_systolic", 172, T0, "mmHg")
    _add(db, p, "vitals", "blood_pressure_diastolic", 112, T0, "mmHg")
    _add(db, p, "vitals", "blood_pressure_systolic", 120, T0 + timedelta(days=2), "mmHg")
    _add(db, p, "vitals", "blood_pressure_diastolic", 78, T0 + timedelta(days=2), "mmHg")
    # fetal HR normal must not be read as maternal pulse
    _add(db, p, "per_abdominal_examination", "fetal_heart_rate", 140, T0 + timedelta(days=2), "bpm")

    latest = load_latest_events(db, p.id)
    assert latest[("vitals", "blood_pressure_systolic")].value["value"] == 120

    rec = RiskEngine().assess(db, AiRiskRequest(patient_id=p.id))
    assert rec.overall_risk_level == "low"
    assert rec.referral_recommended is False
    assert rec.referral_urgency == "low"
    assert rec.evidence == []
    assert rec.citations == []
    assert rec.engine == ENGINE_VERSION
    assert rec.safety_note == DISCLAIMER


def test_risk_engine_critical_with_evidence(db: Session):
    p = _mk_patient(db, age=37)
    _add(db, p, "vitals", "blood_pressure_systolic", 168, T0, "mmHg")
    _add(db, p, "vitals", "blood_pressure_diastolic", 108, T0, "mmHg")
    _add(db, p, "urine_examination", "dipstick_protein", "++", T0)
    _add(db, p, "blood_investigations", "hemoglobin", 6.8, T0, "g/dL")

    rec = RiskEngine().assess(db, AiRiskRequest(patient_id=p.id, clinical_question="evaluate preeclampsia risk"))
    assert rec.overall_risk_level == "critical"
    assert rec.referral_recommended is True
    assert rec.referral_urgency == "critical"
    assert rec.summary.startswith("Advisory assessment focused on: evaluate preeclampsia risk.")
    codes = {e.code for e in rec.evidence}
    assert {"severe_hypertension", "proteinuria_significant", "severe_anemia", "age_advanced"} <= codes
    bp_ev = next(e for e in rec.evidence if e.code == "severe_hypertension")
    assert bp_ev.section == "vitals" and bp_ev.factor == "blood_pressure_systolic"
    assert bp_ev.observed_value["value"] == 168
    assert bp_ev.event_time is not None
    assert len(rec.explanation) >= 50


def test_risk_engine_unknown_when_patient_has_no_events(db: Session):
    p = _mk_patient(db)
    rec = RiskEngine().assess(db, AiRiskRequest(patient_id=p.id))
    assert rec.overall_risk_level == "unknown"
    assert rec.referral_recommended is False


def test_risk_engine_missing_patient_raises(db: Session):
    with pytest.raises(ValueError):
        RiskEngine().assess(db, AiRiskRequest(patient_id=uuid.uuid4()))


def test_ai_patient_service_generates_persists_and_invalidates(db: Session):
    p = _mk_patient(db, age=24)
    _add(db, p, "vitals", "blood_pressure_systolic", 150, T0, "mmHg")
    _add(db, p, "vitals", "blood_pressure_diastolic", 95, T0, "mmHg")
    _add(db, p, "vitals", "pulse_rate", 82, T0, "bpm")
    _add(db, p, "blood_investigations", "hemoglobin", 9.0, T0, "g/dL")

    svc = AIPatientService(db)
    analysis = svc.get_or_generate_analysis(p.id)
    assert analysis is not None
    assert analysis.model_used == ENGINE_VERSION
    assert analysis.data_version == 1
    assert analysis.summary_metadata["risk_level"] == "medium"
    assert analysis.referral_needed is True
    assert analysis.referral_urgency == "medium"
    assert analysis.referral_confidence == pytest.approx(0.35)
    names = {r["name"] for r in analysis.risk_factors["detected_risks"]}
    assert {"Elevated blood pressure", "Moderate anemia"} == names
    assert analysis.summary_metadata["disclaimer"] == DISCLAIMER
    # flagged findings come first, then reassuring pulse
    kf = analysis.summary_metadata["key_findings"]
    assert "⚠️" in kf[0]
    assert any("Maternal pulse rate" in k and "Normal" in k for k in kf)

    # cached: same row returned without regeneration
    again = svc.get_or_generate_analysis(p.id)
    assert again.id == analysis.id and again.data_version == 1

    # status: nothing new since analysis
    needs, _ = svc.needs_update(again, p.id)
    assert needs is False

    # new clinical write -> invalidation deletes the row; needs_update true
    _add(db, p, "blood_investigations", "hemoglobin", 12.5, T0 + timedelta(days=1), "g/dL")
    mark_ai_analysis_for_update(db, p.id)
    db.commit()
    assert svc.get_existing(p.id) is None
    needs, last_change = svc.needs_update(None, p.id)
    assert needs is True and last_change is not None

    # regenerate: latest Hb is normal now -> only BP flag remains
    regenerated = svc.get_or_generate_analysis(p.id)
    assert regenerated.referral_confidence == pytest.approx(0.20)
    assert {r["name"] for r in regenerated.risk_factors["detected_risks"]} == {"Elevated blood pressure"}


def test_ai_patient_service_force_regenerate_bumps_version(db: Session):
    p = _mk_patient(db)
    svc = AIPatientService(db)
    a1 = svc.get_or_generate_analysis(p.id)
    assert a1.summary_metadata["risk_level"] == "unknown"
    assert a1.referral_needed is False
    a2 = svc.get_or_generate_analysis(p.id, force_regenerate=True)
    assert a2.id == a1.id
    assert a2.data_version == 2


def test_needs_update_detects_data_recorded_after_analysis(db: Session):
    p = _mk_patient(db)
    svc = AIPatientService(db)
    a = svc.get_or_generate_analysis(p.id)
    # simulate a write path that forgot to invalidate: event created after analysis
    ev = _add(db, p, "vitals", "temperature", 38.6, T0, "°C")
    ev.created_at = a.last_analyzed_at + timedelta(seconds=30)
    db.commit()
    needs, last_change = svc.needs_update(a, p.id)
    assert needs is True


def test_endpoint_response_shape_matches_frontend_contract(db: Session):
    from app.api.v1.endpoints.ai_analysis import _to_response

    p = _mk_patient(db, age=30)
    _add(db, p, "vitals", "blood_pressure_systolic", 165, T0, "mmHg")
    _add(db, p, "urine_examination", "dipstick_protein", "+", T0)
    analysis = AIPatientService(db).get_or_generate_analysis(p.id)

    resp = _to_response(analysis).model_dump()
    # top level
    assert set(resp) >= {"patient_id", "summary", "referral_recommendation", "last_analyzed_at", "data_version", "model_used", "disclaimer"}
    assert resp["model_used"] == ENGINE_VERSION
    # summary card
    s = resp["summary"]
    assert set(s) == {"summary", "key_findings", "risk_level", "metadata"}
    assert s["risk_level"] in {"unknown", "low", "medium", "high", "critical"}
    # referral card
    r = resp["referral_recommendation"]
    assert set(r) >= {"referral_needed", "urgency", "confidence", "reasons", "risk_factors", "clinical_indicators"}
    assert r["urgency"] in {"low", "medium", "high", "critical"}
    assert 0.0 <= r["confidence"] <= 0.95
    dr = r["risk_factors"]["detected_risks"]
    assert dr and {"name", "weight", "value"} <= set(dr[0])
    assert "confidence_calculation" in r["risk_factors"]
    assert r["recommended_facility"] is None and r["recommended_specialties"] == []
    assert s["risk_level"] == "critical" and r["urgency"] == "critical"
