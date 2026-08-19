# backend/app/services/ai_update_service.py

"""
Invalidation of the stored advisory analysis when patient data changes.

`mark_ai_analysis_for_update(db, patient_id)` is called from every clinical
write path (events, medical-data, referrals). It deletes the cached
`AIPatientAnalysis` row inside the caller's transaction; the analysis is
regenerated on the next generation request (see endpoints/ai_analysis.py).
"""

import logging
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.ai_patient_analysis import AIPatientAnalysis

logger = logging.getLogger(__name__)


def mark_ai_analysis_for_update(db: Session, patient_id: UUID) -> None:
    """
    Invalidate the stored advisory analysis for a patient by deleting it.
    It will be regenerated on the next generation request.

    Does NOT commit: the caller owns the transaction so the invalidation is
    atomic with the clinical write. Never raises (best-effort, non-critical).
    """
    try:
        stmt = delete(AIPatientAnalysis).where(AIPatientAnalysis.patient_id == patient_id)
        result = db.execute(stmt)
        if result.rowcount and result.rowcount > 0:
            logger.info("Invalidated advisory analysis for patient %s", patient_id)
    except Exception as e:  # pragma: no cover - defensive
        logger.error("Error invalidating advisory analysis for patient %s: %s", patient_id, e)


__all__ = ["mark_ai_analysis_for_update"]
