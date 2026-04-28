#!/usr/bin/env python3
"""
Test Error Logging System
Tests the error logging API endpoints
"""
import requests
import json
from datetime import datetime

BASE_URL = "https://masternoder.dk"

def test_error_logging():
    """Test error logging system"""
    print("=" * 70)
    print("TESTING ERROR LOGGING SYSTEM")
    print("=" * 70)
    print()
    
    results = {
        'passed': [],
        'failed': [],
        'warnings': []
    }
    
    # Test 1: Error Statistics
    print("[1/4] Testing Error Statistics Endpoint...")
    try:
        url = f"{BASE_URL}/vidgenerator/api/errors/statistics"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and 'statistics' in data:
                stats = data['statistics']
                results['passed'].append("Error statistics endpoint working")
                print(f"  [OK] Statistics endpoint working")
                print(f"    Total errors: {stats.get('total_errors', 0)}")
                print(f"    Error types: {len(stats.get('errors_by_type', {}))}")
                print(f"    Endpoints with errors: {len(stats.get('errors_by_endpoint', {}))}")
            else:
                results['warnings'].append("Statistics endpoint returns unexpected structure")
        else:
            results['failed'].append(f"Statistics endpoint returns {response.status_code}")
    except Exception as e:
        results['failed'].append(f"Statistics test: {str(e)[:50]}")
    
    print()
    
    # Test 2: Recent Errors
    print("[2/4] Testing Recent Errors Endpoint...")
    try:
        url = f"{BASE_URL}/vidgenerator/api/errors/recent?limit=10"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and 'errors' in data:
                errors = data['errors']
                results['passed'].append("Recent errors endpoint working")
                print(f"  [OK] Recent errors endpoint working")
                print(f"    Recent errors count: {len(errors)}")
            else:
                results['warnings'].append("Recent errors endpoint returns unexpected structure")
        else:
            results['failed'].append(f"Recent errors endpoint returns {response.status_code}")
    except Exception as e:
        results['failed'].append(f"Recent errors test: {str(e)[:50]}")
    
    print()
    
    # Test 3: Errors by Type
    print("[3/4] Testing Errors by Type Endpoint...")
    try:
        url = f"{BASE_URL}/vidgenerator/api/errors/by-type/api_error_404"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and 'count' in data:
                results['passed'].append("Errors by type endpoint working")
                print(f"  [OK] Errors by type endpoint working")
                print(f"    404 errors: {data.get('count', 0)}")
            else:
                results['warnings'].append("Errors by type endpoint returns unexpected structure")
        else:
            results['warnings'].append(f"Errors by type endpoint returns {response.status_code} (may be no errors yet)")
    except Exception as e:
        results['warnings'].append(f"Errors by type test: {str(e)[:50]}")
    
    print()
    
    # Test 4: Errors by Endpoint
    print("[4/4] Testing Errors by Endpoint Endpoint...")
    try:
        url = f"{BASE_URL}/vidgenerator/api/errors/by-endpoint"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                results['passed'].append("Errors by endpoint endpoint working")
                print(f"  [OK] Errors by endpoint endpoint working")
                if 'endpoints' in data:
                    print(f"    Endpoints with errors: {len(data['endpoints'])}")
            else:
                results['warnings'].append("Errors by endpoint returns unexpected structure")
        else:
            results['warnings'].append(f"Errors by endpoint returns {response.status_code}")
    except Exception as e:
        results['failed'].append(f"Errors by endpoint test: {str(e)[:50]}")
    
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
    test_error_logging()
