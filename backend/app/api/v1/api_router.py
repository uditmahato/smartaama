from fastapi import APIRouter
from app.api.v1.endpoints import patients, clinical_events, referrals, ai_risk

api_router = APIRouter()

api_router.include_router(patients.router, prefix="/patients", tags=["Patients"])
api_router.include_router(clinical_events.router, prefix="/events", tags=["Clinical Events"])
api_router.include_router(referrals.router, prefix="/referrals", tags=["Referrals"])
api_router.include_router(ai_risk.router, prefix="/ai", tags=["AI Risk"])
