# backend/app/api/v1/api_router.py

from app.api.v1.endpoints import (
    admin,
    ai_analysis,
    ai_risk,
    auth,
    clinical_events,
    facilities,
    locations,
    medical_data,
    medical_schema,
    patients,
    referrals,
)
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(admin.router, prefix="/admin")
api_router.include_router(patients.router, prefix="/patients", tags=["Patients"])
api_router.include_router(clinical_events.router, prefix="/events", tags=["Clinical Events"])
api_router.include_router(referrals.router, prefix="/referrals", tags=["Referrals"])
api_router.include_router(ai_risk.router, prefix="/ai", tags=["AI Risk"])
api_router.include_router(ai_analysis.router, prefix="/ai-analysis", tags=["AI Analysis"])
api_router.include_router(medical_schema.router, prefix="/schema", tags=["Medical Schema"])
api_router.include_router(medical_data.router, prefix="/medical-data", tags=["Medical Data"])
api_router.include_router(locations.router)
api_router.include_router(facilities.router)
