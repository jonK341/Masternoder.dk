#!/usr/bin/env python3
"""
Test Loose Ends
Tests various loose ends and verifies fixes
"""
import requests
import json
from datetime import datetime

BASE_URL = "https://masternoder.dk"

def test_loose_ends():
    """Test loose ends and verify fixes"""
    print("=" * 70)
    print("TESTING LOOSE ENDS AND VERIFYING FIXES")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {
        'passed': [],
        'failed': [],
        'warnings': []
    }
    
    # Test 1: API endpoints return JSON on error
    print("[1/5] Testing API endpoints return JSON on error...")
    test_endpoints = [
        '/vidgenerator/api/test/nonexistent',
        '/vidgenerator/api/invalid/endpoint',
    ]
    
    for endpoint in test_endpoints:
        try:
            url = f"{BASE_URL}{endpoint}"
            response = requests.get(url, timeout=5)
            
            # Check if response is JSON
            try:
                data = response.json()
                if isinstance(data, dict):
                    results['passed'].append(f"{endpoint} returns JSON")
                    print(f"  [OK] {endpoint}: Returns JSON")
                else:
                    results['warnings'].append(f"{endpoint} returns non-dict JSON")
            except:
                # Check if it's HTML
                if response.headers.get('Content-Type', '').startswith('text/html'):
                    results['failed'].append(f"{endpoint} returns HTML instead of JSON")
                    print(f"  [FAIL] {endpoint}: Returns HTML (status {response.status_code})")
                else:
                    results['warnings'].append(f"{endpoint} returns non-JSON")
        except Exception as e:
            results['failed'].append(f"{endpoint}: {str(e)[:50]}")
    
    print()
    
    # Test 2: Placeholder endpoints return proper structure
    print("[2/5] Testing placeholder endpoints...")
    placeholder_endpoints = [
        '/vidgenerator/api/points/comprehensive?user_id=test_user',
        '/vidgenerator/api/points/statistics?user_id=test_user',
        '/vidgenerator/api/monetization/top50?user_id=test_user',
    ]
    
    for endpoint in placeholder_endpoints:
        try:
            url = f"{BASE_URL}{endpoint}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get('success') is not None:
                        results['passed'].append(f"{endpoint} returns proper structure")
                        print(f"  [OK] {endpoint}: Returns proper JSON structure")
                    else:
                        results['warnings'].append(f"{endpoint} missing 'success' field")
                except:
                    results['failed'].append(f"{endpoint} doesn't return JSON")
            else:
                results['warnings'].append(f"{endpoint} returns {response.status_code}")
        except Exception as e:
            results['failed'].append(f"{endpoint}: {str(e)[:50]}")
    
    print()
    
    # Test 3: Auto-fix system working
    print("[3/5] Testing auto-fix system...")
    try:
        url = f"{BASE_URL}/vidgenerator/api/auto-fix/statistics"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                results['passed'].append("Auto-fix statistics endpoint working")
                print(f"  [OK] Auto-fix system is active")
                stats = data.get('statistics', {})
                print(f"    Total fixed: {stats.get('total_fixed', 0)}")
            else:
                results['warnings'].append("Auto-fix endpoint returns success=false")
        else:
            results['warnings'].append(f"Auto-fix endpoint returns {response.status_code}")
    except Exception as e:
        results['failed'].append(f"Auto-fix test: {str(e)[:50]}")
    
    print()
    
    # Test 4: Error handling in frontend connector
    print("[4/5] Testing error handling...")
    # This would require checking the actual JS file, but we can test API error responses
    error_endpoints = [
        '/vidgenerator/api/user/profile/invalid_user_12345/stats',
    ]
    
    for endpoint in error_endpoints:
        try:
            url = f"{BASE_URL}{endpoint}"
            response = requests.get(url, timeout=5)
            
            # Should return JSON even on error
            try:
                data = response.json()
                if isinstance(data, dict) and 'error' in data or 'success' in data:
                    results['passed'].append(f"{endpoint} returns JSON error")
                    print(f"  [OK] {endpoint}: Returns JSON error response")
                else:
                    results['warnings'].append(f"{endpoint} returns JSON but no error field")
            except:
                results['failed'].append(f"{endpoint} doesn't return JSON on error")
        except Exception as e:
            results['failed'].append(f"{endpoint}: {str(e)[:50]}")
    
    print()
    
    # Test 5: Summary
    print("[5/5] Test Summary...")
    print()
    print("=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    print()
    print(f"[OK] Passed: {len(results['passed'])}")
    print(f"[FAIL] Failed: {len(results['failed'])}")
    print(f"[WARN] Warnings: {len(results['warnings'])}")
    print()
    
    if results['passed']:
        print("Passed Tests:")
        for test in results['passed']:
            print(f"  [OK] {test}")
        print()
    
    if results['warnings']:
        print("Warnings:")
        for test in results['warnings']:
            print(f"  [WARN] {test}")
        print()
    
    if results['failed']:
        print("Failed Tests:")
        for test in results['failed']:
            print(f"  [FAIL] {test}")
        print()
    
    print("=" * 70)
    
    return results

if __name__ == '__main__':
    test_loose_ends()
