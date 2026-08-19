# Advisory Engine (rule-based) — Patient Summary & Referral Suggestion

**Status: implemented.** This document describes what the code actually does.

> There is **no LLM, no OpenAI/GPT, no retrieval-augmented generation (RAG), no
> vector database and no background worker** in SmartAama. The "AI" cards on the
> patient profile are produced by a small, deterministic, **rule-based advisory
> engine** that reads the *latest recorded value* of a fixed set of clinical
> data points and applies fixed thresholds. `model_used` / `model_version` is
> always `"rule-based-advisory-v2"`. LLM-based summarisation and guideline
> retrieval are possible future work and are **not** present in the codebase.

## Safety statement

Every output is **advisory only**. It is not a diagnosis, it does not replace
clinical assessment, and clinical decisions rest with the responsible qualified
clinician. Every human-readable string the engine emits is checked at runtime by
`app/ai/validators.py::validate_advisory_language`, which rejects imperative or
autonomous wording ("must", "administer", "diagnose", "patient has
pre-eclampsia", ...). Responses carry an explicit `disclaimer` field.

The engine only sees what has been recorded. Missing, stale or mistyped data
means missing or wrong flags. A `low`/`unknown` result never excludes risk.

---

## Where the code lives

| File | Role |
|------|------|
| `backend/app/services/advisory_rules.py` | **Single source of truth.** Pure function `evaluate_latest_values(latest, patient_age=None) -> RuleResult`; all input keys, thresholds, weights, wording, risk-level and referral logic. No DB, no settings. |
| `backend/app/services/risk_engine.py` | `RiskEngine` (used by `POST /ai/risk`). Loads latest event per `(section, factor)` (`load_latest_events`, `latest_per_factor`), runs the shared rules, returns `AdvisoryRiskRecommendation` with evidence. |
| `backend/app/services/ai_patient_service.py` | `AIPatientService` (used by `/ai-analysis/*`, the patient-profile cards). Same shared rules; shapes the result into summary + referral suggestion and caches it in `ai_patient_analyses`. |
| `backend/app/services/ai_update_service.py` | `mark_ai_analysis_for_update(db, patient_id)` — deletes the cached row; called from every clinical write path. |
| `backend/app/ai/validators.py` | Advisory-language guardrail. |
| `backend/app/schemas/ai.py`, `backend/app/schemas/ai_analysis.py` | Response schemas. |
| `backend/app/models/ai_patient_analysis.py` | Cache table (`JSON` with `JSONB` variant on PostgreSQL; portable to SQLite for tests). |
| `backend/tests/test_risk_rules.py`, `test_risk_engine_service.py`, `test_risk_endpoints.py` | Tests. |

---

## What the engine reads (exact `section.factor` keys from `app/models/medical_schema.py`)

Only the **latest** value per key is used (latest by `event_time`, then
`created_at`). Where the same finding is captured in several sections, the most
recent across the group is used.

| Domain | Key(s) | Notes |
|--------|--------|-------|
| Blood pressure | `vitals.blood_pressure_systolic`, `vitals.blood_pressure_diastolic` | mmHg |
| Maternal pulse | `vitals.pulse_rate` | **maternal only** — fetal heart rate is never read as maternal pulse |
| Temperature | `vitals.temperature` | °C |
| Respiratory rate | `vitals.respiratory_rate` | breaths/min |
| BMI | `vitals.body_mass_index` | context only |
| Hemoglobin | `blood_investigations.hemoglobin` | g/dL |
| Blood glucose | `blood_investigations.blood_glucose` | mg/dL (fasting status unknown → conservative) |
| Platelets | `blood_investigations.platelet_count` | /mm³ |
| Proteinuria | `urine_examination.dipstick_protein` (`Negative/Trace/+/++/+++/++++`), `urine_examination.urine_protein_24hr`, `urine_examination.protein_creatinine_ratio` | |
| Fetal heart rate | `per_abdominal_examination.fetal_heart_rate`, `ultrasonography.fetal_heart_rate` (most recent) | labelled **fetal**, fetal thresholds |
| Placenta | `ultrasonography.placental_location` | Low-lying / Previa |
| Symptoms | `second_trimester_anc.headache_epigastric_visual_symptoms`, `third_trimester_anc.headache_epigastric_visual_symptoms`; `first_trimester_anc.vaginal_bleeding_or_discharge`, `third_trimester_anc.vaginal_bleeding_or_discharge`; `*_trimester_anc.fever_or_urinary_symptoms`; `third_trimester_anc.fetal_movement_normal` (`false` → reduced fetal movement) | booleans |
| General signs / exam | `general_signs.pallor`, `general_signs.edema`, `general_examination.level_of_consciousness` | |
| History (context) | `past_medical_history.hypertension`, `past_medical_history.diabetes`, `obstetric_history.pregnancy_loss_history`, `obstetric_history.previous_complications`, patient `age_in_years` | info-level only |

Anything else recorded is ignored (and legacy keys such as `vitals.bp_systolic`
or `lab_investigations.hemoglobin` are **not** read — they were never written by
the schema).

## Thresholds and flags

Severity: `info` < `warning` < `severe` < `critical`. Weight = contribution to
the referral score. (Table generated from `advisory_rules.py`; edit the code, not
the table.)

| Rule code | Trigger | Severity | Weight |
|-----------|---------|----------|--------|
| `severe_hypertension` | SBP ≥160 or DBP ≥110 | severe | 0.35 |
| `hypertension` | SBP ≥140 or DBP ≥90 | warning | 0.20 |
| `hypotension` | SBP <90 | warning | 0.15 |
| `maternal_tachycardia_severe` | pulse ≥120 | severe | 0.20 |
| `maternal_tachycardia` | pulse 100–119 | warning | 0.10 |
| `maternal_bradycardia` | pulse <50 | warning | 0.10 |
| `fever` | temperature ≥38.0 °C | warning | 0.15 |
| `tachypnoea_severe` / `tachypnoea` | RR ≥30 / RR ≥21 | severe / warning | 0.20 / 0.10 |
| `bmi_high` / `bmi_low` | BMI ≥30 / <18.5 | info | 0.05 |
| `severe_anemia` | Hb <7.0 | severe | 0.30 |
| `moderate_anemia` | Hb 7.0–9.9 | warning | 0.15 |
| `mild_anemia` | Hb 10.0–10.9 | info | 0.05 |
| `hyperglycaemia_marked` / `hyperglycaemia` | glucose ≥200 / ≥140 mg/dL | warning | 0.20 / 0.10 |
| `thrombocytopenia_severe` / `thrombocytopenia` | platelets <50,000 / <100,000 | severe / warning | 0.25 / 0.15 |
| `proteinuria_significant` / `proteinuria` / `proteinuria_trace` | dipstick ≥`++` / `+` / `Trace` | warning / warning / info | 0.20 / 0.15 / 0 |
| `proteinuria_24h` / `proteinuria_pcr` | ≥300 mg/24h / PCR ≥0.3 | warning | 0.15 |
| `preeclampsia_symptoms` | headache/epigastric/visual = true | warning | 0.15 |
| `vaginal_bleeding` | bleeding/discharge = true | warning | 0.20 |
| `fever_or_urinary_symptoms` | = true | warning | 0.10 |
| `reduced_fetal_movement` | fetal_movement_normal = false | warning (fetal) | 0.15 |
| `fetal_bradycardia` / `fetal_tachycardia` | FHR <110 / >160 bpm | warning (fetal) | 0.20 / 0.15 |
| `unconscious` | level_of_consciousness = Unconscious | **critical** | 0.50 |
| `altered_consciousness` | Drowsy / Confused | severe | 0.30 |
| `pallor`, `edema` | = true | info | 0.05 |
| `placenta_previa_or_low_lying` | Low-lying / Previa | warning | 0.10 |
| `history_hypertension`, `history_diabetes`, `history_pregnancy_loss`, `history_previous_complications`, `age_advanced` (≥35), `age_young` (<18) | | info | 0.05 |

### Combination rules (escalate the overall level)

| Combination | Minimum level |
|-------------|---------------|
| severe hypertension **and** (any proteinuria **or** headache/epigastric/visual symptoms) | **critical** |
| severe hypertension **and** low platelets | **critical** |
| elevated (non-severe) hypertension **and** (proteinuria **or** symptoms) | high |
| vaginal bleeding **and** (maternal tachycardia **or** hypotension) | high |
| fever **and** maternal tachycardia | high |
| ≥3 concurrent maternal `warning`-or-worse flags | high |

### Overall risk level

`unknown` (no evaluable data recorded) · `low` (only info flags / nothing
crossed) · `medium` (any warning) · `high` (any severe, or a high combination) ·
`critical` (any critical flag / critical combination).

### Referral suggestion

* `referral_needed` / `referral_recommended` = level ∈ {medium, high, critical}
* `urgency` = the level (`low` when not recommended) — vocabulary `low | medium | high | critical`
* `confidence` / `referral_score` = **sum of triggered rule weights, capped at 0.95**.
  This is a *transparency score* kept for the UI's percentage display; it is
  **not** a probability and not a model confidence.
* `reasons` = combination reasons first, then per-flag reasons (warning or worse).

---

## Endpoints

All routes require a valid JWT and **facility-level access to the patient**
(`app/core/authz.py::get_accessible_patient_or_404`: admins see all; others need
the patient registered at their facility or a referral involving their facility;
403 otherwise, 404 if the patient does not exist).

| Method & path | Who | What |
|---------------|-----|------|
| `GET /api/v1/ai-analysis/patients/{patient_id}/analysis?auto_generate=true&force_regenerate=false` | any authenticated user with access (**read**); generation (auto or forced) only for `clinician` / `hospital` / `admin` | Returns the stored analysis. A viewer whose patient has no stored analysis gets **404** (nothing is generated); a viewer passing `force_regenerate=true` gets **403**. |
| `POST /api/v1/ai-analysis/generate` `{patient_id, force_regenerate}` | clinician / hospital / admin | Generate or regenerate and return the analysis. |
| `GET /api/v1/ai-analysis/patients/{patient_id}/status` | any authenticated user with access | `has_analysis`, `last_analyzed_at`, `data_version`, `needs_update` (true when nothing stored **or** an event/referral was recorded after `last_analyzed_at`), `last_data_change_at`, `model_used`. |
| `DELETE /api/v1/ai-analysis/patients/{patient_id}` | clinician / hospital / admin | Delete the stored analysis. |
| `POST /api/v1/ai/risk` `{patient_id, clinical_question?, referral_id?}` | clinician / hospital / admin | Explainable assessment with per-flag `evidence`; writes an `AuditLog` row (`AI_RISK_ASSESSMENT_RUN`). |

### `GET /ai-analysis/patients/{id}/analysis` response

```json
{
  "patient_id": "uuid",
  "summary": {
    "summary": "Patient (29 years): 2 finding(s) outside advisory rule thresholds ... Overall advisory risk level: critical. Clinician review is advised.",
    "key_findings": [
      "Blood pressure: 165/100 mmHg (⚠️ Severely Elevated, ≥160/110)",
      "Urine dipstick protein: ++ (⚠️ Elevated, ++ or more)",
      "Maternal pulse rate: 82 bpm (Normal range)"
    ],
    "risk_level": "critical",
    "metadata": { "engine": "rule-based-advisory-v2", "clinical_events": 4, "data_points_evaluated": 3, "flag_count": 2, "disclaimer": "..." }
  },
  "referral_recommendation": {
    "referral_needed": true,
    "urgency": "critical",
    "confidence": 0.55,
    "reasons": ["Severe-range blood pressure together with proteinuria ... may indicate severe pre-eclampsia features; urgent clinician review and consideration of immediate referral is advised.", "..."],
    "recommended_facility": null,
    "recommended_specialties": [],
    "risk_factors": {
      "detected_risks": [{ "name": "Severe hypertension", "weight": 0.35, "value": "165/100 mmHg", "code": "severe_hypertension", "severity": "severe", "domain": "maternal" }],
      "confidence_calculation": "Sum of rule weights: 55.0% (capped at 95%)",
      "data_points_analyzed": 4
    },
    "clinical_indicators": { "engine": "rule-based-advisory-v2", "risk_level": "critical", "total_risk_factors": 2, "confidence_score": "55.0%", "severe_hypertension": "DETECTED: 165/100 mmHg" }
  },
  "last_analyzed_at": "2026-08-18T10:00:00Z",
  "data_version": 1,
  "model_used": "rule-based-advisory-v2",
  "disclaimer": "This output is generated by a deterministic rule-based advisory engine ..."
}
```

`key_findings` strings keep the `⚠️` / `Elevated` / `Low` / `Normal` markers the
frontend uses for colouring. `recommended_facility` / `recommended_specialties`
are reserved and always empty (facility suggestion is not implemented).

### `POST /ai/risk` response

`{patient_id, generated_at, model_version: "rule-based-advisory-v2", disclaimer, recommendation}` where
`recommendation` = `{overall_risk_level, summary, recommended_actions[], referral_recommended, referral_urgency, referral_reason, referral_reasons[], referral_score, explanation, evidence[{section, factor, observed_value, event_time, note, code, severity, domain, finding}], citations: [] (always empty; retrieval not implemented), engine, safety_note}`.

---

## Caching & invalidation

The result is cached one row per patient in `ai_patient_analyses`. Every clinical
write path (`/events`, `/medical-data`, referrals) calls
`mark_ai_analysis_for_update(db, patient_id)`, which deletes the row inside the
same transaction; the next generation request rebuilds it and `data_version`
increments on regeneration. `GET .../status` additionally compares the latest
event/referral `created_at` with `last_analyzed_at` as a defensive check.

## Database table `ai_patient_analyses`

| Column | Type | Notes |
|--------|------|-------|
| id, patient_id (unique FK) | UUID | |
| summary | TEXT | |
| summary_metadata | JSON (JSONB on PG) | key_findings, risk_level, counts, disclaimer |
| referral_needed / referral_urgency / referral_confidence | bool / varchar(20) / float | urgency ∈ low, medium, high, critical |
| referral_reasons, recommended_specialties | JSON | |
| recommended_facility | varchar(255) | always NULL (reserved) |
| risk_factors, clinical_indicators | JSON | |
| model_used | varchar(100) | `rule-based-advisory-v2` |
| data_version, last_analyzed_at, created_at | | |

(Legacy databases may still contain a nullable `tokens_used` column; it is no
longer mapped or written.)

## Limitations (please read)

* Rules are fixed thresholds on the latest value only — no trends, no gestational-age
  awareness (e.g. BP thresholds are not adjusted for gestation), no unit conversion
  (values are assumed to be in the schema's units), no free-text understanding.
* Booleans in trimester ANC sections are read as recorded; a symptom stays flagged
  until a newer entry (in any trimester section of the same group) records `false`.
* Fetal presentation, gestational age, AFI, EFW, thyroid, LFT/RFT, serology are
  **not** evaluated (they are recorded but no rule reads them yet).
* The referral "confidence" is a weight sum, not a calibrated probability.
* No guideline citations are produced (`citations` is always `[]`).

## Tests

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/test_risk_rules.py tests/test_risk_engine_service.py tests/test_risk_endpoints.py -q
```

`test_risk_rules.py` (pure rules: thresholds, fetal-vs-maternal, latest-per-factor,
unknown/no-data, advisory-language validation), `test_risk_engine_service.py`
(services on in-memory SQLite, caching/invalidation, response shape),
`test_risk_endpoints.py` (authorization and HTTP shapes via the shared conftest).

## Frontend

`frontend/src/components/AIPatientSummary.tsx` and `AIReferralRecommendation.tsx`
render the two cards from `GET /ai-analysis/patients/{id}/analysis` (fetched in
`PatientProfile.tsx`). They present the output as "Advisory (rule-based)".

## Future work (not implemented)

* LLM-generated narrative summaries and guideline retrieval (RAG) with citations.
* Gestational-age-aware and trend-aware rules; configurable thresholds per facility.
* Facility / specialty suggestion for referrals.
