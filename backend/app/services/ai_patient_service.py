# backend/app/services/ai_patient_service.py

"""
Advisory Patient Analysis Service (rule-based, no LLM).

Produces the summary + referral suggestion shown on the patient profile
(/ai-analysis/*). All clinical thresholds and wording come from the shared
pure rule module `app.services.advisory_rules` (`evaluate_latest_values`),
which is the same function used by `RiskEngine` (POST /ai/risk).

Only the LATEST recorded value per (section, factor) is evaluated, so an old
abnormal reading followed by a newer normal one no longer flags.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.ai.validators import validate_advisory_language
from app.models.ai_patient_analysis import AIPatientAnalysis
from app.models.clinical_event import ClinicalEvent
from app.models.patient import Patient
from app.models.referral import Referral
from app.schemas.ai_analysis import AIPatientSummary, AIReferralRecommendation
from app.services.advisory_rules import (
    DISCLAIMER,
    ENGINE_VERSION,
    RISK_UNKNOWN,
    SEV_WARNING,
    RuleResult,
    build_summary_text,
    evaluate_latest_values,
)
from app.services.risk_engine import FactorKey, LatestEvent, latest_per_factor, to_latest_values

logger = logging.getLogger(__name__)

MAX_KEY_FINDINGS = 6
MAX_REASONS = 5


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class AIPatientService:
    """Service for generating and caching the rule-based advisory analysis."""

    engine_version = ENGINE_VERSION

    def __init__(self, db: Session, settings: Any = None):
        # `settings` is accepted for backwards compatibility and ignored: the
        # engine has no configurable external dependencies.
        self.db = db

    # ------------------------------------------------------------------ data

    def get_patient_complete_data(self, patient_id: UUID) -> Optional[Dict[str, Any]]:
        """Fetch patient demographics, all clinical events and referrals."""
        stmt = (
            select(Patient)
            .options(joinedload(Patient.clinical_events), joinedload(Patient.referrals))
            .where(Patient.id == patient_id)
        )
        patient = self.db.execute(stmt).unique().scalar_one_or_none()
        if not patient:
            return None

        return {
            "patient_id": str(patient.id),
            "demographics": {
                "name": patient.full_name,
                "age": patient.age_in_years,
                "sex": patient.sex,
                "location": {
                    "district": patient.district,
                    "province": patient.province,
                    "municipality": patient.municipality,
                },
            },
            "clinical_events": list(patient.clinical_events),
            "referrals": [
                {
                    "status": ref.status.value if hasattr(ref.status, "value") else str(ref.status),
                    "from_facility": ref.from_facility,
                    "to_facility": ref.to_facility,
                    "reason": ref.reason,
                    "created_at": ref.created_at.isoformat() if ref.created_at else None,
                }
                for ref in patient.referrals
            ],
        }

    # ------------------------------------------------------------- pure build

    @staticmethod
    def evaluate(
        events: List[Any],
        *,
        patient_age: Optional[int] = None,
    ) -> "tuple[RuleResult, Dict[FactorKey, LatestEvent]]":
        """Reduce events to latest-per-factor and run the shared rules (no DB)."""
        latest = latest_per_factor(events)
        result = evaluate_latest_values(to_latest_values(latest), patient_age=patient_age)
        return result, latest

    @staticmethod
    def build_summary(
        result: RuleResult,
        *,
        age: Optional[Any],
        event_count: int,
        referral_count: int = 0,
    ) -> AIPatientSummary:
        """Shape rule output into the summary card schema (pure)."""
        findings: List[str] = []

        # Flagged findings first (warning+ then info), then reassuring values.
        flagged = [f.finding for f in result.flags]
        findings.extend(flagged[:MAX_KEY_FINDINGS])
        remaining = MAX_KEY_FINDINGS - len(findings)
        if remaining > 0:
            findings.extend(result.normal_findings[:min(2, remaining)])

        if result.risk_level == RISK_UNKNOWN:
            if event_count > 0:
                findings.append(
                    f"Clinical entries recorded: {event_count}; none of them are values the advisory rules evaluate."
                )
            else:
                findings.append("No clinical measurements recorded yet")

        if referral_count > 0:
            findings.append(f"Referral history: {referral_count} previous referral(s)")

        summary_text = build_summary_text(result, age=age, event_count=event_count)
        for t in [summary_text] + findings:
            validate_advisory_language(t)

        return AIPatientSummary(
            summary=summary_text,
            key_findings=findings,
            risk_level=result.risk_level,
            metadata={
                "engine": ENGINE_VERSION,
                "clinical_events": event_count,
                "data_points_evaluated": result.data_points_evaluated,
                "flag_count": len(result.flags),
                "warning_or_worse_count": len(result.flags_at_least(SEV_WARNING)),
                "referrals": referral_count,
                "disclaimer": DISCLAIMER,
            },
        )

    @staticmethod
    def build_referral(result: RuleResult, *, event_count: int) -> AIReferralRecommendation:
        """Shape rule output into the referral card schema (pure)."""
        detected = [
            {
                "name": f.name,
                "weight": f.weight,
                "value": f.observed,
                "code": f.code,
                "severity": f.severity,
                "domain": f.domain,
            }
            for f in result.flags
            if f.weight > 0
        ]

        pct = round(result.referral_score * 100, 1)
        clinical_indicators: Dict[str, Any] = {
            "engine": ENGINE_VERSION,
            "risk_level": result.risk_level,
            "total_risk_factors": len(detected),
            "confidence_score": f"{pct}%",
            "referral_score_meaning": "Sum of triggered rule weights (capped at 95%); a transparency score, not a probability.",
        }
        for f in result.flags:
            clinical_indicators[f.code] = f"DETECTED: {f.observed}"

        reasons = list(result.referral_reasons[:MAX_REASONS])
        for r in reasons:
            validate_advisory_language(r)

        return AIReferralRecommendation(
            referral_needed=result.referral_recommended,
            urgency=result.referral_urgency,
            confidence=result.referral_score,
            reasons=reasons,
            recommended_facility=None,
            recommended_specialties=[],
            risk_factors={
                "detected_risks": detected,
                "confidence_calculation": f"Sum of rule weights: {pct}% (capped at 95%)",
                "data_points_analyzed": event_count,
                "data_points_evaluated": result.data_points_evaluated,
                "engine": ENGINE_VERSION,
            },
            clinical_indicators=clinical_indicators,
        )

    # -------------------------------------------------------------- persistence

    def get_existing(self, patient_id: UUID) -> Optional[AIPatientAnalysis]:
        """
        Return the stored analysis for the current rule engine only. Rows produced by any
        other engine (e.g. LLM-era rows on an upgraded database) are treated as absent and
        deleted, so stale/foreign output is never served as if it came from this engine.
        """
        stmt = select(AIPatientAnalysis).where(AIPatientAnalysis.patient_id == patient_id)
        row = self.db.execute(stmt).scalar_one_or_none()
        if row is not None and row.model_used != ENGINE_VERSION:
            logger.info(
                "Discarding stored analysis for patient %s produced by engine %r (current %r)",
                patient_id, row.model_used, ENGINE_VERSION,
            )
            self.db.delete(row)
            self.db.flush()
            return None
        return row

    def latest_data_change_at(self, patient_id: UUID) -> Optional[datetime]:
        """Most recent clinical event / referral creation time for the patient."""
        ev = self.db.execute(
            select(func.max(ClinicalEvent.created_at)).where(ClinicalEvent.patient_id == patient_id)
        ).scalar_one_or_none()
        rf = self.db.execute(
            select(func.max(Referral.created_at)).where(Referral.patient_id == patient_id)
        ).scalar_one_or_none()
        candidates = [d for d in (_as_utc(ev), _as_utc(rf)) if d is not None]
        return max(candidates) if candidates else None

    def needs_update(self, analysis: Optional[AIPatientAnalysis], patient_id: UUID) -> "tuple[bool, Optional[datetime]]":
        """
        True when no analysis is stored, or when clinical data / referrals were
        recorded after `last_analyzed_at`. Write paths also delete the stored
        row via `mark_ai_analysis_for_update`, so this is a defensive check.
        """
        last_change = self.latest_data_change_at(patient_id)
        if analysis is None:
            return True, last_change
        if last_change is None:
            return False, None
        analyzed = _as_utc(analysis.last_analyzed_at)
        return (analyzed is None or last_change > analyzed), last_change

    def get_or_generate_analysis(
        self,
        patient_id: UUID,
        force_regenerate: bool = False,
    ) -> Optional[AIPatientAnalysis]:
        """Return the stored analysis, generating (or regenerating) it if needed."""
        existing = self.get_existing(patient_id)
        if existing and not force_regenerate:
            return existing

        patient_data = self.get_patient_complete_data(patient_id)
        if not patient_data:
            logger.error("Patient %s not found", patient_id)
            return None

        events: List[Any] = patient_data["clinical_events"]
        demographics = patient_data.get("demographics", {})
        referrals = patient_data.get("referrals", [])

        result, _latest = self.evaluate(events, patient_age=demographics.get("age"))
        summary = self.build_summary(
            result, age=demographics.get("age"), event_count=len(events), referral_count=len(referrals)
        )
        referral_rec = self.build_referral(result, event_count=len(events))

        if existing:
            analysis = existing
            analysis.data_version = (analysis.data_version or 0) + 1
        else:
            analysis = AIPatientAnalysis(patient_id=patient_id)

        analysis.summary = summary.summary
        analysis.summary_metadata = {
            "key_findings": summary.key_findings,
            "risk_level": summary.risk_level,
            **(summary.metadata or {}),
        }
        analysis.referral_needed = referral_rec.referral_needed
        analysis.referral_urgency = referral_rec.urgency
        analysis.referral_confidence = referral_rec.confidence
        analysis.referral_reasons = referral_rec.reasons
        analysis.recommended_facility = referral_rec.recommended_facility
        analysis.recommended_specialties = referral_rec.recommended_specialties
        analysis.risk_factors = referral_rec.risk_factors
        analysis.clinical_indicators = referral_rec.clinical_indicators
        analysis.model_used = ENGINE_VERSION
        analysis.last_analyzed_at = _utcnow()

        if not existing:
            self.db.add(analysis)

        self.db.commit()
        self.db.refresh(analysis)
        return analysis


__all__ = ["AIPatientService"]
