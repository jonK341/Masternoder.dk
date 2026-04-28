#!/usr/bin/env python3
"""
Test all game points and stats connections comprehensively
"""
import sys
import requests
import json

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = 'https://masternoder.dk/vidgenerator'
USER_ID = 'default_user'

def test_endpoint(name, method, url, data=None, expected_status=200):
    """Test a single endpoint"""
    print(f"\n[TEST] {name}")
    print(f"  URL: {url}")
    try:
        if method == 'GET':
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        
        status_ok = response.status_code == expected_status
        print(f"  Status: {response.status_code} {'✅' if status_ok else '❌'}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"  Response: {json.dumps(data, indent=2)[:200]}...")
            except:
                print(f"  Response: {response.text[:200]}...")
        
        return status_ok
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    print("="*80)
    print("COMPREHENSIVE GAME POINTS & STATS TEST")
    print("="*80)
    
    results = {}
    
    # Game State
    results['game_state'] = test_endpoint(
        "Game State",
        'GET',
        f"{BASE_URL}/api/game/state?user_id={USER_ID}"
    )
    
    # Stats Points
    results['stats_points'] = test_endpoint(
        "Stats Points",
        'GET',
        f"{BASE_URL}/api/game/stats-points?user_id={USER_ID}"
    )
    
    # Achievements
    results['achievements'] = test_endpoint(
        "Achievements",
        'GET',
        f"{BASE_URL}/api/game/achievements?user_id={USER_ID}"
    )
    
    # Milestones
    results['milestones'] = test_endpoint(
        "Milestones",
        'GET',
        f"{BASE_URL}/api/game/milestones?user_id={USER_ID}"
    )
    
    # Update Stats
    results['update_stats'] = test_endpoint(
        "Update Stats",
        'POST',
        f"{BASE_URL}/api/game/update-stats",
        {'user_id': USER_ID}
    )
    
    # Hunters Profile
    results['hunters_profile'] = test_endpoint(
        "Hunters Profile",
        'GET',
        f"{BASE_URL}/api/game/hunters/profile?user_id={USER_ID}"
    )
    
    # Hunters Level
    results['hunters_level'] = test_endpoint(
        "Hunters Level",
        'GET',
        f"{BASE_URL}/api/game/hunters/level?user_id={USER_ID}"
    )
    
    # Stats Summary
    results['stats_summary'] = test_endpoint(
        "Stats Summary",
        'GET',
        f"{BASE_URL}/api/stats/summary"
    )
    
    # Statistics
    results['statistics'] = test_endpoint(
        "Statistics",
        'GET',
        f"{BASE_URL}/api/statistics"
    )
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} passed ({passed*100//total}%)")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

