#!/usr/bin/env python3
"""
Test User Identification
Tests the user identification system
"""
import requests
import json
from datetime import datetime

BASE_URL = "https://masternoder.dk"

def test_user_identification():
    """Test user identification system"""
    print("=" * 70)
    print("TESTING USER IDENTIFICATION SYSTEM")
    print("=" * 70)
    print()
    
    results = {
        'passed': [],
        'failed': [],
        'warnings': []
    }
    
    # Test 1: Simple identification endpoint
    print("[1/3] Testing User Identification Endpoint...")
    try:
        url = f"{BASE_URL}/vidgenerator/api/user/identify/simple"
        test_data = {
            'device_fingerprint': 'test_fingerprint_123',
            'screen_width': 1920,
            'screen_height': 1080,
            'timezone': 'UTC',
            'language': 'en-US'
        }
        
        response = requests.post(url, json=test_data, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('user_id'):
                user_id = data['user_id']
                results['passed'].append("User identification endpoint working")
                print(f"  [OK] User identification working")
                print(f"    User ID: {user_id}")
                print(f"    New user: {data.get('new_user', False)}")
                
                # Test 2: Verify user profile exists
                print()
                print("[2/3] Testing User Profile Creation...")
                profile_url = f"{BASE_URL}/vidgenerator/api/user/profile/{user_id}/display"
                profile_response = requests.get(profile_url, timeout=5)
                
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    if profile_data.get('success'):
                        results['passed'].append("User profile created automatically")
                        print(f"  [OK] User profile exists for {user_id}")
                    else:
                        results['warnings'].append("User profile not created automatically")
                else:
                    results['warnings'].append(f"Profile check returned {profile_response.status_code}")
            else:
                results['failed'].append("Identification endpoint doesn't return user_id")
        else:
            results['failed'].append(f"Identification endpoint returns {response.status_code}")
    except Exception as e:
        results['failed'].append(f"Identification test: {str(e)[:50]}")
    
    print()
    print("[3/3] Testing Default User Fallback...")
    # Test that default_user still works as fallback
    try:
        url = f"{BASE_URL}/vidgenerator/api/user/profile/default_user/display"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            results['passed'].append("Default user still accessible as fallback")
            print(f"  [OK] Default user still works as fallback")
        else:
            results['warnings'].append("Default user not accessible")
    except Exception as e:
        results['warnings'].append(f"Default user test: {str(e)[:50]}")
    
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
    test_user_identification()
