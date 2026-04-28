#!/usr/bin/env python3
"""
Test All Page URLs
Tests common page URLs to identify 404 errors
"""
import requests
import json
from datetime import datetime

BASE_URL = "https://masternoder.dk"

# Common page URLs to test
PAGES_TO_TEST = [
    "/vidgenerator/",
    "/vidgenerator/stats",
    "/vidgenerator/stats/",
    "/vidgenerator/dashboard",
    "/vidgenerator/dashboard/",
    "/vidgenerator/profile",
    "/vidgenerator/profile/",
    "/vidgenerator/generator",
    "/vidgenerator/generator/",
    "/vidgenerator/gallery",
    "/vidgenerator/gallery/",
    "/vidgenerator/game",
    "/vidgenerator/game/",
    "/vidgenerator/battle",
    "/vidgenerator/battle/",
    "/vidgenerator/shop",
    "/vidgenerator/shop/",
    "/vidgenerator/social",
    "/vidgenerator/social/",
    "/vidgenerator/chat",
    "/vidgenerator/chat/",
    "/vidgenerator/analytics",
    "/vidgenerator/analytics/",
    "/vidgenerator/aggregator",
    "/vidgenerator/aggregator/",
    "/vidgenerator/debugger",
    "/vidgenerator/debugger/",
    "/vidgenerator/leaderboards",
    "/vidgenerator/leaderboards/",
    "/vidgenerator/quests",
    "/vidgenerator/quests/",
    "/vidgenerator/trophies",
    "/vidgenerator/trophies/",
    "/vidgenerator/metal",
    "/vidgenerator/metal/",
    "/vidgenerator/theme-points",
    "/vidgenerator/theme-points/",
    "/vidgenerator/battlegrounds",
    "/vidgenerator/battlegrounds/",
    "/vidgenerator/champions-league",
    "/vidgenerator/champions-league/",
]

def test_url(url):
    """Test a single URL"""
    try:
        full_url = f"{BASE_URL}{url}"
        response = requests.get(full_url, timeout=10, allow_redirects=True)
        
        # Check if it's HTML 404 error
        is_html_404 = (
            response.status_code == 404 and 
            'text/html' in response.headers.get('Content-Type', '') and
            ('404' in response.text.lower() or 'not found' in response.text.lower())
        )
        
        return {
            'url': url,
            'status_code': response.status_code,
            'is_html_404': is_html_404,
            'content_type': response.headers.get('Content-Type', ''),
            'success': response.status_code == 200 and not is_html_404
        }
    except Exception as e:
        return {
            'url': url,
            'status_code': None,
            'error': str(e),
            'success': False
        }

def main():
    """Test all URLs"""
    print("=" * 70)
    print("TESTING ALL PAGE URLS")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print()
    
    results = []
    passed = 0
    failed = 0
    
    for url in PAGES_TO_TEST:
        print(f"Testing: {url}...", end=" ")
        result = test_url(url)
        results.append(result)
        
        if result.get('success'):
            print(f"[OK] {result['status_code']}")
            passed += 1
        else:
            status = result.get('status_code', 'ERROR')
            if result.get('is_html_404'):
                print(f"[FAIL] {status} - HTML 404 Error")
            elif result.get('error'):
                print(f"[ERROR] {result['error']}")
            else:
                print(f"[FAIL] {status}")
            failed += 1
    
    print()
    print("=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"Total URLs tested: {len(PAGES_TO_TEST)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {(passed/len(PAGES_TO_TEST)*100):.1f}%")
    print()
    
    # Show failed URLs
    failed_urls = [r for r in results if not r.get('success')]
    if failed_urls:
        print("FAILED URLS:")
        print("-" * 70)
        for result in failed_urls:
            url = result['url']
            status = result.get('status_code', 'ERROR')
            error_type = "HTML 404" if result.get('is_html_404') else "HTTP Error"
            print(f"  {url} - {status} ({error_type})")
        print()
    
    # Save results
    output_file = f"page_url_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'base_url': BASE_URL,
            'total_tested': len(PAGES_TO_TEST),
            'passed': passed,
            'failed': failed,
            'success_rate': passed/len(PAGES_TO_TEST)*100,
            'results': results
        }, f, indent=2)
    
    print(f"Results saved to: {output_file}")
    
    return failed == 0

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
