#!/usr/bin/env python3
"""
Comprehensive test of all game features
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
    print(f"  {method} {url}")
    try:
        if method == 'GET':
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        
        status_ok = response.status_code == expected_status
        status_icon = "✅" if status_ok else "❌"
        print(f"  Status: {response.status_code} {status_icon}")
        
        if response.status_code in [200, 201]:
            try:
                data = response.json()
                if 'success' in data:
                    print(f"  Success: {data.get('success')}")
            except:
                pass
        
        return status_ok
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    print("="*80)
    print("COMPREHENSIVE GAME FEATURES TEST")
    print("="*80)
    
    results = {}
    
    # Game Core
    print("\n" + "="*80)
    print("GAME CORE")
    print("="*80)
    results['game_state'] = test_endpoint("Game State", 'GET', f"{BASE_URL}/api/game/state?user_id={USER_ID}")
    results['stats_points'] = test_endpoint("Stats Points", 'GET', f"{BASE_URL}/api/game/stats-points?user_id={USER_ID}")
    results['achievements'] = test_endpoint("Achievements", 'GET', f"{BASE_URL}/api/game/achievements?user_id={USER_ID}")
    results['milestones'] = test_endpoint("Milestones", 'GET', f"{BASE_URL}/api/game/milestones?user_id={USER_ID}")
    
    # Battle System
    print("\n" + "="*80)
    print("BATTLE SYSTEM")
    print("="*80)
    results['battle_clans'] = test_endpoint("List Clans", 'GET', f"{BASE_URL}/api/battle/clans")
    results['battle_battles'] = test_endpoint("List Battles", 'GET', f"{BASE_URL}/api/battle/battles")
    results['battle_leaderboard'] = test_endpoint("Battle Leaderboard", 'GET', f"{BASE_URL}/api/battle/leaderboard")
    
    # Social Network
    print("\n" + "="*80)
    print("SOCIAL NETWORK")
    print("="*80)
    results['social_feed'] = test_endpoint("Social Feed", 'GET', f"{BASE_URL}/api/social/feed?user_id={USER_ID}")
    results['social_friends'] = test_endpoint("Friends List", 'GET', f"{BASE_URL}/api/social/friends?user_id={USER_ID}")
    results['social_followers'] = test_endpoint("Followers List", 'GET', f"{BASE_URL}/api/social/followers?user_id={USER_ID}")
    
    # Items System
    print("\n" + "="*80)
    print("ITEMS SYSTEM")
    print("="*80)
    results['items_inventory'] = test_endpoint("Inventory", 'GET', f"{BASE_URL}/api/items/inventory?user_id={USER_ID}")
    results['items_definitions'] = test_endpoint("Item Definitions", 'GET', f"{BASE_URL}/api/items/definitions")
    
    # Artifacts System
    print("\n" + "="*80)
    print("ARTIFACTS SYSTEM")
    print("="*80)
    results['artifacts_user'] = test_endpoint("User Artifacts", 'GET', f"{BASE_URL}/api/artifacts/user?user_id={USER_ID}")
    results['artifacts_definitions'] = test_endpoint("Artifact Definitions", 'GET', f"{BASE_URL}/api/artifacts/definitions")
    results['artifacts_power'] = test_endpoint("Artifact Power", 'GET', f"{BASE_URL}/api/artifacts/power?user_id={USER_ID}")
    
    # Player Profiler
    print("\n" + "="*80)
    print("PLAYER PROFILER")
    print("="*80)
    results['profiler_profile'] = test_endpoint("Player Profile", 'GET', f"{BASE_URL}/api/profiler/profile?user_id={USER_ID}")
    results['profiler_triggers'] = test_endpoint("Triggers", 'GET', f"{BASE_URL}/api/profiler/triggers")
    results['profiler_history'] = test_endpoint("Trigger History", 'GET', f"{BASE_URL}/api/profiler/history?user_id={USER_ID}")
    
    # Pages
    print("\n" + "="*80)
    print("PAGES")
    print("="*80)
    results['game_page'] = test_endpoint("Game Page", 'GET', f"{BASE_URL}/game", expected_status=200)
    results['stats_page'] = test_endpoint("Stats Page", 'GET', f"{BASE_URL}/stats", expected_status=200)
    results['generator_page'] = test_endpoint("Generator Page", 'GET', f"{BASE_URL}/generator", expected_status=200)
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} passed ({passed*100//total}%)")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print(f"\n❌ {total - passed} test(s) failed")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

