# backend/tests/test_risk_rules.py
"""
Pure-function tests for the rule-based advisory engine
(app/services/advisory_rules.py) and the shared latest-per-factor helper.

No database, no FastAPI app, no conftest fixtures required.
Run:  backend\\.venv\\Scripts\\python.exe -m pytest tests/test_risk_rules.py -q
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

# Make `app` importable even before pytest.ini (pythonpath=.) exists.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Settings are only needed if something imports app.core.config; set safe defaults.
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-at-least-32-chars-long")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("ENV", "dev")

import pytest  # noqa: E402

from app.ai.validators import AdvisoryLanguageError, validate_advisory_language  # noqa: E402
from app.models.medical_schema import MEDICAL_SCHEMA  # noqa: E402
from app.services import advisory_rules as ar  # noqa: E402
from app.services.advisory_rules import (  # noqa: E402
    DISCLAIMER,
    ENGINE_VERSION,
    RULE_INPUT_KEYS,
    LatestValue,
    build_summary_text,
    evaluate_latest_values,
)
from app.services.risk_engine import latest_per_factor, to_latest_values  # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _codes(result) -> set:
    return {f.code for f in result.flags}


def _payload(v: Any, unit: Optional[str] = None) -> dict:
    """Mimic the stored ClinicalEvent.value payload written by /medical-data."""
    return {"value": v, "unit": unit, "type": "integer"}


# ---------------------------------------------------------------------------
# schema alignment
# ---------------------------------------------------------------------------

def test_every_rule_input_key_exists_in_medical_schema():
    """The engine must only read (section, factor) keys the schema actually defines."""
    for section, factor in RULE_INPUT_KEYS:
        assert section in MEDICAL_SCHEMA, f"unknown section {section}"
        names = {f.name for f in MEDICAL_SCHEMA[section].fields}
        assert factor in names, f"{section}.{factor} is not a schema field"


def test_dipstick_enum_values_are_all_understood():
    enum_values = next(
        f for f in MEDICAL_SCHEMA["urine_examination"].fields if f.name == "dipstick_protein"
    ).enum_values
    for v in enum_values:
        assert ar._dipstick_grade(v) is not None, v


# ---------------------------------------------------------------------------
# blood pressure
# ---------------------------------------------------------------------------

def test_severe_bp_is_high_and_recommends_referral():
    r = evaluate_latest_values({ar.K_BP_SYS: 165, ar.K_BP_DIA: 100})
    assert r.risk_level == "high"
    assert "severe_hypertension" in _codes(r)
    assert r.referral_recommended is True
    assert r.referral_urgency == "high"


def test_severe_diastolic_alone_is_severe():
    r = evaluate_latest_values({ar.K_BP_SYS: 150, ar.K_BP_DIA: 112})
    assert "severe_hypertension" in _codes(r)
    # evidence key points at the diastolic value that crossed the threshold
    assert r.flags[0].factor == "blood_pressure_diastolic"


def test_severe_bp_plus_proteinuria_is_critical():
    r = evaluate_latest_values({
        ar.K_BP_SYS: _payload(170, "mmHg"),
        ar.K_BP_DIA: _payload(115, "mmHg"),
        ar.K_DIPSTICK: {"value": "++", "type": "enum"},
    })
    assert r.risk_level == "critical"
    assert r.referral_urgency == "critical"
    assert r.referral_recommended is True
    assert any("pre-eclampsia" in reason for reason in r.referral_reasons)


def test_severe_bp_plus_symptoms_is_critical():
    r = evaluate_latest_values({ar.K_BP_SYS: 162, ar.K_BP_DIA: 95, ar.K_SYMPTOMS_T3: True})
    assert r.risk_level == "critical"


def test_elevated_bp_plus_proteinuria_is_high():
    r = evaluate_latest_values({ar.K_BP_SYS: 145, ar.K_BP_DIA: 92, ar.K_DIPSTICK: "+"})
    assert r.risk_level == "high"
    assert {"hypertension", "proteinuria"} <= _codes(r)


def test_elevated_bp_alone_is_medium():
    r = evaluate_latest_values({ar.K_BP_SYS: 142, ar.K_BP_DIA: 88})
    assert r.risk_level == "medium"
    assert r.referral_recommended is True
    assert r.referral_urgency == "medium"


def test_normal_bp_is_low_no_referral():
    r = evaluate_latest_values({ar.K_BP_SYS: 118, ar.K_BP_DIA: 76})
    assert r.risk_level == "low"
    assert r.referral_recommended is False
    assert r.referral_urgency == "low"
    assert any("Normal" in n for n in r.normal_findings)


# ---------------------------------------------------------------------------
# hemoglobin
# ---------------------------------------------------------------------------

def test_hb_below_7_is_severe_anemia_high():
    r = evaluate_latest_values({ar.K_HB: 6.5})
    assert "severe_anemia" in _codes(r)
    assert r.risk_level == "high"


def test_hb_bands():
    assert "moderate_anemia" in _codes(evaluate_latest_values({ar.K_HB: 8.9}))
    assert "mild_anemia" in _codes(evaluate_latest_values({ar.K_HB: 10.5}))
    r = evaluate_latest_values({ar.K_HB: 12.0})
    assert not r.flags and r.risk_level == "low"


def test_mild_anemia_alone_is_low_no_referral():
    r = evaluate_latest_values({ar.K_HB: 10.5})
    assert r.risk_level == "low"
    assert r.referral_recommended is False


# ---------------------------------------------------------------------------
# fetal vs maternal heart rate
# ---------------------------------------------------------------------------

def test_normal_fetal_hr_140_does_not_flag_maternal_tachycardia():
    r = evaluate_latest_values({ar.K_FHR_ABDO: 140})
    assert "maternal_tachycardia" not in _codes(r)
    assert "maternal_tachycardia_severe" not in _codes(r)
    assert r.risk_level == "low"
    assert any("Fetal heart rate" in n for n in r.normal_findings)


def test_ultrasound_fetal_hr_150_is_normal_and_not_maternal():
    r = evaluate_latest_values({ar.K_FHR_USG: 150})
    assert not r.flags
    assert r.risk_level == "low"


def test_maternal_pulse_120_flags_severe_maternal_tachycardia():
    r = evaluate_latest_values({ar.K_PULSE: 120})
    assert "maternal_tachycardia_severe" in _codes(r)
    assert r.risk_level == "high"
    flag = r.flags[0]
    assert flag.domain == "maternal"
    assert flag.section == "vitals" and flag.factor == "pulse_rate"


def test_maternal_pulse_104_flags_warning():
    r = evaluate_latest_values({ar.K_PULSE: 104})
    assert "maternal_tachycardia" in _codes(r)
    assert r.risk_level == "medium"


def test_fetal_bradycardia_is_labelled_fetal():
    r = evaluate_latest_values({ar.K_FHR_ABDO: 100})
    assert "fetal_bradycardia" in _codes(r)
    assert r.flags[0].domain == "fetal"
    assert "Fetal" in r.flags[0].finding


def test_fetal_hr_uses_most_recent_source():
    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    new = old + timedelta(days=7)
    r = evaluate_latest_values({
        ar.K_FHR_ABDO: LatestValue(100, old),   # old abnormal
        ar.K_FHR_USG: LatestValue(140, new),    # newer normal
    })
    assert "fetal_bradycardia" not in _codes(r)


# ---------------------------------------------------------------------------
# latest-per-factor semantics
# ---------------------------------------------------------------------------

@dataclass
class _Ev:
    section: str
    factor: str
    value: Any
    event_time: datetime
    created_at: Optional[datetime] = None
    note: Optional[str] = None
    referral_id: Any = None
    id: Any = None


def test_latest_per_factor_old_abnormal_new_normal_does_not_flag():
    t0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    events = [
        _Ev("vitals", "blood_pressure_systolic", _payload(170), t0),
        _Ev("vitals", "blood_pressure_diastolic", _payload(115), t0),
        _Ev("vitals", "blood_pressure_systolic", _payload(118), t0 + timedelta(days=3)),
        _Ev("vitals", "blood_pressure_diastolic", _payload(76), t0 + timedelta(days=3)),
    ]
    latest = latest_per_factor(events)
    assert latest[("vitals", "blood_pressure_systolic")].value["value"] == 118
    r = evaluate_latest_values(to_latest_values(latest))
    assert not r.flags
    assert r.risk_level == "low"
    assert r.referral_recommended is False


def test_latest_per_factor_uses_created_at_as_tiebreak_and_handles_naive_datetimes():
    t0 = datetime(2026, 2, 1, 9, 0)  # naive
    events = [
        _Ev("blood_investigations", "hemoglobin", _payload(6.0), t0, created_at=t0),
        _Ev("blood_investigations", "hemoglobin", _payload(12.0), t0, created_at=t0 + timedelta(seconds=5)),
    ]
    latest = latest_per_factor(events)
    assert latest[("blood_investigations", "hemoglobin")].value["value"] == 12.0
    r = evaluate_latest_values(to_latest_values(latest))
    assert "severe_anemia" not in _codes(r)


def test_latest_per_factor_new_abnormal_after_old_normal_flags():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = [
        _Ev("blood_investigations", "hemoglobin", _payload(12.0), t0),
        _Ev("blood_investigations", "hemoglobin", _payload(6.2), t0 + timedelta(days=1)),
    ]
    r = evaluate_latest_values(to_latest_values(latest_per_factor(events)))
    assert "severe_anemia" in _codes(r)


# ---------------------------------------------------------------------------
# symptoms / other rules
# ---------------------------------------------------------------------------

def test_symptom_booleans_accept_true_and_string_true():
    assert "vaginal_bleeding" in _codes(evaluate_latest_values({ar.K_BLEED_T3: True}))
    assert "vaginal_bleeding" in _codes(evaluate_latest_values({ar.K_BLEED_T1: "true"}))
    assert "vaginal_bleeding" not in _codes(evaluate_latest_values({ar.K_BLEED_T3: False}))


def test_symptom_group_uses_most_recent_section():
    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    new = old + timedelta(days=30)
    r = evaluate_latest_values({
        ar.K_SYMPTOMS_T2: LatestValue(True, old),
        ar.K_SYMPTOMS_T3: LatestValue(False, new),
    })
    assert "preeclampsia_symptoms" not in _codes(r)


def test_reduced_fetal_movement_flags_when_false():
    r = evaluate_latest_values({ar.K_FETAL_MOVEMENT_T3: False})
    assert "reduced_fetal_movement" in _codes(r)
    assert r.flags[0].domain == "fetal"
    r2 = evaluate_latest_values({ar.K_FETAL_MOVEMENT_T3: True})
    assert not r2.flags


def test_fever_and_tachycardia_escalates_to_high():
    r = evaluate_latest_values({ar.K_TEMP: 38.4, ar.K_PULSE: 105})
    assert r.risk_level == "high"


def test_unconscious_is_critical():
    r = evaluate_latest_values({ar.K_CONSCIOUSNESS: "Unconscious"})
    assert r.risk_level == "critical"
    assert r.referral_urgency == "critical"


def test_three_maternal_warnings_escalate_to_high():
    r = evaluate_latest_values({ar.K_TEMP: 38.2, ar.K_GLUCOSE: 150, ar.K_HB: 8.5})
    assert len(r.flags_at_least("warning")) == 3
    assert r.risk_level == "high"


def test_history_flags_are_info_only():
    r = evaluate_latest_values({ar.K_HX_HTN: True, ar.K_HX_DM: True, ar.K_HX_LOSS: "Stillbirth"}, patient_age=38)
    assert r.risk_level == "low"
    assert r.referral_recommended is False
    assert {"history_hypertension", "history_diabetes", "history_pregnancy_loss", "age_advanced"} <= _codes(r)


def test_ignores_unknown_keys_and_unparseable_values():
    r = evaluate_latest_values({
        ("vitals", "bp_systolic"): 200,           # legacy/wrong key -> ignored
        ("lab_investigations", "hemoglobin"): 4,  # legacy/wrong key -> ignored
        ar.K_BP_SYS: "not-a-number",
    })
    assert r.risk_level == "unknown"
    assert not r.flags


# ---------------------------------------------------------------------------
# unknown / no data
# ---------------------------------------------------------------------------

def test_no_data_is_unknown_and_no_referral():
    r = evaluate_latest_values({})
    assert r.risk_level == "unknown"
    assert r.referral_recommended is False
    assert r.referral_urgency == "low"
    assert r.referral_score == 0.0
    assert r.referral_reasons and "No clinical measurements" in r.referral_reasons[0]
    assert "no clinical measurements" in build_summary_text(r).lower()


# ---------------------------------------------------------------------------
# referral score and ordering
# ---------------------------------------------------------------------------

def test_referral_score_is_sum_of_weights_capped():
    r = evaluate_latest_values({ar.K_BP_SYS: 165, ar.K_DIPSTICK: "++"})
    assert r.referral_score == pytest.approx(0.55)
    big = evaluate_latest_values({
        ar.K_BP_SYS: 170, ar.K_DIPSTICK: "+++", ar.K_HB: 6, ar.K_PULSE: 125,
        ar.K_TEMP: 39, ar.K_CONSCIOUSNESS: "Unconscious",
    })
    assert big.referral_score == 0.95


def test_flags_are_sorted_most_severe_first():
    r = evaluate_latest_values({ar.K_HB: 10.5, ar.K_BP_SYS: 165, ar.K_TEMP: 38.5})
    sev = [f.severity for f in r.flags]
    assert sev == ["severe", "warning", "info"]


# ---------------------------------------------------------------------------
# advisory language guardrail
# ---------------------------------------------------------------------------

_SCENARIOS = [
    {},
    {ar.K_BP_SYS: 118, ar.K_BP_DIA: 76, ar.K_HB: 12, ar.K_PULSE: 80, ar.K_TEMP: 36.8},
    {ar.K_BP_SYS: 142, ar.K_BP_DIA: 88},
    {ar.K_BP_SYS: 165, ar.K_BP_DIA: 100, ar.K_DIPSTICK: "++", ar.K_SYMPTOMS_T3: True},
    {ar.K_HB: 6.5, ar.K_PALLOR: True},
    {ar.K_PULSE: 120, ar.K_TEMP: 38.5, ar.K_RR: 31},
    {ar.K_FHR_ABDO: 100, ar.K_FETAL_MOVEMENT_T3: False},
    {ar.K_BLEED_T3: True, ar.K_BP_SYS: 85, ar.K_BP_DIA: 50},
    {ar.K_CONSCIOUSNESS: "Drowsy", ar.K_PLATELETS: 40000, ar.K_BP_SYS: 170},
    {ar.K_GLUCOSE: 210, ar.K_BMI: 34, ar.K_EDEMA: True, ar.K_PLACENTA: "Previa"},
    {ar.K_HX_HTN: True, ar.K_HX_COMPLICATIONS: "PPH in 2021", ar.K_HX_LOSS: "Miscarriage"},
    {ar.K_PROTEIN_24H: 450, ar.K_PCR: 0.4, ar.K_DIPSTICK: "Trace"},
]


@pytest.mark.parametrize("latest", _SCENARIOS)
def test_all_generated_strings_pass_advisory_validation(latest):
    r = evaluate_latest_values(latest, patient_age=36)
    for text in r.all_texts():
        validate_advisory_language(text)  # raises on failure
    validate_advisory_language(build_summary_text(r, age=36, event_count=len(latest)))
    validate_advisory_language(build_summary_text(r, age=None, event_count=0))


def test_disclaimer_and_engine_constants():
    validate_advisory_language(DISCLAIMER)
    assert "advisory" in DISCLAIMER.lower()
    assert ENGINE_VERSION == "rule-based-advisory-v2"
    assert "gpt" not in ENGINE_VERSION.lower() and "openai" not in ENGINE_VERSION.lower()


def test_validator_still_rejects_imperative_language():
    with pytest.raises(AdvisoryLanguageError):
        validate_advisory_language("The patient must be referred immediately.")
