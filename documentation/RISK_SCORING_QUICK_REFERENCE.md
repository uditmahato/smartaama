# Quick Reference: Maternal Health Risk Factors

## The 10 Major Risk Categories

| # | Risk Factor | Weight | Key Sub-factors | Total Sub-factors |
|---|------------|--------|-----------------|-------------------|
| 1 | Pre-eclampsia/Eclampsia | 10% | High BP, Obesity, Primigravida, Edema | 11 |
| 2 | Placenta Previa | 10% | Multiple gestation, Bleeding, Age >35 | 7 |
| 3 | Abruptio Placenta | 10% | Trauma, High BP, High parity | 9 |
| 4 | Gestational Diabetes | 10% | Family DM history, Obesity, Age >30 | 7 |
| 5 | Preterm Birth | 10% | Multiple gestation, Prior preterm, Infection | 8 |
| 6 | Postpartum Hemorrhage | 10% | Grand multipara, Large baby, Anemia | 15 |
| 7 | Recurrent Pregnancy Loss | 10% | Advanced age, Uterine anomaly, DM | 9 |
| 8 | Anemia in Pregnancy | 10% | Low Hb, Short spacing, Iron tablets | 4 |
| 9 | Obstructed/Prolonged Labor | 10% | Short height, Malpresentation, Obesity | 12 |
| 10 | Maternal Sepsis | 10% | Unhygienic delivery, Fever, Prolonged ROM | 9 |

---

## Quick Scoring Formula

$$\text{Total Confidence} = \sum_{i=1}^{10} \left( 0.10 \times \frac{\text{Sub-factors Present}_i}{\text{Total Sub-factors}_i} \right)$$

**Capped at 95% maximum**

---

## Confidence Ranges at a Glance

```
100% ├─────────────────────────────────────┤
      │                                     │
 95%  ├──── CRITICAL (≥75%) ────┤
      │      Immediate Referral │ Max 95%
 75%  ├────────────────────────┤
      │                        │
      │  HIGH (55-74%)         │
 55%  ├─── Urgent Referral ────┤
      │                        │
      │  MEDIUM (35-54%)       │
 35%  ├─ Consider Referral ────┤
      │                        │
      │  LOW (15-34%)          │
 15%  ├─ Monitor Closely ──────┤
      │                        │
  0%  ├────────────────────────┤ NO Referral
      │  None Detected (<15%)  │
```

---

## Decision Flowchart

```
Patient presents with clinical data
           ↓
    Analyze 10 risk factors
           ↓
    Calculate sub-factor matches
           ↓
    Compute total confidence score
           ↓
     Is Confidence ≥ 75%?
    ↙ YES              NO ↘
  CRITICAL          Is ≥ 55%?
   Urgent           ↙ YES  NO ↘
  Referral        HIGH      Is ≥ 35%?
                 Urgent    ↙ YES  NO ↘
                Referral  MEDIUM   Is ≥ 15%?
                          Refer   ↙ YES  NO ↘
                        Facility  LOW    SAFE
                       Evaluate  Monitor Routine
                                 Care   Care
```

---

## Real-World Examples

### Example 1: Young, Healthy Primigravida
- 1st pregnancy, Age 24, No medical history
- BP: 110/70, Hb: 12, BMI: 23
- **Active Risk Factors**: 0/10
- **Confidence**: 0% → **No referral needed**

### Example 2: Older Gravida with Hypertension
- Age 38, 2nd pregnancy, Known HTN
- BP: 145/95, Hb: 10.5, Edema present
- **Active Risk Factors**: Pre-eclampsia (50%), Anemia (25%)
- **Confidence**: ~7.5% → **Monitor closely**

### Example 3: High-Risk Multipara
- Age 40, 6th pregnancy, Twins, History of PPH
- BP: 150/100, Hb: 8.5, BMI: 31, Edema severe
- **Active Risk Factors**: Pre-eclampsia (45%), Anemia (25%), PPH (33%), Recurrent Loss (22%)
- **Confidence**: ~31% → **Refer to tertiary facility**

### Example 4: Critical Case
- Age 25, 1st pregnancy, Diabetic, Multiple gestation, Severe HTN
- BP: 160/110, Symptoms: headache, vision changes
- **Active Risk Factors**: Pre-eclampsia (70%), GDM (43%), Preterm (25%), Anemia (25%)
- **Confidence**: ~41% → **Urgent evaluation**
- **With critical signs** → **CRITICAL urgency override**

---

## How to Read the Output

### What You'll See

```
AI Referral Solution

┌─────────────────────────────────────┐
│ ✓ Referral Recommended              │
│ URGENCY: HIGH                       │
│ CONFIDENCE: 62%                     │
└─────────────────────────────────────┘

Reasons for Recommendation:
• Pre-eclampsia/Eclampsia: 45% risk
• Anemia in Pregnancy: 30% risk
• Gestational Diabetes Mellitus: 14% risk

Clinical Indicators:
├─ High Risk: YES
├─ Medium Risk: NO
├─ Low Risk: NO
└─ Total Risk Factors: 3

Risk Factors Analysis:
├─ Pre-eclampsia/Eclampsia
│  └─ Sub-factors Present: 5 of 11
├─ Anemia in Pregnancy
│  └─ Sub-factors Present: 3 of 4
└─ Gestational Diabetes
   └─ Sub-factors Present: 2 of 7
```

### What Each Part Means

- **Referral Recommended/Not Needed**: Clear yes/no decision
- **Urgency Level**: CRITICAL → HIGH → MEDIUM → LOW
- **Confidence %**: 0-95%, how confident the AI is
- **Reasons**: Top 3 risk factors contributing to score
- **Clinical Indicators**: Risk category summary
- **Risk Factors Analysis**: Detailed breakdown of each factor

---

## Troubleshooting

### Q: Why is confidence so low even though patient seems high-risk?
**A**: The system matches sub-factors precisely. A patient might have pre-eclampsia **symptoms** but not match the exact sub-factors. Manually verify clinical judgment.

### Q: Why is confidence high for a seemingly low-risk patient?
**A**: The system may have detected multiple sub-factors even if subtle. Review the "Risk Factors Analysis" section to see what was matched.

### Q: Can I override the AI recommendation?
**A**: **YES** - The AI is a decision support tool, not a mandate. Clinical judgment always prevails. If you think referral is needed, refer anyway.

### Q: How often should I regenerate the analysis?
**A**: 
- After new clinical events are recorded
- At each antenatal visit
- If maternal condition changes
- Before discharge decisions

---

## Key Takeaways

✅ Each major risk factor = 10% of total score
✅ Sub-factors divide that 10% equally  
✅ Only detected sub-factors count
✅ Total capped at 95% (never 100%)
✅ < 15% = safe, ≥ 75% = critical
✅ Always use clinical judgment first
✅ AI is a support tool, not a decision maker

---

## Contact & Updates

For questions about the scoring system:
- Review: `MATERNAL_RISK_SCORING_FRAMEWORK.md`
- Implementation: `AI_RISK_SCORING_IMPLEMENTATION.md`
- Code: `app/services/ai_patient_service.py`

**Last Updated**: January 31, 2026
**Version**: 1.0
**Status**: Production Ready
