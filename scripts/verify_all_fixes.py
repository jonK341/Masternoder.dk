#!/usr/bin/env python3
"""
Verify All Fixes
Comprehensive verification of all recent fixes
"""
import requests
import json
from datetime import datetime

BASE_URL = "https://masternoder.dk"

def verify_fixes():
    """Verify all fixes are working"""
    print("=" * 70)
    print("VERIFYING ALL FIXES")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {
        'verified': [],
        'failed': [],
        'warnings': []
    }
    
    # Test 1: JSON Error Handler
    print("[1/6] Testing JSON Error Handler...")
    error_endpoints = [
        ('/vidgenerator/api/test/404', 404),
        ('/vidgenerator/api/test/500', 500),
    ]
    
    for endpoint, expected_status in error_endpoints:
        try:
            url = f"{BASE_URL}{endpoint}"
            response = requests.get(url, timeout=5)
            
            # Check if response is JSON
            try:
                data = response.json()
                if isinstance(data, dict) and 'success' in data:
                    results['verified'].append(f"JSON error handler for {expected_status}")
                    print(f"  [OK] {endpoint}: Returns JSON error (status {response.status_code})")
                else:
                    results['warnings'].append(f"{endpoint} returns JSON but wrong structure")
            except:
                if response.headers.get('Content-Type', '').startswith('text/html'):
                    results['failed'].append(f"{endpoint} still returns HTML")
                    print(f"  [FAIL] {endpoint}: Still returns HTML")
                else:
                    results['warnings'].append(f"{endpoint} returns non-JSON")
        except Exception as e:
            results['failed'].append(f"{endpoint}: {str(e)[:50]}")
    
    print()
    
    # Test 2: Placeholder Endpoints
    print("[2/6] Testing Placeholder Endpoints...")
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
                data = response.json()
                if data.get('success') is not None:
                    results['verified'].append(f"Placeholder endpoint: {endpoint.split('?')[0]}")
                    print(f"  [OK] {endpoint.split('?')[0]}: Returns proper JSON")
                else:
                    results['warnings'].append(f"{endpoint} missing 'success' field")
        except Exception as e:
            results['failed'].append(f"{endpoint}: {str(e)[:50]}")
    
    print()
    
    # Test 3: Auto-Fix System
    print("[3/6] Testing Auto-Fix System...")
    try:
        url = f"{BASE_URL}/vidgenerator/api/auto-fix/statistics"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                results['verified'].append("Auto-fix system active")
                print(f"  [OK] Auto-fix system is active")
            else:
                results['warnings'].append("Auto-fix endpoint returns success=false")
        else:
            results['warnings'].append(f"Auto-fix endpoint returns {response.status_code}")
    except Exception as e:
        results['failed'].append(f"Auto-fix test: {str(e)[:50]}")
    
    print()
    
    # Test 4: Error Handling
    print("[4/6] Testing Error Handling...")
    try:
        url = f"{BASE_URL}/vidgenerator/api/user/profile/invalid_user_12345/stats"
        response = requests.get(url, timeout=5)
        
        try:
            data = response.json()
            if isinstance(data, dict) and ('error' in data or 'success' in data):
                results['verified'].append("Error handling returns JSON")
                print(f"  [OK] Error endpoint returns JSON")
            else:
                results['warnings'].append("Error endpoint returns JSON but no error field")
        except:
            results['failed'].append("Error endpoint doesn't return JSON")
    except Exception as e:
        results['failed'].append(f"Error handling test: {str(e)[:50]}")
    
    print()
    
    # Test 5: Check if files exist on server
    print("[5/6] Verifying deployed files...")
    files_to_check = [
        '/vidgenerator/static/js/backend-connector.js',
        '/vidgenerator/static/js/navigation-toolbar.js',
    ]
    
    for file_path in files_to_check:
        try:
            url = f"{BASE_URL}{file_path}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                # Check for key improvements
                if 'exponential' in response.text.lower() or 'retry' in response.text.lower():
                    results['verified'].append(f"Frontend file updated: {file_path.split('/')[-1]}")
                    print(f"  [OK] {file_path.split('/')[-1]}: Contains improvements")
                else:
                    results['warnings'].append(f"{file_path} may not have latest changes")
        except Exception as e:
            results['warnings'].append(f"{file_path}: {str(e)[:50]}")
    
    print()
    
    # Test 6: Summary
    print("[6/6] Summary...")
    print()
    print("=" * 70)
    print("VERIFICATION RESULTS")
    print("=" * 70)
    print()
    print(f"[OK] Verified: {len(results['verified'])}")
    print(f"[FAIL] Failed: {len(results['failed'])}")
    print(f"[WARN] Warnings: {len(results['warnings'])}")
    print()
    
    if results['verified']:
        print("Verified Fixes:")
        for item in results['verified']:
            print(f"  [OK] {item}")
        print()
    
    if results['warnings']:
        print("Warnings:")
        for item in results['warnings']:
            print(f"  [WARN] {item}")
        print()
    
    if results['failed']:
        print("Failed:")
        for item in results['failed']:
            print(f"  [FAIL] {item}")
        print()
    
    print("=" * 70)
    
    return results

if __name__ == '__main__':
    verify_fixes()
