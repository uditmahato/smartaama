#!/usr/bin/env python
import asyncio
import sys
from uuid import UUID
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.ai_patient_service import AIPatientService

async def test_ai_service():
    db = SessionLocal()
    service = AIPatientService(db, settings)
    
    # Use the patient ID from the error message
    patient_id = UUID("adfe978f-c5e6-4ead-9edb-3e2a3c4d7195")
    
    try:
        print(f"🔄 Testing AI service for patient: {patient_id}")
        analysis = await service.get_or_generate_analysis(patient_id, force_regenerate=True)
        
        if analysis:
            print("✅ Analysis generated successfully!")
            print(f"Summary: {analysis.summary[:100] if analysis.summary else 'None'}")
            print(f"Referral Needed: {analysis.referral_needed}")
        else:
            print("❌ No analysis returned")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_ai_service())
