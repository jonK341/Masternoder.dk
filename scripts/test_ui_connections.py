#!/usr/bin/env python3
"""
UI Connection Test Script
Tests frontend-backend API connections
"""
import os
import sys
import requests
from typing import Dict, List, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app


class UIConnectionTester:
    """Test UI connections to backend"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or "http://localhost:5000"
        self.app = create_app()
        self.results = {
            'passed': [],
            'failed': [],
            'errors': []
        }
    
    def test_all_connections(self):
        """Test all UI connections"""
        print("=" * 80)
        print("UI CONNECTION TEST")
        print("=" * 80)
        print()
        
        # Test using Flask test client
        with self.app.test_client() as client:
            # Key endpoints that UI uses
            endpoints = [
                # Health checks
                ('/api/health', 'GET', None),
                ('/api/health/database', 'GET', None),
                ('/api/health/system', 'GET', None),
                
                # Points endpoints
                ('/api/points/comprehensive?user_id=test_user', 'GET', None),
                ('/api/points/statistics?user_id=test_user', 'GET', None),
                
                # Stats endpoints
                ('/api/stats/summary?user_id=test_user', 'GET', None),
                ('/api/game/stats?user_id=test_user', 'GET', None),
                ('/api/battle/stats?user_id=test_user', 'GET', None),
                
                # User endpoints
                ('/api/user/identify', 'POST', {'user_id': 'test_user'}),
                
                # Game endpoints
                ('/api/game/milestones?user_id=test_user', 'GET', None),
                ('/api/game/achievements?user_id=test_user', 'GET', None),
                
                # Aggregator endpoints
                ('/api/aggregator/frontend?user_id=test_user', 'GET', None),
                ('/api/aggregator/stats/user/test_user', 'GET', None),
            ]
            
            print(f"Testing {len(endpoints)} endpoints...")
            print()
            
            for endpoint, method, data in endpoints:
                self.test_endpoint(client, endpoint, method, data)
            
            # Print summary
            self.print_summary()
    
    def test_endpoint(self, client, endpoint: str, method: str, data: Dict = None):
        """Test a single endpoint"""
        try:
            if method == 'GET':
                response = client.get(endpoint)
            elif method == 'POST':
                response = client.post(endpoint, json=data or {})
            else:
                return
            
            status_code = response.status_code
            is_json = False
            
            try:
                json_data = response.get_json()
                is_json = True
            except Exception:
                json_data = None
            
            # Check if response is valid
            valid = status_code in [200, 201] and is_json
            
            status = "[OK]" if valid else "[FAIL]"
            print(f"{status} {method:4} {endpoint:50} [{status_code}] {'JSON' if is_json else 'NOT JSON'}")
            
            if valid:
                self.results['passed'].append(endpoint)
            else:
                self.results['failed'].append({
                    'endpoint': endpoint,
                    'status': status_code,
                    'is_json': is_json
                })
                
        except Exception as e:
            print(f"[ERROR] {method:4} {endpoint:50} [ERROR] {str(e)}")
            self.results['errors'].append({
                'endpoint': endpoint,
                'error': str(e)
            })
    
    def print_summary(self):
        """Print test summary"""
        print()
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print()
        
        total = len(self.results['passed']) + len(self.results['failed']) + len(self.results['errors'])
        passed = len(self.results['passed'])
        
        print(f"Total Tests: {total}")
        print(f"[OK] Passed: {passed}")
        print(f"[FAIL] Failed: {len(self.results['failed'])}")
        print(f"[WARN] Errors: {len(self.results['errors'])}")
        print()
        
        if self.results['failed']:
            print("Failed Endpoints:")
            for item in self.results['failed']:
                print(f"   - {item['endpoint']} (Status: {item['status']}, JSON: {item['is_json']})")
            print()
        
        if self.results['errors']:
            print("Errors:")
            for item in self.results['errors']:
                print(f"   - {item['endpoint']}: {item['error']}")
            print()
        
        success_rate = (passed / total * 100) if total > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        print()


def main():
    """Main entry point"""
    tester = UIConnectionTester()
    tester.test_all_connections()


if __name__ == '__main__':
    main()
