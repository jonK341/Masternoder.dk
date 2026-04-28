#!/usr/bin/env python3
"""
Test Slå functionality - POST request to rettigheder API
"""

import requests
import urllib3
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://masternoder.dk/vidgenerator"

def test_slaa():
    """Test Slå functionality"""
    print("=" * 70)
    print("Testing Slå Functionality")
    print("=" * 70)
    print()
    
    # Test data
    test_rettigheder = ["Musik", "TV", "Sex"]
    
    print(f"Testing with rettigheder: {test_rettigheder}")
    print()
    
    # Test POST to /api/rettigheder/slaa
    url = BASE_URL + "/api/rettigheder/slaa"
    
    try:
        response = requests.post(
            url,
            json={"rettigheder": test_rettigheder},
            headers={"Content-Type": "application/json"},
            timeout=10,
            verify=False
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ POST request successful!")
            print()
            print("Response:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            if data.get('success'):
                print()
                print(f"✅ {data.get('message', 'Rettigheder slået')}")
                print(f"   Rettigheder processed: {len(data.get('rettigheder', []))}")
            else:
                print()
                print(f"⚠️  Request succeeded but returned success=False")
                if 'error' in data:
                    print(f"   Error: {data['error']}")
        elif response.status_code == 405:
            print("⚠️  Method Not Allowed - endpoint exists but may need different method")
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 70)
    print("Test Complete")
    print("=" * 70)

if __name__ == '__main__':
    test_slaa()

