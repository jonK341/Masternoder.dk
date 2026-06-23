#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test All Debugger URLs
Comprehensive testing of all debugger endpoints
"""
import requests
import json
import sys
from datetime import datetime
from typing import Dict, List

# Fix encoding for Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

BASE_URL = "https://masternoder.dk"

# Some debugger endpoints do heavy work (full route/blueprint scans, diagnostics)
# and uWSGI workers pay a one-time import cost on first hit, so use a generous
# timeout and retry once on timeout before declaring a problem.
REQUEST_TIMEOUT = 20
MAX_ATTEMPTS = 2

# Test endpoints
# Production serves API at https://masternoder.dk/api/ — /vidgenerator/api returns 410 (disabled).
ENDPOINTS = [
    # Debug endpoints
    {'url': '/api/debug/all-systems', 'method': 'GET', 'name': 'Debug All Systems'},
    {'url': '/api/debug/all-routes', 'method': 'GET', 'name': 'Debug All Routes'},
    {'url': '/api/debug/check-duplicates', 'method': 'GET', 'name': 'Check Duplicates'},
    {'url': '/api/debug/report', 'method': 'GET', 'name': 'Generate Report'},
    
    # Scanner endpoints
    {'url': '/api/debugger/scanner/scan', 'method': 'GET', 'name': 'Scanner Scan All'},
    {'url': '/api/debugger/scanner/blueprints', 'method': 'GET', 'name': 'Scanner Blueprints'},
    {'url': '/api/debugger/scanner/routes', 'method': 'GET', 'name': 'Scanner Routes'},
    {'url': '/api/debugger/scanner/missing', 'method': 'GET', 'name': 'Scanner Missing'},
    {'url': '/api/debugger/scanner/suggestions', 'method': 'GET', 'name': 'Scanner Suggestions'},
    {'url': '/api/debugger/scanner/registration-code', 'method': 'GET', 'name': 'Scanner Registration Code'},
    {'url': '/api/debugger/scanner/services', 'method': 'GET', 'name': 'Scanner Services'},
    
    # Agent fix endpoints
    {'url': '/api/debugger/agent/fix-personality', 'method': 'POST', 'name': 'Fix Personality'},
    {'url': '/api/debugger/agent/fix-missions', 'method': 'POST', 'name': 'Fix Missions'},
    {'url': '/api/debugger/agent/fix-quests', 'method': 'POST', 'name': 'Fix Quests'},
    {'url': '/api/debugger/agent/fix-history', 'method': 'POST', 'name': 'Fix History'},
    {'url': '/api/debugger/agent/fix-behavior', 'method': 'POST', 'name': 'Fix Behavior'},
    {'url': '/api/debugger/agent/fix-all', 'method': 'POST', 'name': 'Fix All'},
    
    # Agent get endpoints
    {'url': '/api/agent/master-fix/personality', 'method': 'GET', 'name': 'Get Personality'},
    {'url': '/api/agent/master-fix/missions', 'method': 'GET', 'name': 'Get Missions'},
    {'url': '/api/agent/master-fix/quests', 'method': 'GET', 'name': 'Get Quests'},
    {'url': '/api/agent/master-fix/history', 'method': 'GET', 'name': 'Get History'},
    {'url': '/api/agent/master-fix/statistics', 'method': 'GET', 'name': 'Get Statistics'},
    {'url': '/api/agent/master-fix/behavior-pattern', 'method': 'GET', 'name': 'Get Behavior'},
    {'url': '/api/agent/master-fix/run-full-diagnostic', 'method': 'POST', 'name': 'Run Diagnostic'},
    {'url': '/api/agent/master-fix/diagnostic', 'method': 'POST', 'name': 'Diagnostic'},
    
    # Profile endpoints
    {'url': '/api/debugger/profile/points?user_id=default_user', 'method': 'GET', 'name': 'Profile Points'},
    {'url': '/api/debugger/profile/stats?user_id=default_user', 'method': 'GET', 'name': 'Profile Stats'},
    {'url': '/api/debugger/profile/agent-points?agent_id=agent_manager', 'method': 'GET', 'name': 'Agent Points'},
    
    # Task endpoints
    {'url': '/api/debugger/tasks/list', 'method': 'GET', 'name': 'List Tasks'},
    {'url': '/api/debugger/tasks/stats', 'method': 'GET', 'name': 'Task Stats'},
    {'url': '/api/errors/tasks/list', 'method': 'GET', 'name': 'Error Tasks List'},
    {'url': '/api/errors/tasks/stats', 'method': 'GET', 'name': 'Error Tasks Stats'},
    
    # Error endpoints
    {'url': '/api/errors/stats?days=7', 'method': 'GET', 'name': 'Error Stats'},
    {'url': '/api/errors/list?limit=10', 'method': 'GET', 'name': 'Error List'},
    {'url': '/api/errors/handler-status/analyze', 'method': 'GET', 'name': 'Error Handler Status'},
]


def test_endpoint(endpoint: Dict) -> Dict:
    """Test a single endpoint"""
    url = f"{BASE_URL}{endpoint['url']}"
    method = endpoint['method']
    name = endpoint['name']
    
    result = {
        'name': name,
        'url': url,
        'method': method,
        'status': 'unknown',
        'status_code': None,
        'response_time': None,
        'has_data': False,
        'error': None
    }
    
    if method not in ('GET', 'POST'):
        result['error'] = f'Unsupported method: {method}'
        return result

    try:
        start_time = datetime.now()

        response = None
        last_timeout = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                if method == 'GET':
                    response = requests.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
                else:
                    response = requests.post(url, json={}, timeout=REQUEST_TIMEOUT, allow_redirects=True)
                break
            except requests.exceptions.Timeout as te:
                last_timeout = te
                if attempt >= MAX_ATTEMPTS:
                    raise
        
        end_time = datetime.now()
        result['response_time'] = (end_time - start_time).total_seconds()
        result['status_code'] = response.status_code
        
        # Try to parse JSON
        try:
            data = response.json()
            result['has_data'] = True
            result['data_type'] = type(data).__name__
            
            if response.status_code == 200:
                if isinstance(data, dict):
                    if data.get('success') is not False:
                        result['status'] = 'OK'
                    else:
                        result['status'] = 'FAILED'
                        result['error'] = data.get('error', 'Unknown error')
                else:
                    result['status'] = 'OK'
            elif response.status_code == 404:
                result['status'] = '404_NOT_FOUND'
                result['error'] = 'Endpoint not found'
            elif response.status_code == 500:
                result['status'] = '500_SERVER_ERROR'
                result['error'] = data.get('error', 'Server error') if isinstance(data, dict) else 'Server error'
            else:
                result['status'] = f'HTTP_{response.status_code}'
                result['error'] = f'HTTP {response.status_code}'
        except json.JSONDecodeError:
            result['status'] = 'INVALID_JSON'
            result['error'] = 'Response is not valid JSON'
            result['response_text'] = response.text[:200]
    except requests.exceptions.Timeout:
        result['status'] = 'TIMEOUT'
        result['error'] = 'Request timed out'
    except requests.exceptions.ConnectionError:
        result['status'] = 'CONNECTION_ERROR'
        result['error'] = 'Connection error'
    except Exception as e:
        result['status'] = 'ERROR'
        result['error'] = str(e)
    
    return result


def main():
    """Run all endpoint tests"""
    print("=" * 80)
    print("DEBUGGER URL HARD TEST")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print(f"Total endpoints to test: {len(ENDPOINTS)}")
    print()
    
    results = []
    working = []
    failed = []
    errors = []
    
    for i, endpoint in enumerate(ENDPOINTS, 1):
        print(f"[{i}/{len(ENDPOINTS)}] Testing {endpoint['name']}...", end=' ')
        result = test_endpoint(endpoint)
        results.append(result)
        
        if result['status'] == 'OK':
            print(f"[OK] ({result['response_time']:.2f}s)")
            working.append(result)
        elif result['status'] in ['404_NOT_FOUND', '500_SERVER_ERROR']:
            print(f"[FAIL] {result['status']} - {result.get('error', 'Unknown')}")
            failed.append(result)
        else:
            print(f"[WARN] {result['status']} - {result.get('error', 'Unknown')}")
            errors.append(result)
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print(f"Total endpoints tested: {len(ENDPOINTS)}")
    print(f"[OK] Working: {len(working)}")
    print(f"[FAIL] Failed (404/500): {len(failed)}")
    print(f"[WARN] Errors/Other: {len(errors)}")
    print()
    
    if failed:
        print("FAILED ENDPOINTS (404/500):")
        print("-" * 80)
        for result in failed:
            print(f"  [FAIL] {result['name']}")
            print(f"     URL: {result['url']}")
            print(f"     Status: {result['status']} ({result['status_code']})")
            if result.get('error'):
                print(f"     Error: {result['error']}")
            print()
    
    if errors:
        print("ERRORS/OTHER ISSUES:")
        print("-" * 80)
        for result in errors:
            print(f"  [WARN] {result['name']}")
            print(f"     URL: {result['url']}")
            print(f"     Status: {result['status']}")
            if result.get('error'):
                print(f"     Error: {result['error']}")
            print()
    
    # Save detailed results
    output_file = 'debugger_url_test_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total': len(ENDPOINTS),
                'working': len(working),
                'failed': len(failed),
                'errors': len(errors)
            },
            'results': results
        }, f, indent=2, default=str)
    
    print(f"Detailed results saved to: {output_file}")
    print()
    
    # Return exit code
    if failed:
        return 1
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
