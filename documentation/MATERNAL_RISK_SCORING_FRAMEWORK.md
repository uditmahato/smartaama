# Maternal Health Risk Scoring Framework (design reference)

> **STATUS: DESIGN REFERENCE — NOT IMPLEMENTED IN CODE.**
>
> The 10-factor / 10%-each scoring scheme described below is a clinical design
> proposal. It is **not** what the backend runs. The former `MATERNAL_RISK_FACTORS`
> constant that mirrored this table was never wired into any scoring and has been
> removed from `app/services/ai_patient_service.py`.
>
> What the application actually implements is a smaller, deterministic
> **rule-based advisory engine** (`backend/app/services/advisory_rules.py`) that
> evaluates the latest recorded vitals, investigations, ANC symptom booleans and
> a few history fields against fixed thresholds. Its inputs, thresholds, weights,
> risk levels (`unknown | low | medium | high | critical`), urgency
> (`low | medium | high | critical`) and referral logic are documented in
> **`documentation/AI_FEATURES_README.md`**. No LLM/RAG is used.
>
> The clinical content below is kept as domain reference for a possible future
> implementation. Wiring it would require most of the listed sub-factors to be
> captured as structured fields first (many — e.g. multiple gestation, ART,
> prior PPH, cervical surgery — do not exist in `app/models/medical_schema.py`).

## Overview (proposal)
The proposed referral score would be calculated from **10 major maternal health risk factors**, each weighted at **10%** (total 100%).

## How It Would Work

### Risk Factor Scoring
1. **Major Risk Factor Weight**: Each of the 10 maternal health risk factors = 10%
2. **Sub-Factor Division**: Each major factor's 10% is divided equally among its sub-factors
3. **Score Calculation**: 
   ```
   Risk Factor Score = 10% × (Sub-factors present / Total sub-factors)
   ```
4. **Total Confidence**: Sum of all risk factor scores (0-100%)

### Example Calculation
If a patient has:
- **Pre-eclampsia/Eclampsia**: 5 out of 11 sub-factors present
  - Score = 10% × (5/11) = 4.5%
- **Gestational Diabetes**: 3 out of 7 sub-factors present
  - Score = 10% × (3/7) = 4.3%
- **Anemia in Pregnancy**: 2 out of 4 sub-factors present
  - Score = 10% × (2/4) = 5%

**Total Confidence = 4.5% + 4.3% + 5% = 13.8%**

---

## The 10 Major Maternal Health Risk Factors

### 1. Pre-eclampsia/Eclampsia (10%)
**Sub-factors** (11 total):
- Primigravida
- Obesity (BMI >35)
- Family history of hypertension/pre-eclampsia
- Edema not resolving with rest
- Multiple gestation
- Hypertension
- Assisted pregnancy
- Clinical features (blurring of vision/headache/abdominal pain)
- Coagulation disorders
- Diabetes
- High blood pressure (SBP >140 OR DBP >90 after 20 weeks)

### 2. Placenta Previa (10%)
**Sub-factors** (7 total):
- Multiple gestation
- Vaginal bleeding (PV bleed)
- Age >35 years
- Pregnancy following ART
- Prior uterine surgeries
- Prior placenta previa
- Smoking

### 3. Abruptio Placenta (10%)
**Sub-factors** (9 total):
- Age >35 years
- Vaginal bleeding (PV bleed)
- High birth order (>5)
- Smoking/cocaine use
- Hypertension in pregnancy
- Uterine anomaly
- Coagulation disorder
- Prior abruption
- Trauma

### 4. Gestational Diabetes Mellitus (10%)
**Sub-factors** (7 total):
- Family history of diabetes
- Prior overweight baby
- Prior stillbirth
- Prior polyhydramnios
- Age >30 years
- Obesity
- Diabetes

### 5. Preterm Birth (10%)
**Sub-factors** (8 total):
- Prior preterm birth
- Multiple gestation
- Prior cervical surgery
- Short interpregnancy interval (<6 months)
- Smoking
- Polyhydramnios
- Infection (UTI)
- Pregnancy following ART

### 6. Postpartum Hemorrhage (10%)
**Sub-factors** (15 total):
- Grand multipara
- Over-distention of uterus
- Multiple gestation
- Polyhydramnios
- Large baby (>4kg)
- Malnutrition & anemia
- Low hemoglobin (Hb <9 g/dL)
- Antepartum hemorrhage
- Placenta previa
- Abruptio placenta
- Prolonged labor (>12 hours)
- Precipitated labor (delivery within 3 hours)
- Uterine fibroid
- Uterine malformation
- Prior PPH history

### 7. Recurrent Pregnancy Loss (10%)
**Sub-factors** (9 total):
- Uterine anomaly
- Advanced maternal age (>35 years)
- Prior pregnancy loss
- Genetic/chromosomal diseases
- Infection during pregnancy
- Overt hypothyroidism
- Uncontrolled diabetes mellitus
- Obesity
- Smoking/alcohol/harmful intoxicants

### 8. Anemia in Pregnancy (10%)
**Sub-factors** (4 total):
- Short birth spacing
- Pallor
- Iron tablets not taken
- Low hemoglobin (Hb <11 in 1st TM, <10.5 in 2nd TM)

### 9. Obstructed/Prolonged Labor (10%)
**Sub-factors** (12 total):
- Maternal height (<145cm)
- Malpresentation
- Primigravida
- Previous stillbirth/prolonged labor
- Symphysis-Fundal Height (SFH) > GA by ≥3cm
- History of prior large baby (>4kg)
- Gestational diabetes
- Maternal obesity
- Excessive maternal weight gain
- Difficult fetal palpation
- Polyhydramnios

### 10. Maternal Sepsis (Antenatal/Postnatal) (10%)
**Sub-factors** (9 total):
- Unhygienic practices
- Fever
- Home delivery without clean kit
- Foul-smelling discharge
- Delivery with unwashed hands
- Prolonged rupture of membranes (>18 hours)
- Use of non-sterile instruments
- Home delivery
- Application of harmful substances (cow dung, ash, oil, herbs)

---

## Referral Decision Tree (proposal — not implemented)

### Confidence Score Thresholds (proposal)

| Confidence Range | Urgency | Referral Status | Action |
|-----------------|---------|-----------------|--------|
| ≥75% | **CRITICAL** | **YES** | Immediate referral to tertiary facility |
| 55-74% | **HIGH** | **YES** | Urgent referral to district hospital |
| 35-54% | **MEDIUM** | **YES** | Refer to higher facility for evaluation |
| 15-34% | **LOW** | **YES** | Consider referral based on clinical judgment |
| <15% | **LOW** | **NO** | Continue routine care with regular monitoring |

> In the implemented engine, urgency is derived from the overall risk level
> (which comes from flag severity and combination rules), **not** from score
> bands. See `AI_FEATURES_README.md`.

---

## Clinical Indicators (proposal)

The proposal also envisaged these indicators:
- **High Risk**: Total confidence ≥55%
- **Medium Risk**: Total confidence 35-54%
- **Low Risk**: Total confidence <35%
- **Referral History**: Previous hospital referrals documented
- **Total Risk Factors Detected**: Number of active major risk factors

---

## Risk Factor Breakdown Display (proposal)

The proposed referral card would show:
1. **Overall Confidence Score** (percentage)
2. **Top 3 Active Risk Factors** with individual scores
3. **Sub-factors Present** for each detected risk factor
4. **Clinical Indicators** summary
5. **Recommended Facility & Specialties** (not implemented; the API returns `recommended_facility: null`)

---

## Example Output (proposal — illustrative only)

```
Referral Recommendation:
- Total Confidence: 68%
- Urgency: HIGH
- Referral Needed: YES

Top Risk Factors:
1. Pre-eclampsia/Eclampsia: 45%
2. Gestational Diabetes Mellitus: 43%
3. Anemia in Pregnancy: 30%

Clinical Indicators:
- High Risk Status: Yes
- Referral History: Yes
- Total Risk Factors Detected: 3
```

---

## Integration Points (current code)

- **Implemented rules**: `backend/app/services/advisory_rules.py` (shared by `risk_engine.py` and `ai_patient_service.py`)
- **This 10-factor framework**: not wired; no constant in code
- **API Response**: `GET /api/v1/ai-analysis/patients/{patient_id}/analysis` and `POST /api/v1/ai/risk`
- **Frontend Display**: `frontend/src/components/AIReferralRecommendation.tsx`

---

## Notes

- The implemented engine caps its referral score at 0.95 (95%) — the score is a
  sum of rule weights, not a probability (see `AI_FEATURES_README.md`).
- Everything else in this document is a proposal awaiting structured data
  capture for the listed sub-factors.
- Last updated: 2026-08-18 (status header added; clinical content unchanged).
