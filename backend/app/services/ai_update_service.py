# backend/app/services/ai_update_service.py

"""
Service to handle automatic AI analysis updates when patient data changes.
"""

import logging
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.ai_patient_analysis import AIPatientAnalysis

logger = logging.getLogger(__name__)


def mark_ai_analysis_for_update(db: Session, patient_id: UUID) -> None:
    """
    Mark AI analysis for update by deleting it.
    It will be regenerated on next access.
    
    Call this whenever patient data changes (clinical events, referrals, etc.)
    """
    try:
        # Delete existing analysis - it will be regenerated on next access
        stmt = delete(AIPatientAnalysis).where(AIPatientAnalysis.patient_id == patient_id)
        result = db.execute(stmt)
        
        if result.rowcount > 0:
            logger.info(f"Marked AI analysis for patient {patient_id} for regeneration")
        
        # Note: We don't commit here - let the calling function handle commit
        # so it's part of the same transaction
        
    except Exception as e:
        logger.error(f"Error marking AI analysis for update: {e}")
        # Don't raise - this is a non-critical operation


def trigger_ai_analysis_background(patient_id: UUID) -> None:
    """
    Trigger background AI analysis generation.
    
    TODO: Implement with Celery or FastAPI BackgroundTasks
    For now, this is a placeholder for future async processing.
    """
    # This would queue a background task to regenerate AI analysis
    # Example with Celery:
    # from app.background.tasks import generate_ai_analysis
    # generate_ai_analysis.delay(patient_id)
    
    logger.info(f"Would trigger background AI analysis for patient {patient_id}")
