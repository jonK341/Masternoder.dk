#!/usr/bin/env python3
"""
Aggregator Validation Script
Uses the aggregator to validate data consistency across all subsystems
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask

def validate_with_aggregator():
    """Validate data using aggregator"""
    print("="*70)
    print("AGGREGATOR VALIDATION")
    print("="*70)
    print()
    
    # Create Flask app
    try:
        from src.app import create_app
        app = create_app()
    except Exception as e:
        print(f"[ERROR] Could not create app: {e}")
        return
    
    # Test aggregator route
    test_users = ['test_user_1', 'test_user_2', 'test_user_3', 'test_user_5', 'test_user_10']
    
    results = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'errors': []
    }
    
    with app.test_client() as client:
        # Test aggregator route if it exists
        aggregator_routes = [
            '/api/aggregator/data?user_id=test_user_1',
            '/vidgenerator/api/aggregator/data?user_id=test_user_1',
            '/api/intelligence/aggregate?user_id=test_user_1',
            '/vidgenerator/api/intelligence/aggregate?user_id=test_user_1',
        ]
        
        print("[1/3] Testing aggregator routes...")
        for route in aggregator_routes:
            results['total'] += 1
            try:
                response = client.get(route)
                if response.status_code == 200:
                    try:
                        data = response.get_json()
                        if data:
                            results['success'] += 1
                            print(f"  [OK] {route[:60]}...")
                        else:
                            results['failed'] += 1
                            print(f"  [WARN] {route[:60]}... - Empty response")
                    except Exception as e:
                        results['failed'] += 1
                        print(f"  [WARN] {route[:60]}... - {str(e)}")
                elif response.status_code == 404:
                    print(f"  [SKIP] {route[:60]}... - Route not found (expected)")
                else:
                    results['failed'] += 1
                    print(f"  [ERROR] {route[:60]}... - Status {response.status_code}")
            except Exception as e:
                results['failed'] += 1
                print(f"  [ERROR] {route[:60]}... - {str(e)}")
        print()
        
        # Test unified dashboard (acts as aggregator)
        print("[2/3] Testing unified dashboard aggregator...")
        for user_id in test_users:
            results['total'] += 1
            try:
                route = f'/api/unified-dashboard/data?user_id={user_id}'
                response = client.get(route)
                if response.status_code == 200:
                    try:
                        data = response.get_json()
                        if data and isinstance(data, dict):
                            # Check if data is aggregated correctly
                            has_points = 'points' in data
                            has_energy = 'energy' in data
                            has_cash = 'cash' in data
                            has_top50 = 'top50' in data
                            
                            if has_points or has_energy or has_cash or has_top50:
                                results['success'] += 1
                                print(f"  [OK] {user_id}: Aggregated data present")
                            else:
                                results['failed'] += 1
                                print(f"  [WARN] {user_id}: No aggregated data")
                        else:
                            results['failed'] += 1
                            print(f"  [WARN] {user_id}: Invalid response format")
                    except Exception as e:
                        results['failed'] += 1
                        print(f"  [ERROR] {user_id}: {str(e)}")
                else:
                    results['failed'] += 1
                    print(f"  [ERROR] {user_id}: Status {response.status_code}")
            except Exception as e:
                results['failed'] += 1
                print(f"  [ERROR] {user_id}: {str(e)}")
        print()
        
        # Test leaderboard aggregation
        print("[3/3] Testing leaderboard aggregation...")
        leaderboard_routes = [
            '/api/leaderboard/all?limit=50&timeframe=all',
            '/api/leaderboard/xp?limit=50',
            '/api/leaderboard/battle?limit=50',
            '/api/leaderboard/social?limit=50',
        ]
        
        for route in leaderboard_routes:
            results['total'] += 1
            try:
                response = client.get(route)
                if response.status_code == 200:
                    try:
                        data = response.get_json()
                        if data and isinstance(data, dict):
                            has_entries = 'entries' in data or 'leaderboard' in data or 'users' in data
                            if has_entries:
                                entries = data.get('entries', data.get('leaderboard', data.get('users', [])))
                                if isinstance(entries, list) and len(entries) > 0:
                                    results['success'] += 1
                                    print(f"  [OK] {route[:50]}... - {len(entries)} entries")
                                else:
                                    results['failed'] += 1
                                    print(f"  [WARN] {route[:50]}... - No entries")
                            else:
                                results['failed'] += 1
                                print(f"  [WARN] {route[:50]}... - No entries field")
                        else:
                            results['failed'] += 1
                            print(f"  [WARN] {route[:50]}... - Invalid format")
                    except Exception as e:
                        results['failed'] += 1
                        print(f"  [ERROR] {route[:50]}... - {str(e)}")
                elif response.status_code == 404:
                    print(f"  [SKIP] {route[:50]}... - Route not found")
                else:
                    results['failed'] += 1
                    print(f"  [ERROR] {route[:50]}... - Status {response.status_code}")
            except Exception as e:
                results['failed'] += 1
                print(f"  [ERROR] {route[:50]}... - {str(e)}")
        print()
    
    print("="*70)
    print("AGGREGATOR VALIDATION SUMMARY")
    print("="*70)
    print()
    print(f"Total tests: {results['total']}")
    print(f"Successful: {results['success']}")
    print(f"Failed: {results['failed']}")
    print(f"Success rate: {results['success']/results['total']*100 if results['total'] > 0 else 0:.1f}%")
    print()
    
    return results

if __name__ == "__main__":
    validate_with_aggregator()
