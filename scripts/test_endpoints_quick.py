#!/usr/bin/env python3
"""
Quick Endpoint Test - Fast testing with timeout handling
"""
import requests
import sys

BASE_URL = "https://masternoder.dk"

ENDPOINTS = [
    ("Agent Controller Status", "/vidgenerator/api/agent-controller/status"),
    ("Agent Skillset Stats", "/vidgenerator/api/agent/skillset/stats"),
    ("Agent Automation Status", "/vidgenerator/api/agent/automation/status"),
    ("User Agent Skills", "/vidgenerator/api/user/agent-skills/test_user_1"),
]

def test_endpoint(name, endpoint, timeout=5):
    """Test endpoint with short timeout"""
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(url, timeout=timeout)
        status = "✅" if response.status_code == 200 else "❌"
        print(f"{status} {response.status_code:3d} - {name}")
        if response.status_code != 200:
            print(f"      Response: {response.text[:100]}...")
        return response.status_code == 200
    except requests.exceptions.Timeout:
        print(f"⏱️  TIMEOUT - {name} (no response after {timeout}s)")
        return False
    except requests.exceptions.ConnectionError:
        print(f"🔌 CONNECTION ERROR - {name} (cannot connect)")
        return False
    except Exception as e:
        print(f"❌ ERROR - {name}: {e}")
        return False

def main():
    print("=" * 70)
    print("Quick Endpoint Test")
    print("=" * 70)
    print()
    
    results = []
    for name, endpoint in ENDPOINTS:
        success = test_endpoint(name, endpoint)
        results.append(success)
    
    print()
    print("=" * 70)
    success_count = sum(results)
    print(f"Results: {success_count}/{len(ENDPOINTS)} working")
    print("=" * 70)
    
    return 0 if success_count == len(ENDPOINTS) else 1

if __name__ == "__main__":
    sys.exit(main())
