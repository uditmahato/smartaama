# backend/app/services/risk_engine.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.validators import validate_advisory_language  # to be implemented next (currently empty file)
from app.models.clinical_event import ClinicalEvent
from app.models.patient import Patient
from app.schemas.ai import (
    AdvisoryRiskRecommendation,
    AiRiskRequest,
    GuidelineCitation,
    RiskFactorEvidence,
)
from app.services.ai_rag_service import AiRagService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class _LatestEvent:
    section: str
    factor: str
    value: Dict[str, Any]
    event_time: datetime
    note: Optional[str]
    referral_id: Optional[UUID]
    event_id: UUID


class RiskEngine:
    """
    Deterministic, explainable risk scaffold.

    IMPORTANT:
    - This does NOT make autonomous decisions.
    - It provides advisory risk level + suggested actions + explicit evidence.
    - Extend heuristics carefully to match Nepal maternal health standards/guidelines.
    """

    def __init__(self, rag: Optional[AiRagService] = None):
        self._rag = rag or AiRagService()

    def assess(self, db: Session, request: AiRiskRequest) -> AdvisoryRiskRecommendation:
        patient = db.get(Patient, request.patient_id)
        if not patient:
            raise ValueError("Patient not found")

        latest = self._get_latest_events(db, request.patient_id)

        # Apply simple baseline heuristics (transparent and conservative)
        risk_level, actions, flags, explanation_lines = self._apply_heuristics(latest)

        # Build evidence list from flagged factors (if any)
        evidence: List[RiskFactorEvidence] = []
        for sec, fac in flags:
            ev = latest.get((sec, fac))
            if not ev:
                continue
            evidence.append(
                RiskFactorEvidence(
                    section=ev.section,
                    factor=ev.factor,
                    observed_value=ev.value,
                    event_time=ev.event_time,
                    note=ev.note,
                )
            )

        # Compose explanation (always required)
        explanation = "\n".join(explanation_lines).strip()
        if not explanation:
            explanation = (
                "No high-risk signals were detected in the available recorded data. "
                "This assessment is limited by data completeness and recency."
            )

        # Referral recommendation rule (conservative)
        referral_recommended, referral_urgency, referral_reason = self._referral_logic(risk_level, flags)

        # RAG enrichment (citations and guideline support)
        citations: List[GuidelineCitation] = []
        if self._rag:
            citations = self._rag.get_guideline_citations(
                patient_id=request.patient_id,
                latest_events=[e for e in latest.values()],
                flags=flags,
                clinical_question=request.clinical_question,
            )

        summary = self._build_summary(risk_level, flags, request.clinical_question)

        rec = AdvisoryRiskRecommendation(
            overall_risk_level=risk_level,
            summary=summary,
            recommended_actions=actions,
            referral_recommended=referral_recommended,
            referral_urgency=referral_urgency,
            referral_reason=referral_reason,
            explanation=explanation,
            evidence=evidence,
            citations=citations,
        )

        # Ensure advisory language (no autonomous/imperative clinical decision)
        validate_advisory_language(rec.explanation)
        for a in rec.recommended_actions:
            validate_advisory_language(a)
        if rec.referral_reason:
            validate_advisory_language(rec.referral_reason)

        return rec

    def _get_latest_events(self, db: Session, patient_id: UUID) -> Dict[Tuple[str, str], _LatestEvent]:
        """
        Return latest (by event_time, then created_at) event for each (section, factor).
        """
        stmt = (
            select(ClinicalEvent)
            .where(ClinicalEvent.patient_id == patient_id)
            .order_by(ClinicalEvent.event_time.asc(), ClinicalEvent.created_at.asc())
        )

        latest: Dict[Tuple[str, str], _LatestEvent] = {}
        for ev in db.execute(stmt).scalars().all():
            key = (ev.section, ev.factor)
            latest[key] = _LatestEvent(
                section=ev.section,
                factor=ev.factor,
                value=ev.value or {},
                event_time=ev.event_time,
                note=ev.note,
                referral_id=ev.referral_id,
                event_id=ev.id,
            )
        return latest

    def _apply_heuristics(
        self, latest: Dict[Tuple[str, str], _LatestEvent]
    ) -> Tuple[str, List[str], List[Tuple[str, str]], List[str]]:
        """
        Minimal baseline heuristics using common maternal risk signals.
        These are intentionally conservative and should be aligned to Nepal guidelines as you add sources.

        Returns:
            risk_level: low|moderate|high|critical
            actions: advisory actions
            flags: list of (section,factor) used as evidence
            explanation_lines: explainable narrative lines
        """
        flags: List[Tuple[str, str]] = []
        actions: List[str] = []
        explain: List[str] = []

        def get_num(sec: str, fac: str) -> Optional[float]:
            ev = latest.get((sec, fac))
            if not ev:
                return None
            v = ev.value.get("value")
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        def flag(sec: str, fac: str, line: str) -> None:
            flags.append((sec, fac))
            explain.append(line)

        # Example: BP heuristic (vitals)
        sys_bp = get_num("vitals", "bp_systolic")
        dia_bp = get_num("vitals", "bp_diastolic")
        if sys_bp is not None and sys_bp >= 160:
            flag("vitals", "bp_systolic", f"Observed systolic BP {sys_bp} suggests severe hypertension.")
        if dia_bp is not None and dia_bp >= 110:
            flag("vitals", "bp_diastolic", f"Observed diastolic BP {dia_bp} suggests severe hypertension.")
        if (sys_bp is not None and sys_bp >= 140) or (dia_bp is not None and dia_bp >= 90):
            actions.append(
                "Consider evaluation for hypertensive disorders of pregnancy and confirm BP with repeat measurements."
            )

        # Example: Hemoglobin heuristic (lab_investigations)
        hb = get_num("lab_investigations", "hemoglobin")
        if hb is not None and hb < 7.0:
            flag("lab_investigations", "hemoglobin", f"Hemoglobin {hb} suggests severe anemia.")
            actions.append("Consider urgent assessment and management for severe anemia per local protocol.")
        elif hb is not None and hb < 11.0:
            flag("lab_investigations", "hemoglobin", f"Hemoglobin {hb} suggests anemia.")
            actions.append("Consider anemia workup and supplementation per ANC guidance.")

        # Example: Proteinuria heuristic (urine_investigations)
        protein = latest.get(("urine_investigations", "proteinuria"))
        if protein:
            pv = str(protein.value.get("value", "")).strip().lower()
            if pv in {"+", "++", "+++", "positive"}:
                flag("urine_investigations", "proteinuria", f"Urine protein result '{pv}' may indicate proteinuria.")
                actions.append("Consider correlating proteinuria with blood pressure and symptoms to assess preeclampsia risk.")

        # Example: Danger signs (present_pregnancy)
        danger = latest.get(("present_pregnancy", "danger_signs"))
        if danger:
            dv = danger.value.get("value")
            # Could be array/object; keep flexible
            danger_text = dv if isinstance(dv, str) else str(dv)
            if danger_text and danger_text != "[]":
                flag("present_pregnancy", "danger_signs", "Recorded danger signs warrant clinician review and possible escalation.")
                actions.append("Consider focused assessment of reported danger signs and escalation if indicated.")

        # Risk level determination (simple)
        risk_level = "low"
        severe_bp = (sys_bp is not None and sys_bp >= 160) or (dia_bp is not None and dia_bp >= 110)
        severe_anemia = hb is not None and hb < 7.0

        if severe_bp or severe_anemia:
            risk_level = "high"
        elif len(flags) >= 2:
            risk_level = "moderate"

        if severe_bp and protein:
            # combined severe HTN + proteinuria => potentially critical
            pv = str(protein.value.get("value", "")).strip().lower()
            if pv in {"+", "++", "+++", "positive"}:
                risk_level = "critical"
                actions.append("Consider urgent referral evaluation due to possible severe preeclampsia features.")

        if not flags:
            explain.append(
                "Available recorded data did not trigger baseline risk heuristics. "
                "This does not exclude risk; ensure ANC completeness and recency of vitals/investigations."
            )

        # Ensure we do not over-prescribe; keep language advisory
        actions = [a.strip() for a in actions if a.strip()]
        return risk_level, actions, flags, explain

    def _referral_logic(
        self, risk_level: str, flags: List[Tuple[str, str]]
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Conservative referral suggestion logic.
        """
        if risk_level == "critical":
            return True, "immediate", "Consider immediate referral based on combined high-risk findings."
        if risk_level == "high":
            return True, "urgent", "Consider early referral to higher-level facility for further evaluation and management."
        if risk_level == "moderate":
            return False, "routine", "Referral may be considered depending on clinical assessment and available services."
        return False, None, None

    def _build_summary(self, risk_level: str, flags: List[Tuple[str, str]], question: Optional[str]) -> str:
        if question:
            return f"Advisory risk assessment focused on: {question}. Overall risk level estimated as {risk_level}."
        if flags:
            return f"Advisory risk assessment identified {len(flags)} flagged data points. Overall risk level estimated as {risk_level}."
        return f"Advisory risk assessment completed. Overall risk level estimated as {risk_level}."
