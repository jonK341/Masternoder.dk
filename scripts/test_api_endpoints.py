#!/usr/bin/env python3
"""
Test API Endpoints - Verify all agent-related endpoints are accessible
"""
import requests
import sys

BASE_URL = "https://masternoder.dk"
# BASE_URL = "http://localhost:5000"  # For local testing

ENDPOINTS_TO_TEST = [
    # Agent Controller
    "/vidgenerator/api/agent-controller/status",
    "/vidgenerator/api/agent-controller/all-agents",
    
    # Agent Skillsets
    "/vidgenerator/api/agent/skillset/stats",
    "/vidgenerator/api/agent/skillset/all",
    
    # User Agent Skills
    "/vidgenerator/api/user/agent-skills/test_user_1",
    "/vidgenerator/api/user/profile/test_user_1",
    
    # User Profile Routes
    "/vidgenerator/api/user/scraped-info/test_user_1",
]

def test_endpoint(url):
    """Test a single endpoint"""
    try:
        response = requests.get(url, timeout=10)
        status = "✅" if response.status_code == 200 else "❌"
        print(f"{status} {response.status_code:3d} - {url}")
        if response.status_code != 200:
            try:
                data = response.json()
                if 'error' in data:
                    print(f"      Error: {data.get('error', 'Unknown error')}")
            except:
                print(f"      Response: {response.text[:100]}")
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR - {url}")
        print(f"      Exception: {e}")
        return False

def main():
    """Test all endpoints"""
    print("=" * 70)
    print("API Endpoint Testing")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")
    print()
    
    success_count = 0
    total_count = len(ENDPOINTS_TO_TEST)
    
    for endpoint in ENDPOINTS_TO_TEST:
        url = f"{BASE_URL}{endpoint}"
        if test_endpoint(url):
            success_count += 1
        print()
    
    print("=" * 70)
    print(f"Results: {success_count}/{total_count} endpoints working")
    print("=" * 70)
    
    if success_count == total_count:
        print("✅ All endpoints are working!")
        return 0
    else:
        print(f"⚠️  {total_count - success_count} endpoint(s) need attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())
