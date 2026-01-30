"""
Quick test to force regenerate AI analysis with new simplified logic
"""
import asyncio
import sys
sys.path.append('.')

from app.core.config import Settings
from app.db.session import SessionLocal
from app.services.ai_patient_service import AIPatientService
from uuid import UUID

async def test_regenerate_analysis():
    """Test the new simplified AI analysis"""
    settings = Settings()
    db = SessionLocal()
    
    try:
        service = AIPatientService(db, settings)
        
        # Test with patient ID 1 (or adjust to the patient you're viewing)
        # You'll need to replace this with the actual UUID of your patient
        test_patient_id = "00000000-0000-0000-0000-000000000001"  # Adjust this UUID
        
        print("🔄 Force regenerating AI analysis with new simplified logic...")
        analysis = await service.get_or_generate_analysis(
            UUID(test_patient_id), 
            force_regenerate=True
        )
        
        if analysis:
            print("✅ Analysis generated successfully!")
            print(f"📊 Summary: {analysis.summary[:100]}...")
            print(f"🎯 Risk Level: {analysis.summary_metadata.get('risk_level') if analysis.summary_metadata else 'Unknown'}")
            print(f"🔍 Referral needed: {analysis.referral_needed}")
            print(f"📈 Confidence: {analysis.referral_confidence * 100:.1f}%" if analysis.referral_confidence else "No confidence data")
            print(f"⚡ Key findings: {len(analysis.summary_metadata.get('key_findings', []))} items" if analysis.summary_metadata else "No findings data")
        else:
            print("❌ Failed to generate analysis")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_regenerate_analysis())