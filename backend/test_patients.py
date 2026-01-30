import requests
import json

# First, let's see what patients exist
print("🔍 Checking available patients...")
try:
    response = requests.get("http://localhost:8000/api/v1/patients?limit=10")
    print(f"✅ Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        patients = data.get('items', [])
        print(f"\n📊 Found {len(patients)} patients:")
        for patient in patients:
            print(f"- ID: {patient['id']}, Name: {patient.get('first_name', 'Unknown')} {patient.get('last_name', '')}")
            
        if patients:
            # Test with the first patient
            patient_id = patients[0]['id']
            print(f"\n🔄 Testing AI API with patient ID: {patient_id}")
            
            url = f"http://localhost:8000/api/v1/ai-analysis/patients/{patient_id}/analysis?force_regenerate=true"
            response = requests.get(url)
            print(f"✅ AI Analysis Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("\n📊 New AI Analysis Response:")
                print(json.dumps(data, indent=2))
            else:
                print(f"❌ AI Analysis Error: {response.text}")
    else:
        print(f"❌ Error getting patients: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")