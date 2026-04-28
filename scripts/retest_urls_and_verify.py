#!/usr/bin/env python3
"""
Retest URLs and Verify Blueprints
Re-tests URLs after restart and verifies blueprint registrations
"""
import requests
import json
import time
from typing import Dict, List

BASE_URL = "https://masternoder.dk"

# URLs to test
TEST_URLS = [
    "/vidgenerator/api/points/all",
    "/vidgenerator/api/unified-dashboard/data",
    "/vidgenerator/api/monetization/top50",
    "/vidgenerator/api/leaderboard/all",
    "/vidgenerator/api/debug/report",
    "/vidgenerator/api/debug/system/unified_point_counter",
    "/vidgenerator/api/debug/route?path=/api/points/all",
    "/vidgenerator/api/debug/check-duplicates",
    "/vidgenerator/api/aggregator/all",
    "/vidgenerator/api/aggregator/dashboard",
    "/vidgenerator/api/tech-tree/knowledge",
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
    
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
    
    return result

def verify_blueprints() -> Dict:
    """Verify blueprint registrations via debug endpoint"""
    result = {
        'success': False,
        'blueprints': {},
        'duplicates': [],
        'error': None
    }
    
    try:
        # Try to get blueprint info from debug endpoint
        response = requests.get(f"{BASE_URL}/vidgenerator/api/debug/check-duplicates", timeout=10)
        if response.status_code == 200:
            data = response.json()
            result['success'] = True
            result['blueprints'] = data.get('result', {})
            result['duplicates'] = data.get('result', {}).get('duplicates', [])
        else:
            result['error'] = f"Status {response.status_code}"
    except Exception as e:
        result['error'] = str(e)
    
    return result

def check_route_prefixes() -> Dict:
    """Check if routes need /vidgenerator prefix"""
    result = {
        'needs_prefix': [],
        'works_without_prefix': [],
        'works_with_prefix': []
    }
    
    test_routes = [
        "/api/points/all",
        "/api/debug/report",
        "/api/aggregator/all",
    ]
    
    for route in test_routes:
        # Test without prefix
        try:
            resp1 = requests.get(f"{BASE_URL}{route}", timeout=5, allow_redirects=False)
            if resp1.status_code == 200:
                result['works_without_prefix'].append(route)
        except:
            pass
        
        # Test with prefix
        try:
            resp2 = requests.get(f"{BASE_URL}/vidgenerator{route}", timeout=5, allow_redirects=False)
            if resp2.status_code == 200:
                result['works_with_prefix'].append(route)
        except:
            pass
    
    return result

def main():
    """Main testing function"""
    print("="*80)
    print("RETESTING URLs AND VERIFYING BLUEPRINTS")
    print("="*80)
    print()
    
    # Test URLs
    print("[1/3] Testing URLs...")
    results = []
    for url in TEST_URLS:
        print(f"  Testing: {url}...", end=' ')
        result = test_url(url)
        results.append(result)
        if result['status'] == 'ok':
            print(f"✓ OK ({result['status_code']}) - {result['response_time']}ms")
        else:
            print(f"✗ {result['status'].upper()} ({result.get('status_code', 'N/A')})")
    
    print()
    print("[2/3] Verifying blueprint registrations...")
    blueprint_info = verify_blueprints()
    if blueprint_info['success']:
        print(f"  ✓ Blueprints verified")
        if blueprint_info['duplicates']:
            print(f"  ⚠ Found {len(blueprint_info['duplicates'])} duplicates")
        else:
            print(f"  ✓ No duplicates found")
    else:
        print(f"  ✗ Error: {blueprint_info.get('error', 'Unknown')}")
    
    print()
    print("[3/3] Checking route prefix handling...")
    prefix_info = check_route_prefixes()
    print(f"  Works with prefix: {len(prefix_info['works_with_prefix'])}")
    print(f"  Works without prefix: {len(prefix_info['works_without_prefix'])}")
    
    print()
    print("="*80)
    print("SUMMARY")
    print("="*80)
    ok_count = len([r for r in results if r['status'] == 'ok'])
    broken_count = len([r for r in results if r['status'] != 'ok'])
    print(f"Total tested: {len(results)}")
    print(f"OK: {ok_count}")
    print(f"Broken: {broken_count}")
    
    if broken_count > 0:
        print()
        print("Broken URLs:")
        for r in results:
            if r['status'] != 'ok':
                print(f"  - {r['url']}: {r['status']} ({r.get('status_code', 'N/A')})")
    
    # Save results
    with open('retest_results.json', 'w') as f:
        json.dump({
            'url_results': results,
            'blueprint_info': blueprint_info,
            'prefix_info': prefix_info,
            'summary': {
                'total': len(results),
                'ok': ok_count,
                'broken': broken_count
            }
        }, f, indent=2)
    
    print()
    print("Results saved to retest_results.json")

if __name__ == "__main__":
    main()
