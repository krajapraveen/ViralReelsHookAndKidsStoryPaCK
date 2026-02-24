import requests
import time
import json

# Test the story generation we just started
base_url = "https://backend-rebuild-8.preview.emergentagent.com"
token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJhZG1pbkBjcmVhdG9yc3R1ZGlvLmFpIiwiaWF0IjoxNzcxMDg2Mjc3LCJleHAiOjE3NzExNzI2Nzd9.hi5TyWzP5gG-q3q5uk3eL2GSRXDMxPabQimZWjC_RxQ"
generation_id = "436d6b6f-43c3-4741-8072-496c9ea63a8d"

headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
}

print("🔍 Checking story generation status...")

# Check generation status
try:
    response = requests.get(f"{base_url}/api/generate/generations/{generation_id}", headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Generation Status: {result.get('status', 'Unknown')}")
        if result.get('outputJson'):
            output = result['outputJson']
            print(f"Story Title: {output.get('title', 'No title')}")
            print(f"Story Synopsis: {output.get('synopsis', 'No synopsis')[:100]}...")
            print(f"Number of scenes: {len(output.get('scenes', []))}")
        else:
            print("No output yet")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Error checking status: {e}")

print("\n🔍 Testing other endpoints...")

# Test admin endpoints
try:
    response = requests.get(f"{base_url}/api/admin/stats", headers=headers, timeout=10)
    print(f"Admin Stats: {response.status_code}")
    if response.status_code == 200:
        print(f"Admin data available: {list(response.json().keys())}")
except Exception as e:
    print(f"Admin stats error: {e}")

# Test payments endpoints
try:
    response = requests.get(f"{base_url}/api/payments/products", headers=headers, timeout=10)
    print(f"Payment Products: {response.status_code}")
    if response.status_code == 200:
        products = response.json()
        print(f"Found {len(products)} products")
except Exception as e:
    print(f"Payment products error: {e}")

# Test history endpoints
try:
    response = requests.get(f"{base_url}/api/credits/ledger", headers=headers, timeout=10)
    print(f"Credits Ledger: {response.status_code}")
    if response.status_code == 200:
        ledger = response.json()
        print(f"Ledger entries: {len(ledger.get('content', []))}")
except Exception as e:
    print(f"Credits ledger error: {e}")

print("\n✅ Backend API testing completed")