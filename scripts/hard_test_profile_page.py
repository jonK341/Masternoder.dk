#!/usr/bin/env python3
"""
Hard Test Profile Page - Comprehensive testing of profile page and APIs
"""
import requests
import json

BASE_URL = "https://masternoder.dk"

def test_profile_page():
    """Test the profile page HTML"""
    print("=" * 70)
    print("HARD TEST: PROFILE PAGE")
    print("=" * 70)
    print()
    
    # Test 1: Get profile page HTML
    print("[1/6] Testing profile page HTML...")
    try:
        r = requests.get(f"{BASE_URL}/vidgenerator/profile", timeout=15)
        print(f"  Status: {r.status_code}")
        html = r.text
        
        checks = {
            'backend-connector.js': '/vidgenerator/static/js/backend-connector.js' in html,
            'ProfileManager class': 'class ProfileManager' in html,
            'loadProfile method': 'async loadProfile()' in html,
            'getUserProfileDisplay call': 'getUserProfileDisplay' in html,
            'DOMContentLoaded': 'DOMContentLoaded' in html
        }
        
        print("  HTML Checks:")
        for check, passed in checks.items():
            status = "[OK]" if passed else "[FAIL]"
            print(f"    {status} {check}")
        
        print(f"  HTML Size: {len(html)} bytes")
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False
    
    print()
    
    # Test 2: Test backend-connector.js
    print("[2/6] Testing backend-connector.js...")
    try:
        r = requests.get(f"{BASE_URL}/vidgenerator/static/js/backend-connector.js", timeout=10)
        print(f"  Status: {r.status_code}")
        js = r.text
        
        js_checks = {
            'BackendConnector class': 'class BackendConnector' in js,
            'getUserId method': 'getUserId()' in js,
            'getUserProfileDisplay method': 'getUserProfileDisplay' in js,
            'getStats method': 'getStats' in js,
            'getAllPoints method': 'getAllPoints' in js,
            'global instance': 'const backendConnector = new BackendConnector()' in js or 'backendConnector = new BackendConnector' in js
        }
        
        print("  JavaScript Checks:")
        for check, passed in js_checks.items():
            status = "[OK]" if passed else "[FAIL]"
            print(f"    {status} {check}")
        
        print(f"  JS Size: {len(js)} bytes")
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False
    
    print()
    
    # Test 3: Test profile display API
    print("[3/6] Testing profile display API...")
    test_user = 'default_user'
    try:
        url = f"{BASE_URL}/vidgenerator/api/user/profile/{test_user}/display"
        r = requests.get(url, timeout=10)
        print(f"  Status: {r.status_code}")
        print(f"  URL: {url}")
        
        if r.status_code == 200:
            try:
                data = r.json()
                print(f"  Response Success: {data.get('success')}")
                print(f"  Has Profile: {'profile' in data}")
                print(f"  Has Stats: {'stats' in data}")
                print(f"  Has Skills: {'skills' in data}")
                
                if data.get('profile'):
                    profile = data['profile']
                    print(f"  Profile User ID: {profile.get('user_id')}")
                    print(f"  Profile Display Name: {profile.get('display_name')}")
                
            except Exception as e:
                print(f"  [ERROR] Failed to parse JSON: {e}")
                print(f"  Response (first 200 chars): {r.text[:200]}")
        else:
            print(f"  [ERROR] API returned {r.status_code}")
            print(f"  Response (first 200 chars): {r.text[:200]}")
            
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False
    
    print()
    
    # Test 4: Test stats API
    print("[4/6] Testing stats API...")
    try:
        url = f"{BASE_URL}/vidgenerator/api/stats/user/{test_user}"
        r = requests.get(url, timeout=10)
        print(f"  Status: {r.status_code}")
        print(f"  URL: {url}")
        
        if r.status_code == 200:
            try:
                data = r.json()
                print(f"  Response Success: {data.get('success')}")
                print(f"  Has Stats: {'stats' in data}")
            except Exception as e:
                print(f"  [ERROR] Failed to parse JSON: {e}")
        else:
            print(f"  [WARN] Stats API returned {r.status_code}")
            
    except Exception as e:
        print(f"  [WARN] Stats API error: {e}")
    
    print()
    
    # Test 5: Test points API
    print("[5/6] Testing points API...")
    try:
        url = f"{BASE_URL}/vidgenerator/api/points/all?user_id={test_user}"
        r = requests.get(url, timeout=10)
        print(f"  Status: {r.status_code}")
        print(f"  URL: {url}")
        
        if r.status_code == 200:
            try:
                data = r.json()
                print(f"  Response Success: {data.get('success')}")
                print(f"  Has All Points: {'all_points' in data}")
            except Exception as e:
                print(f"  [ERROR] Failed to parse JSON: {e}")
        else:
            print(f"  [WARN] Points API returned {r.status_code}")
            
    except Exception as e:
        print(f"  [WARN] Points API error: {e}")
    
    print()
    
    # Test 6: Test agent skills API
    print("[6/6] Testing agent skills API...")
    try:
        url = f"{BASE_URL}/vidgenerator/api/user/agent-skills/{test_user}"
        r = requests.get(url, timeout=10)
        print(f"  Status: {r.status_code}")
        print(f"  URL: {url}")
        
        if r.status_code == 200:
            try:
                data = r.json()
                print(f"  Response Success: {data.get('success')}")
                print(f"  Has Skills: {'skills' in data}")
            except Exception as e:
                print(f"  [ERROR] Failed to parse JSON: {e}")
        else:
            print(f"  [WARN] Agent Skills API returned {r.status_code}")
            
    except Exception as e:
        print(f"  [WARN] Agent Skills API error: {e}")
    
    print()
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    test_profile_page()
