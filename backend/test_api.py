import requests
import json

# Test the new AI API with force regeneration
url = "http://localhost:8000/api/v1/ai-analysis/patients/26cd8776-d104-4cd2-bb84-e6e1c1cb1340/analysis?force_regenerate=true"

print("🔄 Testing AI API with force regeneration...")
try:
    response = requests.get(url)
    print(f"✅ Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n📊 New AI Analysis Response:")
        print(json.dumps(data, indent=2))
    else:
        print(f"❌ Error: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")