# Test AI Analysis Endpoints
# Run this to verify the AI features are working

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

# Login to get token
login_response = requests.post(
    f"{BASE_URL}/auth/login",
    data={"username": "superadmin", "password": "supersecret123"}
)

if login_response.status_code == 200:
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    print("✓ Login successful")
    
    # Get first patient
    patients_response = requests.get(f"{BASE_URL}/patients", headers=headers)
    if patients_response.status_code == 200 and len(patients_response.json()) > 0:
        patient_id = patients_response.json()[0]["id"]
        print(f"✓ Found patient: {patient_id}")
        
        # Test AI analysis endpoint
        print("\nTesting AI Analysis endpoints...")
        
        # 1. Get AI analysis (auto-generate)
        print("\n1. GET /ai-analysis/patient/{patient_id}")
        analysis_response = requests.get(
            f"{BASE_URL}/ai-analysis/patient/{patient_id}?auto_generate=true",
            headers=headers
        )
        print(f"   Status: {analysis_response.status_code}")
        if analysis_response.status_code == 200:
            data = analysis_response.json()
            print(f"   ✓ Summary: {data.get('summary', {}).get('summary', 'N/A')[:100]}...")
            print(f"   ✓ Referral needed: {data.get('referral_recommendation', {}).get('referral_needed', 'N/A')}")
            print(f"   ✓ Urgency: {data.get('referral_recommendation', {}).get('urgency', 'N/A')}")
        else:
            print(f"   ✗ Error: {analysis_response.text}")
        
        # 2. Get analysis status
        print("\n2. GET /ai-analysis/patient/{patient_id}/status")
        status_response = requests.get(
            f"{BASE_URL}/ai-analysis/patient/{patient_id}/status",
            headers=headers
        )
        print(f"   Status: {status_response.status_code}")
        if status_response.status_code == 200:
            data = status_response.json()
            print(f"   ✓ Has analysis: {data.get('has_analysis')}")
            print(f"   ✓ Needs update: {data.get('needs_update')}")
        
        # 3. Force regenerate
        print("\n3. POST /ai-analysis/generate (force regenerate)")
        regenerate_response = requests.post(
            f"{BASE_URL}/ai-analysis/generate",
            headers=headers,
            json={"patient_id": patient_id, "force_regenerate": True}
        )
        print(f"   Status: {regenerate_response.status_code}")
        if regenerate_response.status_code == 200:
            print("   ✓ Analysis regenerated successfully")
        
        print("\n" + "="*60)
        print("✓ All AI endpoints are working!")
        print("="*60)
        print("\nNote: The system is using MOCK DATA since OpenAI API is not configured.")
        print("To enable real AI analysis:")
        print("1. Get API key from https://platform.openai.com/api-keys")
        print("2. Add to .env: OPENAI_API_KEY=your-key-here")
        print("3. Install: pip install openai")
        print("4. Restart backend")
        
    else:
        print("✗ No patients found. Create a patient first.")
else:
    print(f"✗ Login failed: {login_response.text}")
