#!/usr/bin/env python
"""
Direct test of the AI analysis endpoint without HTTP
"""
from uuid import UUID
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models.patient import Patient
from app.models.ai_patient_analysis import AIPatientAnalysis

patient_id = UUID("adfe978f-c5e6-4ead-9edb-3e2a3c4d7195")

db = SessionLocal()
try:
    # Check if patient exists
    patient = db.execute(select(Patient).where(Patient.id == patient_id)).scalar_one_or_none()
    print(f"Patient exists: {patient is not None}")
    if patient:
        print(f"  - Name: {patient.first_name} {patient.last_name}")
        print(f"  - ID: {patient.id}")
    
    # Check if analysis exists
    analysis = db.execute(select(AIPatientAnalysis).where(AIPatientAnalysis.patient_id == patient_id)).scalar_one_or_none()
    print(f"Analysis exists: {analysis is not None}")
    
finally:
    db.close()
