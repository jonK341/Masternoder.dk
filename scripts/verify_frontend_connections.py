#!/usr/bin/env python3
"""
Verify Frontend Connections Script
Tests that frontend can connect to all routes and displays data correctly
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask

def verify_frontend_connections():
    """Verify frontend can connect to all routes"""
    print("="*70)
    print("FRONTEND CONNECTION VERIFICATION")
    print("="*70)
    print()
    
    # Create Flask app
    try:
        from src.app import create_app
        app = create_app()
    except Exception as e:
        print(f"[ERROR] Could not create app: {e}")
        return
    
    # Frontend routes that need to be tested
    frontend_routes = {
        'unified_dashboard': [
            '/api/unified-dashboard/data?user_id=test_user_1',
            '/api/monetization/top50?limit=6',
            '/api/monetization/cash?user_id=test_user_1',
            '/api/tech-tree/knowledge?user_id=test_user_1',
            '/api/agent/get-all?user_id=test_user_1',
            '/api/agent/recommendations?user_id=test_user_1&context=general',
            '/api/points/history/analytics?user_id=test_user_1&days=30',
            '/api/points/statistics?user_id=test_user_1&days=30',
            '/api/points/calculator/predict?user_id=test_user_1&activity_type=general&base_points=100&days=7',
        ],
        'leaderboard': [
            '/api/leaderboard/all?limit=100&timeframe=all',
            '/api/leaderboard/xp?limit=50',
            '/api/leaderboard/stats',
        ],
    }
    
    results = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'errors': []
    }
    
    with app.test_client() as client:
        for page, routes in frontend_routes.items():
            print(f"[{page.upper()}] Testing {len(routes)} routes...")
            for route in routes:
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
                                results['errors'].append(f"{page}: {route} - Empty response")
                                print(f"  [WARN] {route[:60]}... - Empty response")
                        except Exception as e:
                            results['failed'] += 1
                            results['errors'].append(f"{page}: {route} - {str(e)}")
                            print(f"  [ERROR] {route[:60]}... - {str(e)}")
                    else:
                        results['failed'] += 1
                        results['errors'].append(f"{page}: {route} - Status {response.status_code}")
                        print(f"  [ERROR] {route[:60]}... - Status {response.status_code}")
                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append(f"{page}: {route} - {str(e)}")
                    print(f"  [ERROR] {route[:60]}... - {str(e)}")
            print()
    
    print("="*70)
    print("FRONTEND CONNECTION SUMMARY")
    print("="*70)
    print()
    print(f"Total routes tested: {results['total']}")
    print(f"Successful: {results['success']}")
    print(f"Failed: {results['failed']}")
    print(f"Success rate: {results['success']/results['total']*100 if results['total'] > 0 else 0:.1f}%")
    print()
    
    if results['errors']:
        print("Errors:")
        for error in results['errors'][:10]:
            print(f"  - {error}")
        if len(results['errors']) > 10:
            print(f"  ... and {len(results['errors']) - 10} more")
        print()
    
    return results

if __name__ == "__main__":
    verify_frontend_connections()
