#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Test All Debugger URLs
Fast testing with reduced timeout
"""
import requests
import json
from datetime import datetime
import urllib3

# Disable SSL warnings for testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://masternoder.dk"

ENDPOINTS = [
    {'url': '/vidgenerator/api/debug/all-systems', 'method': 'GET'},
    {'url': '/vidgenerator/api/debug/all-routes', 'method': 'GET'},
    {'url': '/vidgenerator/api/debug/check-duplicates', 'method': 'GET'},
    {'url': '/vidgenerator/api/debugger/scanner/scan', 'method': 'GET'},
    {'url': '/vidgenerator/api/debugger/agent/fix-personality', 'method': 'POST'},
    {'url': '/vidgenerator/api/agent/master-fix/personality', 'method': 'GET'},
    {'url': '/vidgenerator/api/debugger/profile/points?user_id=default_user', 'method': 'GET'},
    {'url': '/vidgenerator/api/debugger/tasks/list', 'method': 'GET'},
]

def test_endpoint(endpoint):
    url = f"{BASE_URL}{endpoint['url']}"
    try:
        if endpoint['method'] == 'GET':
            r = requests.get(url, timeout=3)
        else:
            r = requests.post(url, json={}, timeout=3)
        
        try:
            data = r.json()
            status = 'OK' if r.status_code == 200 and data.get('success') is not False else f'HTTP_{r.status_code}'
        except:
            status = f'HTTP_{r.status_code}'
        
        return {
            'name': endpoint['url'].split('/')[-1],
            'status': status,
            'code': r.status_code
        }
    except Exception as e:
        return {
            'name': endpoint['url'].split('/')[-1],
            'status': 'ERROR',
            'error': str(e)[:50]
        }

print("Testing debugger endpoints...")
print("=" * 60)

results = []
for endpoint in ENDPOINTS:
    result = test_endpoint(endpoint)
    results.append(result)
    status_symbol = '[OK]' if result['status'] == 'OK' else '[FAIL]'
    code_info = f"({result.get('code', 'N/A')})" if result.get('code') else ""
    error_info = f" - {result.get('error', '')}" if result.get('error') else ""
    print(f"{status_symbol} {result['name']}: {result['status']} {code_info}{error_info}")

print("=" * 60)
ok_count = sum(1 for r in results if r['status'] == 'OK')
print(f"Results: {ok_count}/{len(ENDPOINTS)} OK")
