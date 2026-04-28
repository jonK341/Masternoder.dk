#!/usr/bin/env python3
"""
Test game points and stats page connection
"""
import sys
import requests
import json

# Fix UnicodeEncodeError on Windows
sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = 'https://masternoder.dk/vidgenerator'

def test_game_stats_connection():
    """Test connection between game and stats"""
    print("="*80)
    print("TESTING GAME AND STATS CONNECTION")
    print("="*80)
    print()
    
    user_id = 'default_user'
    results = {}
    
    # Test 1: Get game state
    print("[TEST 1] Getting game state...")
    try:
        response = requests.get(f"{BASE_URL}/api/game/state?user_id={user_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Game state retrieved")
            print(f"  - Level: {data.get('level', {}).get('current_level', 'N/A')}")
            print(f"  - XP: {data.get('level', {}).get('current_xp', 'N/A')}")
            print(f"  - Stats Points: {data.get('stats_points', {}).get('total', 'N/A')}")
            results['game_state'] = True
        else:
            print(f"  ❌ Failed: {response.status_code}")
            results['game_state'] = False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        results['game_state'] = False
    
    print()
    
    # Test 2: Get stats points
    print("[TEST 2] Getting stats points...")
    try:
        response = requests.get(f"{BASE_URL}/api/game/stats-points?user_id={user_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Stats points retrieved")
            print(f"  - Total: {data.get('total_stats_points', 'N/A')}")
            results['stats_points'] = True
        else:
            print(f"  ❌ Failed: {response.status_code}")
            results['stats_points'] = False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        results['stats_points'] = False
    
    print()
    
    # Test 3: Get achievements
    print("[TEST 3] Getting achievements...")
    try:
        response = requests.get(f"{BASE_URL}/api/game/achievements?user_id={user_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Achievements retrieved")
            print(f"  - Total: {data.get('total', 0)}")
            print(f"  - Earned: {data.get('earned', 0)}")
            results['achievements'] = True
        else:
            print(f"  ❌ Failed: {response.status_code}")
            results['achievements'] = False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        results['achievements'] = False
    
    print()
    
    # Test 4: Get milestones
    print("[TEST 4] Getting milestones...")
    try:
        response = requests.get(f"{BASE_URL}/api/game/milestones?user_id={user_id}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Milestones retrieved")
            print(f"  - Total: {data.get('total', 0)}")
            print(f"  - Reached: {data.get('reached', 0)}")
            results['milestones'] = True
        else:
            print(f"  ❌ Failed: {response.status_code}")
            results['milestones'] = False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        results['milestones'] = False
    
    print()
    
    # Test 5: Get stats summary
    print("[TEST 5] Getting stats summary...")
    try:
        response = requests.get(f"{BASE_URL}/api/stats/summary", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Stats summary retrieved")
            print(f"  - Total videos: {data.get('stats', {}).get('total_videos', 'N/A')}")
            results['stats_summary'] = True
        else:
            print(f"  ❌ Failed: {response.status_code}")
            results['stats_summary'] = False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        results['stats_summary'] = False
    
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test}")
    
    all_passed = all(results.values())
    print()
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED!")
    
    return all_passed

if __name__ == '__main__':
    success = test_game_stats_connection()
    sys.exit(0 if success else 1)

