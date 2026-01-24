# backend/app/api/v1/api_router.py

from fastapi import APIRouter
from app.api.v1.endpoints import auth, patients, clinical_events, referrals, ai_risk, medical_schema, medical_data, locations, facilities

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(patients.router, prefix="/patients", tags=["Patients"])
api_router.include_router(clinical_events.router, prefix="/events", tags=["Clinical Events"])
api_router.include_router(referrals.router, prefix="/referrals", tags=["Referrals"])
api_router.include_router(ai_risk.router, prefix="/ai", tags=["AI Risk"])
api_router.include_router(medical_schema.router, prefix="/schema", tags=["Medical Schema"])
api_router.include_router(medical_data.router, prefix="/medical-data", tags=["Medical Data"])
api_router.include_router(locations.router)
api_router.include_router(facilities.router)
