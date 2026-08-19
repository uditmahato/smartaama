# backend/app/services/risk_engine.py
"""
RiskEngine: rule-based advisory assessment used by POST /ai/risk.

All thresholds and wording live in `app.services.advisory_rules`
(`evaluate_latest_values`), which is shared with `AIPatientService`
(/ai-analysis/*). This module only:
  1. loads the LATEST clinical event per (section, factor) for a patient,
  2. runs the shared rules,
  3. shapes the result into `AdvisoryRiskRecommendation` with evidence.

No LLM, no retrieval, no external calls. Outputs are advisory only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.validators import validate_advisory_language
from app.models.clinical_event import ClinicalEvent
from app.models.patient import Patient
from app.schemas.ai import AdvisoryRiskRecommendation, AiRiskRequest, RiskFactorEvidence
from app.services.advisory_rules import (
    DISCLAIMER,
    ENGINE_VERSION,
    LatestValue,
    RuleResult,
    build_summary_text,
    evaluate_latest_values,
)

FactorKey = Tuple[str, str]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _sortable(dt: Optional[datetime]) -> datetime:
    """Naive datetimes (e.g. from SQLite) are treated as UTC so they compare safely."""
    if dt is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass(frozen=True)
class LatestEvent:
    """Latest recorded clinical event for one (section, factor)."""
    section: str
    factor: str
    value: Dict[str, Any]
    event_time: datetime
    note: Optional[str]
    referral_id: Optional[UUID]
    event_id: Optional[UUID]
    created_at: Optional[datetime] = None

    @property
    def key(self) -> FactorKey:
        return (self.section, self.factor)


# Backwards-compatible alias (older code referenced the private name)
_LatestEvent = LatestEvent


def latest_per_factor(events: Iterable[Any]) -> Dict[FactorKey, LatestEvent]:
    """
    Reduce an iterable of ClinicalEvent-like objects to the latest one per
    (section, factor), ordered by event_time then created_at.

    Objects need: section, factor, value, event_time; optional: created_at, note,
    referral_id, id. Works on ORM rows and on plain objects (tests).
    """
    ordered = sorted(
        events,
        key=lambda e: (_sortable(getattr(e, "event_time", None)), _sortable(getattr(e, "created_at", None))),
    )
    latest: Dict[FactorKey, LatestEvent] = {}
    for ev in ordered:
        value = getattr(ev, "value", None)
        if not isinstance(value, dict):
            value = {"value": value}
        latest[(ev.section, ev.factor)] = LatestEvent(
            section=ev.section,
            factor=ev.factor,
            value=value,
            event_time=getattr(ev, "event_time", None),
            note=getattr(ev, "note", None),
            referral_id=getattr(ev, "referral_id", None),
            event_id=getattr(ev, "id", None),
            created_at=getattr(ev, "created_at", None),
        )
    return latest


def load_latest_events(db: Session, patient_id: UUID) -> Dict[FactorKey, LatestEvent]:
    """Query all events for a patient and reduce to latest per (section, factor)."""
    stmt = (
        select(ClinicalEvent)
        .where(ClinicalEvent.patient_id == patient_id)
        .order_by(ClinicalEvent.event_time.asc(), ClinicalEvent.created_at.asc())
    )
    return latest_per_factor(db.execute(stmt).scalars().all())


def to_latest_values(latest: Dict[FactorKey, LatestEvent]) -> Dict[FactorKey, LatestValue]:
    """Convert LatestEvent map to the pure-rule input map."""
    return {
        k: LatestValue(value=(ev.value or {}).get("value"), event_time=ev.event_time)
        for k, ev in latest.items()
    }


class RiskEngine:
    """
    Deterministic, explainable, advisory-only risk assessment.

    - Does NOT make autonomous decisions.
    - Provides a risk level + suggested actions + explicit evidence.
    - Thresholds live in `advisory_rules.THRESHOLDS`.
    """

    engine_version = ENGINE_VERSION

    def assess(self, db: Session, request: AiRiskRequest) -> AdvisoryRiskRecommendation:
        patient = db.get(Patient, request.patient_id)
        if not patient:
            raise ValueError("Patient not found")

        latest = load_latest_events(db, request.patient_id)
        return self.build_recommendation(
            latest,
            clinical_question=request.clinical_question,
            patient_age=patient.age_in_years,
        )

    def build_recommendation(
        self,
        latest: Dict[FactorKey, LatestEvent],
        *,
        clinical_question: Optional[str] = None,
        patient_age: Optional[int] = None,
    ) -> AdvisoryRiskRecommendation:
        """Pure (no DB): shape shared rule output into the /ai/risk schema."""
        result: RuleResult = evaluate_latest_values(to_latest_values(latest), patient_age=patient_age)
        evidence = self._evidence(result, latest)

        summary = build_summary_text(result, age=patient_age, event_count=len(latest))
        validate_advisory_language(summary)
        if clinical_question:
            # Clinician-supplied text is echoed, not generated; keep it separate from validated text.
            summary = f"Advisory assessment focused on: {clinical_question}. {summary}"

        explanation = "\n".join(result.explanation_lines).strip()
        if not explanation:
            explanation = (
                "No high-risk signals were detected in the available recorded data. "
                "This assessment is limited by data completeness and recency."
            )

        referral_reason = result.referral_reasons[0] if result.referral_reasons else None

        rec = AdvisoryRiskRecommendation(
            overall_risk_level=result.risk_level,
            summary=summary,
            recommended_actions=list(result.actions),
            referral_recommended=result.referral_recommended,
            referral_urgency=result.referral_urgency,
            referral_reason=referral_reason,
            referral_reasons=list(result.referral_reasons),
            referral_score=result.referral_score,
            explanation=explanation,
            evidence=evidence,
            citations=[],
            engine=ENGINE_VERSION,
            safety_note=DISCLAIMER,
        )

        # Guardrail: advisory language on everything the engine generated
        validate_advisory_language(rec.explanation)
        for a in rec.recommended_actions:
            validate_advisory_language(a)
        for r in rec.referral_reasons:
            validate_advisory_language(r)
        return rec

    @staticmethod
    def _evidence(result: RuleResult, latest: Dict[FactorKey, LatestEvent]) -> List[RiskFactorEvidence]:
        evidence: List[RiskFactorEvidence] = []
        for f in result.flags:
            ev = latest.get(f.key)
            evidence.append(
                RiskFactorEvidence(
                    section=f.section,
                    factor=f.factor,
                    observed_value=ev.value if ev else {"value": f.observed},
                    event_time=ev.event_time if ev else None,
                    note=ev.note if ev else None,
                    code=f.code,
                    severity=f.severity,
                    domain=f.domain,
                    finding=f.finding,
                )
            )
        return evidence


__all__ = [
    "LatestEvent",
    "RiskEngine",
    "latest_per_factor",
    "load_latest_events",
    "to_latest_values",
]
