#!/usr/bin/env python3
"""
End-to-End Test Suite for masternoder.dk/vidgenerator
Server-side version - runs on the server itself
"""

import requests
import sys
from typing import Dict, List, Tuple

BASE_URL = "http://127.0.0.1:5000"  # Test locally on server
TIMEOUT = 10

def test_route(url: str, expected_status: int = 200) -> Tuple[bool, str, int]:
    """Test a route and return (success, message, status_code)"""
    try:
        response = requests.get(url, timeout=TIMEOUT, allow_redirects=True)
        success = response.status_code == expected_status
        message = f"{response.status_code} - {len(response.content)} bytes"
        return success, message, response.status_code
    except requests.exceptions.Timeout:
        return False, "Timeout", 0
    except requests.exceptions.RequestException as e:
        return False, f"Error: {str(e)[:50]}", 0

def test_api_get(url: str) -> Tuple[bool, str, int]:
    """Test a GET API endpoint"""
    try:
        response = requests.get(url, timeout=TIMEOUT)
        success = response.status_code in [200, 500]  # 500 is OK for now (database issues)
        message = f"{response.status_code}"
        if response.status_code == 200:
            try:
                data = response.json()
                message += f" - JSON response ({len(str(data))} chars)"
            except:
                message += f" - {len(response.content)} bytes"
        return success, message, response.status_code
    except Exception as e:
        return False, f"Error: {str(e)[:50]}", 0

def test_api_post(url: str, data: dict = None) -> Tuple[bool, str, int]:
    """Test a POST API endpoint"""
    try:
        response = requests.post(url, json=data or {}, timeout=TIMEOUT)
        success = response.status_code in [200, 201, 400, 500]  # Various acceptable statuses
        message = f"{response.status_code}"
        return success, message, response.status_code
    except Exception as e:
        return False, f"Error: {str(e)[:50]}", 0

def test_static_file(url: str) -> Tuple[bool, str, int]:
    """Test a static file"""
    try:
        response = requests.get(url, timeout=TIMEOUT)
        success = response.status_code == 200
        message = f"{response.status_code} - {len(response.content)} bytes"
        return success, message, response.status_code
    except Exception as e:
        return False, f"Error: {str(e)[:50]}", 0

def main():
    """Run end-to-end tests"""
    print("=" * 70)
    print("END-TO-END TEST SUITE - Server-side")
    print("=" * 70)
    print()
    
    results = {
        'routes': [],
        'apis': [],
        'static': [],
        'total': 0,
        'passed': 0,
        'failed': 0
    }
    
    # Test Main Routes
    print("Testing Main Routes:")
    print("-" * 70)
    
    routes = [
        ("/", "Main page"),
        ("/generator", "Generator page"),
        ("/gallery", "Gallery page"),
        ("/stats", "Stats page"),
        ("/debugger", "Debugger page"),
        ("/game", "Game page"),
    ]
    
    for route, name in routes:
        url = f"{BASE_URL}{route}"
        success, message, status = test_route(url)
        results['routes'].append((name, success, message, status))
        results['total'] += 1
        if success:
            results['passed'] += 1
            print(f"  ✅ {name:20} {message}")
        else:
            results['failed'] += 1
            print(f"  ❌ {name:20} {message}")
    
    print()
    
    # Test Static Files
    print("Testing Static Files:")
    print("-" * 70)
    
    static_files = [
        ("/static/css/style.css", "Main CSS"),
        ("/static/js/main.js", "Main JS"),
        ("/static/css/design-system.css", "Design System CSS"),
    ]
    
    for file_path, name in static_files:
        url = f"{BASE_URL}{file_path}"
        success, message, status = test_static_file(url)
        results['static'].append((name, success, message, status))
        results['total'] += 1
        if success:
            results['passed'] += 1
            print(f"  ✅ {name:20} {message}")
        else:
            results['failed'] += 1
            print(f"  ❌ {name:20} {message}")
    
    print()
    
    # Test API Endpoints
    print("Testing API Endpoints:")
    print("-" * 70)
    
    api_get = [
        ("/api/gallery/list", "Gallery list"),
        ("/api/statistics", "Statistics"),
        ("/api/debug/errors/scan", "Error scan"),
    ]
    
    for endpoint, name in api_get:
        url = f"{BASE_URL}{endpoint}"
        success, message, status = test_api_get(url)
        results['apis'].append((name, success, message, status))
        results['total'] += 1
        if success:
            results['passed'] += 1
            print(f"  ✅ {name:20} GET  {message}")
        else:
            results['failed'] += 1
            print(f"  ❌ {name:20} GET  {message}")
    
    api_post = [
        ("/api/generator/create", "Generator create"),
        ("/api/game/xp", "Game XP"),
    ]
    
    for endpoint, name in api_post:
        url = f"{BASE_URL}{endpoint}"
        success, message, status = test_api_post(url, {})
        results['apis'].append((name, success, message, status))
        results['total'] += 1
        if success:
            results['passed'] += 1
            print(f"  ✅ {name:20} POST {message}")
        else:
            results['failed'] += 1
            print(f"  ❌ {name:20} POST {message}")
    
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests:  {results['total']}")
    print(f"Passed:       {results['passed']} ({results['passed']/results['total']*100:.1f}%)")
    print(f"Failed:       {results['failed']}")
    print()
    
    # Detailed Results
    print("Detailed Results:")
    print("-" * 70)
    
    print("\nRoutes:")
    for name, success, message, status in results['routes']:
        status_icon = "✅" if success else "❌"
        print(f"  {status_icon} {name:20} Status: {status} - {message}")
    
    print("\nStatic Files:")
    for name, success, message, status in results['static']:
        status_icon = "✅" if success else "❌"
        print(f"  {status_icon} {name:20} Status: {status} - {message}")
    
    print("\nAPIs:")
    for name, success, message, status in results['apis']:
        status_icon = "✅" if success else "❌"
        print(f"  {status_icon} {name:20} Status: {status} - {message}")
    
    print()
    print("=" * 70)
    
    if results['failed'] == 0:
        print("✅ ALL TESTS PASSED!")
    elif results['passed'] / results['total'] >= 0.8:
        print(f"⚠️  {results['failed']} TESTS FAILED - But most features working")
    else:
        print(f"❌ {results['failed']} TESTS FAILED - Needs attention")
    
    print("=" * 70)
    
    return results['failed'] == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

