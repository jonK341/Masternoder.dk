#!/usr/bin/env python3
"""Test subsystem leaderboards and generate test users with points"""
import requests
import json
import random
import uuid
import sys

BASE_URL = "https://masternoder.dk"

# Subsystems to test
SUBSYSTEMS = ['xp', 'battle', 'trophies', 'activity', 'generation', 'chat', 'theme', 'reward']

def test_endpoint(endpoint, description):
    """Test a leaderboard endpoint"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*70}")
    print(f"Testing: {description}")
    print(f"URL: {endpoint}")
    print(f"{'='*70}")
    
    try:
        response = requests.get(url, timeout=10, headers={'Accept': 'application/json'})
        content_type = response.headers.get('content-type', '')
        
        if response.status_code == 200 and 'application/json' in content_type:
            data = response.json()
            print(f"✓ Status: 200 OK")
            print(f"  Success: {data.get('success', False)}")
            print(f"  Total Entries: {data.get('total_entries', 0)}")
            
            leaderboard = data.get('leaderboard', [])
            if leaderboard and len(leaderboard) > 0:
                print(f"  First Entry:")
                first = leaderboard[0]
                print(f"    User ID: {first.get('user_id', 'N/A')}")
                print(f"    Username: {first.get('username', 'N/A')}")
                print(f"    Points: {first.get('points', first.get('total_points', 0))}")
                print(f"    Rank: {first.get('rank', 'N/A')}")
            else:
                print(f"  ⚠ No entries in leaderboard")
            
            if data.get('error'):
                print(f"  Error: {data.get('error')}")
                
            return data
        else:
            print(f"✗ Status: {response.status_code}")
            print(f"  Content-Type: {content_type}")
            if response.status_code == 404:
                print(f"  Endpoint not found")
            return None
    except Exception as e:
        print(f"✗ Error: {e}")
        return None

def main():
    print("="*70)
    print("SUBSYSTEM LEADERBOARD TESTING")
    print("="*70)
    
    # Test "All Systems" first
    test_endpoint("/vidgenerator/api/leaderboard/all?limit=10", "All Systems Leaderboard")
    
    # Test each subsystem
    for subsystem in SUBSYSTEMS:
        test_endpoint(f"/vidgenerator/api/leaderboard/{subsystem}?limit=10", f"{subsystem.capitalize()} Leaderboard")
    
    # Test stats endpoint
    test_endpoint("/vidgenerator/api/leaderboard/stats", "Leaderboard Stats")
    
    print("\n" + "="*70)
    print("TESTING COMPLETE")
    print("="*70)

if __name__ == "__main__":
    main()
