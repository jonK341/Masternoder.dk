#!/usr/bin/env python3
"""
Test Endpoints with Timing - Check response times and headers
"""
import requests
import sys
import time

BASE_URL = "https://masternoder.dk"

ENDPOINTS = [
    ("Agent Controller Status", "/vidgenerator/api/agent-controller/status"),
    ("Agent Skillset Stats", "/vidgenerator/api/agent/skillset/stats"),
    ("Agent Automation Status", "/vidgenerator/api/agent/automation/status"),
    ("User Agent Skills", "/vidgenerator/api/user/agent-skills/test_user_1"),
]

def test_endpoint(name, endpoint):
    """Test endpoint with timing and detailed info"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*70}")
    
    try:
        start_time = time.time()
        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        })
        elapsed = time.time() - start_time
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {elapsed:.2f} seconds")
        print(f"Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
        print(f"Content-Length: {len(response.content)} bytes")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ SUCCESS")
                print(f"   JSON Keys: {list(data.keys())}")
                if 'success' in data:
                    print(f"   Success: {data['success']}")
            except:
                print(f"✅ SUCCESS (Non-JSON)")
                print(f"   Preview: {response.text[:200]}...")
            return True
        else:
            print(f"❌ FAILED - Status {response.status_code}")
            print(f"   Response: {response.text[:300]}...")
            return False
            
    except requests.exceptions.Timeout:
        print(f"⏱️  TIMEOUT - No response after 30 seconds")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"🔌 CONNECTION ERROR - {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR - {type(e).__name__}: {e}")
        return False

def main():
    print("=" * 70)
    print("Endpoint Testing with Timing")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")
    print()
    
    results = []
    for name, endpoint in ENDPOINTS:
        success = test_endpoint(name, endpoint)
        results.append(success)
        time.sleep(0.5)  # Small delay between requests
    
    print("\n" + "=" * 70)
    success_count = sum(results)
    print(f"SUMMARY: {success_count}/{len(ENDPOINTS)} endpoints working")
    print("=" * 70)
    
    if success_count == len(ENDPOINTS):
        print("\n✅ All endpoints are responding correctly!")
        print("   If you're seeing 'no returns' in browser:")
        print("   1. Check browser console (F12) for JavaScript errors")
        print("   2. Check Network tab to see actual HTTP responses")
        print("   3. Try hard refresh (Ctrl+F5)")
        print("   4. Check if JavaScript is making the requests correctly")
    else:
        print(f"\n⚠️  {len(ENDPOINTS) - success_count} endpoint(s) need attention")
    
    return 0 if success_count == len(ENDPOINTS) else 1

if __name__ == "__main__":
    sys.exit(main())
