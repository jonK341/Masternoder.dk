#!/usr/bin/env python3
"""Test Agent Behavior API"""
import requests
import json

BASE_URL = "https://masternoder.dk"
API_BASE = f"{BASE_URL}/vidgenerator/api"

def test_behavior_api():
    """Test agent behavior endpoints"""
    print("=" * 70)
    print("TESTING AGENT BEHAVIOR API")
    print("=" * 70)
    print()
    
    # Test 1: Get behavior type
    print("1. Testing get-behavior-type...")
    try:
        r = requests.get(f"{API_BASE}/agents/behavior/get-behavior-type?agent_id=test_agent_001", timeout=10)
        if r.status_code == 200:
            data = r.json()
            print(f"   ✓ Status: {r.status_code}")
            print(f"   ✓ Behavior Type: {data.get('behavior_type')}")
        else:
            print(f"   ✗ Status: {r.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 2: Simulate session
    print("\n2. Testing simulate-session...")
    try:
        r = requests.post(f"{API_BASE}/agents/behavior/simulate-session", 
                         json={'agent_id': 'test_agent_001'}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            print(f"   ✓ Status: {r.status_code}")
            if data.get('success'):
                plan = data.get('session_plan', {})
                print(f"   ✓ Actions: {len(plan.get('actions', []))}")
                print(f"   ✓ Total XP: {plan.get('total_xp', 0)}")
        else:
            print(f"   ✗ Status: {r.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 3: Simulate day
    print("\n3. Testing simulate-day...")
    try:
        r = requests.post(f"{API_BASE}/agents/behavior/simulate-day",
                         json={'agent_id': 'test_agent_002'}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            print(f"   ✓ Status: {r.status_code}")
            if data.get('success'):
                activity = data.get('daily_activity', {})
                print(f"   ✓ Sessions: {activity.get('total_sessions', 0)}")
                print(f"   ✓ Total Actions: {activity.get('total_actions', 0)}")
                print(f"   ✓ Total XP: {activity.get('total_xp', 0)}")
        else:
            print(f"   ✗ Status: {r.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # Test 4: Should be active
    print("\n4. Testing should-be-active...")
    try:
        r = requests.get(f"{API_BASE}/agents/behavior/should-be-active?agent_id=test_agent_001", timeout=10)
        if r.status_code == 200:
            data = r.json()
            print(f"   ✓ Status: {r.status_code}")
            print(f"   ✓ Should be active: {data.get('should_be_active')}")
            print(f"   ✓ Current hour: {data.get('current_hour')}")
        else:
            print(f"   ✗ Status: {r.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    print()
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

if __name__ == '__main__':
    test_behavior_api()
