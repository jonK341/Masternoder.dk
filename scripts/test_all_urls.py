#!/usr/bin/env python3
"""
Test All URLs
Tests all API endpoints and finds broken URLs
"""
import requests
import json
from typing import List, Dict
import time

BASE_URL = "https://masternoder.dk"

# Common API endpoints to test
API_ENDPOINTS = [
    "/vidgenerator/api/points/all",
    "/vidgenerator/api/points/history/analytics",
    "/vidgenerator/api/points/statistics",
    "/vidgenerator/api/unified-dashboard/data",
    "/vidgenerator/api/monetization/top50",
    "/vidgenerator/api/monetization/cash",
    "/vidgenerator/api/tech-tree/knowledge",
    "/vidgenerator/api/agent/get-all",
    "/vidgenerator/api/agent/recommendations",
    "/vidgenerator/api/leaderboard/all",
    "/vidgenerator/api/leaderboard/categories",
    "/vidgenerator/api/aggregator/all",
    "/vidgenerator/api/aggregator/dashboard",
    "/vidgenerator/api/aggregator/frontend",
    "/vidgenerator/api/debug/system/unified_point_counter",
    "/vidgenerator/api/debug/route",
    "/vidgenerator/api/debug/report",
    "/vidgenerator/api/debug/check-duplicates",
]

def test_url(url: str) -> Dict:
    """Test a single URL"""
    full_url = f"{BASE_URL}{url}"
    result = {
        'url': url,
        'status': 'unknown',
        'status_code': None,
        'response_time': None,
        'error': None
    }
    
    try:
        start_time = time.time()
        response = requests.get(full_url, timeout=10, allow_redirects=False)
        response_time = time.time() - start_time
        
        result['status_code'] = response.status_code
        result['response_time'] = round(response_time * 1000, 2)
        
        if response.status_code == 200:
            result['status'] = 'ok'
            try:
                result['json'] = response.json()
            except:
                result['content'] = response.text[:200]
        elif response.status_code == 404:
            result['status'] = 'not_found'
        elif response.status_code >= 500:
            result['status'] = 'server_error'
        else:
            result['status'] = 'error'
    
    except requests.exceptions.Timeout:
        result['status'] = 'timeout'
        result['error'] = 'Request timeout'
    except requests.exceptions.ConnectionError:
        result['status'] = 'connection_error'
        result['error'] = 'Connection error'
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result

def main():
    """Test all URLs"""
    print("="*80)
    print("TESTING ALL URLs")
    print("="*80)
    print()
    
    results = []
    broken = []
    
    for endpoint in API_ENDPOINTS:
        print(f"Testing: {endpoint}...", end=' ')
        result = test_url(endpoint)
        results.append(result)
        
        if result['status'] == 'ok':
            print(f"[OK] ({result['status_code']}) - {result['response_time']}ms")
        else:
            print(f"[FAIL] {result['status'].upper()} ({result.get('status_code', 'N/A')})")
            broken.append(result)
    
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Total tested: {len(results)}")
    print(f"OK: {len([r for r in results if r['status'] == 'ok'])}")
    print(f"Broken: {len(broken)}")
    print()
    
    if broken:
        print("BROKEN URLs:")
        print("-" * 80)
        for result in broken:
            print(f"  {result['url']}: {result['status']} ({result.get('status_code', 'N/A')})")
            if result.get('error'):
                print(f"    Error: {result['error']}")
        print()
    
    # Save results
    with open('url_test_results.json', 'w') as f:
        json.dump({
            'total': len(results),
            'ok': len([r for r in results if r['status'] == 'ok']),
            'broken': len(broken),
            'results': results,
            'broken_urls': broken
        }, f, indent=2)
    
    print("Results saved to url_test_results.json")

if __name__ == "__main__":
    main()
