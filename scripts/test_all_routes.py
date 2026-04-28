#!/usr/bin/env python3
"""
Test All Routes Script
Tests all API routes and verifies they return data
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from backend.register_blueprints import register_all_blueprints

def test_all_routes():
    """Test all routes"""
    print("="*70)
    print("ROUTE TESTING")
    print("="*70)
    print()
    
    # Create Flask app
    try:
        from src.app import create_app
        app = create_app()
    except Exception as e:
        print(f"[ERROR] Could not create app: {e}")
        return
    
    # Test routes
    test_routes = [
        # Unified Dashboard Routes
        ('/api/unified-dashboard/data?user_id=test_user_1', 'GET', 'unified_dashboard'),
        ('/vidgenerator/api/unified-dashboard/data?user_id=test_user_1', 'GET', 'unified_dashboard'),
        
        # Monetization Routes
        ('/api/monetization/top50?limit=10', 'GET', 'monetization_top50'),
        ('/vidgenerator/api/monetization/top50?limit=10', 'GET', 'monetization_top50'),
        ('/api/monetization/cash?user_id=test_user_1', 'GET', 'monetization_cash'),
        ('/vidgenerator/api/monetization/cash?user_id=test_user_1', 'GET', 'monetization_cash'),
        ('/api/tech-tree/knowledge?user_id=test_user_1', 'GET', 'tech_tree_knowledge'),
        ('/vidgenerator/api/tech-tree/knowledge?user_id=test_user_1', 'GET', 'tech_tree_knowledge'),
        
        # Agent Routes
        ('/api/agent/get-all?user_id=test_user_1', 'GET', 'agent_get_all'),
        ('/vidgenerator/api/agent/get-all?user_id=test_user_1', 'GET', 'agent_get_all'),
        ('/api/agent/recommendations?user_id=test_user_1&context=general', 'GET', 'agent_recommendations'),
        ('/vidgenerator/api/agent/recommendations?user_id=test_user_1&context=general', 'GET', 'agent_recommendations'),
        
        # Points Routes
        ('/api/points/statistics?user_id=test_user_1&days=30', 'GET', 'points_statistics'),
        ('/vidgenerator/api/points/statistics?user_id=test_user_1&days=30', 'GET', 'points_statistics'),
        ('/api/points/history/analytics?user_id=test_user_1&days=30', 'GET', 'points_history'),
        ('/vidgenerator/api/points/history/analytics?user_id=test_user_1&days=30', 'GET', 'points_history'),
        ('/api/points/calculator/predict?user_id=test_user_1&activity_type=general&base_points=100&days=7', 'GET', 'points_calculator'),
        ('/vidgenerator/api/points/calculator/predict?user_id=test_user_1&activity_type=general&base_points=100&days=7', 'GET', 'points_calculator'),
        
        # Leaderboard Routes
        ('/api/leaderboard/all?limit=100&timeframe=all', 'GET', 'leaderboard_all'),
        ('/vidgenerator/api/leaderboard/all?limit=100&timeframe=all', 'GET', 'leaderboard_all'),
        ('/api/leaderboard/xp?limit=50', 'GET', 'leaderboard_xp'),
        ('/vidgenerator/api/leaderboard/xp?limit=50', 'GET', 'leaderboard_xp'),
        
        # Tech Tree Routes
        ('/api/tech-tree?user_id=test_user_1', 'GET', 'tech_tree'),
        ('/vidgenerator/api/tech-tree?user_id=test_user_1', 'GET', 'tech_tree'),
    ]
    
    results = {
        'total': 0,
        'success': 0,
        'failed': 0,
        'errors': []
    }
    
    with app.test_client() as client:
        for route, method, name in test_routes:
            results['total'] += 1
            try:
                if method == 'GET':
                    response = client.get(route)
                else:
                    response = client.post(route)
                
                if response.status_code == 200:
                    try:
                        data = response.get_json()
                        if data:
                            results['success'] += 1
                            print(f"  [OK] {name}: {route[:60]}...")
                        else:
                            results['failed'] += 1
                            results['errors'].append(f"{name}: Empty response")
                            print(f"  [WARN] {name}: Empty response")
                    except Exception as e:
                        results['failed'] += 1
                        results['errors'].append(f"{name}: {str(e)}")
                        print(f"  [ERROR] {name}: {str(e)}")
                else:
                    results['failed'] += 1
                    results['errors'].append(f"{name}: Status {response.status_code}")
                    print(f"  [ERROR] {name}: Status {response.status_code}")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"{name}: {str(e)}")
                print(f"  [ERROR] {name}: {str(e)}")
    
    print()
    print("="*70)
    print("ROUTE TEST SUMMARY")
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
    test_all_routes()
