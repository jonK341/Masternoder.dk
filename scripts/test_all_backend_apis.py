#!/usr/bin/env python3
"""
Test All Backend APIs
Comprehensive test of all backend API endpoints
"""
import requests
import json
from datetime import datetime

BASE_URL = "https://masternoder.dk"
API_BASE = f"{BASE_URL}/vidgenerator/api"
TEST_USER = "default_user"

def test_endpoint(name, url, method="GET", data=None):
    """Test a single endpoint"""
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10, headers={'Content-Type': 'application/json'})
        else:
            return False, f"Unknown method: {method}"
        
        success = response.status_code in [200, 201]
        content_type = response.headers.get('Content-Type', '')
        is_json = 'application/json' in content_type
        
        result = {
            'name': name,
            'url': url,
            'status': response.status_code,
            'success': success,
            'is_json': is_json,
            'size': len(response.content)
        }
        
        if is_json:
            try:
                json_data = response.json()
                result['has_data'] = bool(json_data)
                result['has_success'] = 'success' in json_data if isinstance(json_data, dict) else False
            except:
                pass
        
        return success, result
    except Exception as e:
        return False, {'name': name, 'url': url, 'error': str(e)}

def main():
    """Test all endpoints"""
    print("=" * 70)
    print("TESTING ALL BACKEND APIs")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print()
    
    endpoints = [
        # User Profile
        ("User Profile", f"{API_BASE}/user/profile/{TEST_USER}", "GET"),
        ("User Profile Display", f"{API_BASE}/user/profile/{TEST_USER}/display", "GET"),
        ("User Profile Stats", f"{API_BASE}/user/profile/{TEST_USER}/stats", "GET"),
        ("User Profile Activity", f"{API_BASE}/user/profile/{TEST_USER}/activity", "GET"),
        
        # Onboarding
        ("Onboarding Status", f"{API_BASE}/user/onboarding/status/{TEST_USER}", "GET"),
        ("Onboarding Progress", f"{API_BASE}/user/onboarding/progress/{TEST_USER}", "GET"),
        
        # Agent Skills
        ("User Agent Skills", f"{API_BASE}/user/agent-skills/{TEST_USER}", "GET"),
        ("Agent Controller Status", f"{API_BASE}/agents/controller/status", "GET"),
        ("Agent Skillset Stats", f"{API_BASE}/agents/skillsets/stats", "GET"),
        
        # Game
        ("Player Level", f"{API_BASE}/game/hunters/level?user_id={TEST_USER}", "GET"),
        ("XP History", f"{API_BASE}/game/hunters/xp-history?user_id={TEST_USER}", "GET"),
        ("Rewards", f"{API_BASE}/game/hunters/rewards?user_id={TEST_USER}", "GET"),
        
        # Shop
        ("Shop Currency", f"{API_BASE}/shop/currency?user_id={TEST_USER}", "GET"),
    ]
    
    results = []
    passed = 0
    failed = 0
    
    print("Testing endpoints...")
    print()
    
    for name, url, method in endpoints:
        success, result = test_endpoint(name, url, method)
        results.append(result)
        
        if success:
            passed += 1
            status = "✓"
        else:
            failed += 1
            status = "✗"
        
        print(f"{status} {name}: {result.get('status', 'ERROR')} - {url[:60]}...")
    
    print()
    print("=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    print(f"Total: {len(endpoints)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success Rate: {(passed/len(endpoints)*100):.1f}%")
    print()
    
    if failed > 0:
        print("Failed endpoints:")
        for result in results:
            if not result.get('success', False):
                print(f"  - {result.get('name')}: {result.get('error', result.get('status', 'Unknown'))}")
    
    return passed == len(endpoints)

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
