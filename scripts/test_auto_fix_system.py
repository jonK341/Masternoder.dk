#!/usr/bin/env python3
"""
Test Auto-Fix System
Tests the auto-fix endpoint system
"""
import requests
import time
from datetime import datetime

BASE_URL = "https://masternoder.dk"

def test_auto_fix():
    """Test the auto-fix system"""
    print("=" * 70)
    print("TESTING AUTO-FIX ENDPOINT SYSTEM")
    print("=" * 70)
    print()
    
    # Test endpoints that should trigger auto-fix
    test_endpoints = [
        '/vidgenerator/api/test/missing/endpoint',
        '/vidgenerator/api/test/another/endpoint',
        '/vidgenerator/api/stats/test',
        '/vidgenerator/api/points/test',
    ]
    
    print("[1/3] Testing missing endpoints (should auto-fix after 3 attempts)...")
    for endpoint in test_endpoints:
        url = f"{BASE_URL}{endpoint}"
        print(f"\n  Testing: {endpoint}")
        
        # First attempt - should return 404 but log it
        response1 = requests.get(url, timeout=5)
        print(f"    Attempt 1: {response1.status_code}")
        
        # Second attempt - should still return 404
        time.sleep(0.5)
        response2 = requests.get(url, timeout=5)
        print(f"    Attempt 2: {response2.status_code}")
        
        # Third attempt - should auto-fix if pattern matches
        time.sleep(0.5)
        response3 = requests.get(url, timeout=5)
        print(f"    Attempt 3: {response3.status_code}")
        
        if response3.status_code == 200:
            data = response3.json()
            if data.get('auto_fixed'):
                print(f"    ✅ Auto-fixed! Response: {data.get('message', 'N/A')}")
            else:
                print(f"    ⚠️  Returned 200 but not auto-fixed")
        else:
            print(f"    ⚠️  Still returning {response3.status_code}")
    
    print()
    print("[2/3] Checking auto-fix statistics...")
    try:
        stats_url = f"{BASE_URL}/vidgenerator/api/auto-fix/statistics"
        response = requests.get(stats_url, timeout=5)
        if response.status_code == 200:
            stats = response.json()
            print(f"  ✅ Statistics endpoint working")
            print(f"    Total fixed: {stats.get('statistics', {}).get('total_fixed', 0)}")
            print(f"    Total patterns: {stats.get('statistics', {}).get('total_patterns', 0)}")
            print(f"    Total 404s: {stats.get('statistics', {}).get('total_404s', 0)}")
        else:
            print(f"  ⚠️  Statistics endpoint returned {response.status_code}")
    except Exception as e:
        print(f"  ❌ Error checking statistics: {e}")
    
    print()
    print("[3/3] Checking fixed endpoints list...")
    try:
        endpoints_url = f"{BASE_URL}/vidgenerator/api/auto-fix/endpoints"
        response = requests.get(endpoints_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            fixed = data.get('fixed_endpoints', {})
            print(f"  ✅ Endpoints list working")
            print(f"    Total fixed endpoints: {len(fixed)}")
            if fixed:
                print(f"    Recent fixes:")
                for path, info in list(fixed.items())[:5]:
                    print(f"      - {path} ({info.get('method', 'GET')})")
        else:
            print(f"  ⚠️  Endpoints list returned {response.status_code}")
    except Exception as e:
        print(f"  ❌ Error checking endpoints: {e}")
    
    print()
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print()
    print("Note: Auto-fix triggers after endpoint is accessed 3+ times")
    print("      Check /vidgenerator/api/auto-fix/statistics for details")

if __name__ == '__main__':
    test_auto_fix()
