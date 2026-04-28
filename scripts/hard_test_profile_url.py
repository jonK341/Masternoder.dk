#!/usr/bin/env python3
"""
Hard Test Profile URL
Comprehensive testing of profile page, plugins, and API endpoints.

  python scripts/hard_test_profile_url.py
  BASE_URL=https://masternoder.dk PROFILE_TEST_TIMEOUT=45 python scripts/hard_test_profile_url.py
  BASE_URL=http://127.0.0.1:5000 python scripts/hard_test_profile_url.py   # local (run.py on 5000)
"""
import os
import time
import requests
import json
from datetime import datetime

BASE_URL = os.environ.get("BASE_URL", "https://masternoder.dk").rstrip("/")
# Production endpoints can be slow; use PROFILE_TEST_TIMEOUT (default 30 for production, 15 local)
_default_timeout = 30 if "masternoder.dk" in BASE_URL else 15
TIMEOUT = int(os.environ.get("PROFILE_TEST_TIMEOUT", str(_default_timeout)))
RETRIES = int(os.environ.get("PROFILE_TEST_RETRIES", "2"))
RETRY_DELAY = float(os.environ.get("PROFILE_TEST_RETRY_DELAY", "3.0"))


def request_get(url, timeout=None):
    """GET with retries on timeout/connection errors."""
    timeout = timeout if timeout is not None else TIMEOUT
    last_err = None
    for attempt in range(RETRIES + 1):
        try:
            return requests.get(url, timeout=timeout)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_err = e
            if attempt < RETRIES:
                time.sleep(RETRY_DELAY)
    raise last_err


def test_profile_page():
    """Test the profile page HTML"""
    print("=" * 70)
    print("HARD TESTING PROFILE URL")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"BASE_URL: {BASE_URL}  (timeout={TIMEOUT}s)")
    print()
    
    # Test 1: Profile Page HTML
    print("[1/6] Testing Profile Page HTML...")
    try:
        url = f"{BASE_URL}/vidgenerator/profile"
        response = request_get(url)
        print(f"  URL: {url}")
        print(f"  Status: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        print(f"  Size: {len(response.content)} bytes")
        
        html = response.text
        
        # Check for key indicators
        checks = {
            'backend-connector.js': 'backend-connector.js' in html,
            'ProfileManager class': 'class ProfileManager' in html,
            'loadDetailedStats method': 'loadDetailedStats' in html,
            'loadPointsStats method': 'loadPointsStats' in html,
            'Loading statistics': 'Loading statistics' in html,
            'initProfileManager': 'initProfileManager' in html,
            'getStats': 'getStats' in html,
        }
        
        print("\n  Key Indicators:")
        for check, found in checks.items():
            status = "[OK]" if found else "[MISS]"
            print(f"    {status} {check}: {found}")
        
        # Check cache version
        if 'cache-version' in html:
            import re
            cache_match = re.search(r'cache-version["\']?\s*content=["\']?([^"\'>\s]+)', html)
            if cache_match:
                print(f"\n  Cache Version: {cache_match.group(1)}")
        
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
    
    print()
    
    # Test 2: Backend Connector JS
    print("[2/6] Testing Backend Connector JS...")
    try:
        url = f"{BASE_URL}/vidgenerator/static/js/backend-connector.js"
        response = request_get(url)
        print(f"  URL: {url}")
        print(f"  Status: {response.status_code}")
        print(f"  Size: {len(response.content)} bytes")
        
        js = response.text
        
        checks = {
            'getStats method': 'async getStats' in js or 'getStats(userId' in js,
            'getUserProfileDisplay': 'getUserProfileDisplay' in js,
            'fetchAPI method': 'async fetchAPI' in js or 'fetchAPI(endpoint' in js,
            'error handling': 'response.ok' in js and 'response.status' in js,
            'points/all endpoint': '/points/all' in js,
        }
        
        print("\n  Key Indicators:")
        for check, found in checks.items():
            status = "[OK]" if found else "[MISS]"
            print(f"    {status} {check}: {found}")
        
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
    
    print()
    
    # Test 3: Stats Summary Endpoint
    print("[3/6] Testing Stats Summary Endpoint...")
    try:
        url = f"{BASE_URL}/vidgenerator/api/stats/summary?user_id=default_user"
        response = request_get(url)
        print(f"  URL: {url}")
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  Response: {json.dumps(data, indent=2)[:200]}...")
                if data.get('success'):
                    print("  [OK] Endpoint returns success")
                else:
                    print(f"  [WARN] Endpoint returns success=false: {data.get('error')}")
            except:
                print(f"  [WARN] Response is not JSON: {response.text[:200]}")
        else:
            print(f"  [FAIL] Status {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
    
    print()
    
    # Test 4: Game Stats Endpoint
    print("[4/6] Testing Game Stats Endpoint...")
    try:
        url = f"{BASE_URL}/vidgenerator/api/game/stats?user_id=default_user"
        response = request_get(url)
        print(f"  URL: {url}")
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  Response: {json.dumps(data, indent=2)[:200]}...")
                if data.get('success'):
                    print("  [OK] Endpoint returns success")
            except:
                print(f"  [WARN] Response is not JSON: {response.text[:200]}")
        else:
            print(f"  [FAIL] Status {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
    
    print()
    
    # Test 5: Battle Stats Endpoint
    print("[5/6] Testing Battle Stats Endpoint...")
    try:
        url = f"{BASE_URL}/vidgenerator/api/battle/stats?user_id=default_user"
        response = request_get(url)
        print(f"  URL: {url}")
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  Response: {json.dumps(data, indent=2)[:200]}...")
                if data.get('success'):
                    print("  [OK] Endpoint returns success")
            except:
                print(f"  [WARN] Response is not JSON: {response.text[:200]}")
        else:
            print(f"  [FAIL] Status {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
    
    print()
    
    # Test 6: User Profile Stats Endpoint
    print("[6/6] Testing User Profile Stats Endpoint...")
    try:
        url = f"{BASE_URL}/vidgenerator/api/user/profile/default_user/stats"
        response = request_get(url)
        print(f"  URL: {url}")
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  Response: {json.dumps(data, indent=2)[:200]}...")
                if data.get('success'):
                    print("  [OK] Endpoint returns success")
                    if data.get('stats'):
                        print(f"  Stats keys: {list(data.get('stats', {}).keys())}")
            except:
                print(f"  [WARN] Response is not JSON: {response.text[:200]}")
        else:
            print(f"  [FAIL] Status {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
    
    print()
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print()
    print("If production times out, test locally (with python run.py on port 5000):")
    print("  BASE_URL=http://127.0.0.1:5000 python scripts/hard_test_profile_url.py")
    print()

if __name__ == '__main__':
    test_profile_page()
