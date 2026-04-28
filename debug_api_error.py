"""
Debug script to capture actual API error
"""
import requests
import json
import sys

BASE_URL = "http://localhost:5000"

print("=" * 70)
print("Debugging API 500 Error")
print("=" * 70)

# Test 1: Check if Flask is running
print("\n[1] Testing Flask health...")
try:
    r = requests.get(f"{BASE_URL}/api/generator/test", timeout=5)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        print(f"  [OK] Flask is running")
    else:
        print(f"  [FAIL] Flask returned {r.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"  [ERROR] Could not connect: {e}")
    sys.exit(1)

# Test 2: Try to create video and capture full error
print("\n[2] Attempting video creation...")
payload = {
    "title": "Debug Test Video",
    "description": "Testing API error",
    "quality": "high"
}

try:
    r = requests.post(
        f"{BASE_URL}/api/generator/create",
        json=payload,
        timeout=15,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"  Status Code: {r.status_code}")
    print(f"  Headers: {dict(r.headers)}")
    
    if r.status_code == 202:
        print(f"  [OK] Video creation started!")
        print(f"  Response: {r.json()}")
    else:
        print(f"  [ERROR] Request failed")
        print(f"  Content-Type: {r.headers.get('Content-Type')}")
        
        # Try to parse as JSON
        try:
            error_data = r.json()
            print(f"\n  Error Response (JSON):")
            print(f"  {json.dumps(error_data, indent=2)}")
        except:
            print(f"\n  Error Response (Text):")
            print(f"  {r.text[:1000]}")
            
except requests.exceptions.ConnectionError:
    print("  [ERROR] Could not connect to Flask app")
except Exception as e:
    print(f"  [ERROR] Exception: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Check if there's a simpler endpoint that works
print("\n[3] Testing other endpoints...")
endpoints = [
    "/api/generator/test",
    "/vidgenerator",
    "/api/stats/summary"
]

for endpoint in endpoints:
    try:
        r = requests.get(f"{BASE_URL}{endpoint}", timeout=5)
        status = "OK" if r.status_code == 200 else f"FAIL ({r.status_code})"
        print(f"  {endpoint}: {status}")
    except:
        print(f"  {endpoint}: ERROR")

print("\n" + "=" * 70)

