#!/usr/bin/env python3
"""
Comprehensive Reality Check
Tests all pages and APIs to identify real errors
"""
import requests
import json
from datetime import datetime
from urllib.parse import urljoin

BASE_URL = "https://masternoder.dk"

# Extended list of pages to test
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
    "/vidgenerator/points",
    "/vidgenerator/points/",
    "/vidgenerator/metal",
    "/vidgenerator/metal/",
    "/vidgenerator/theme-points",
    "/vidgenerator/theme-points/",
    "/vidgenerator/battlegrounds",
    "/vidgenerator/battlegrounds/",
    "/vidgenerator/champions-league",
    "/vidgenerator/champions-league/",
    "/vidgenerator/editor",
    "/vidgenerator/monetization",
    "/vidgenerator/milkyway",
    "/vidgenerator/rights-law",
    "/vidgenerator/victory-tech-tree",
    "/vidgenerator/danish-divine-tech-tree",
    "/vidgenerator/academic-perspective",
    "/vidgenerator/theme_premium",
    "/vidgenerator/time-achievement-guides",
    "/vidgenerator/beta_testing",
    "/vidgenerator/unified_dashboard",
    "/vidgenerator/advanced_calculator",
    "/vidgenerator/agent_support",
]

# Critical API endpoints to test
API_ENDPOINTS_TO_TEST = [
    "/vidgenerator/api/shop/currency?user_id=default_user",
    "/vidgenerator/api/user/profile/default_user/display",
    "/vidgenerator/api/user/onboarding/status/default_user",
    "/vidgenerator/api/agent-controller/status",
    "/vidgenerator/api/agent/skillset/stats",
    "/vidgenerator/api/points/comprehensive?user_id=default_user",
]

def test_url(url, is_api=False):
    """Test a single URL with detailed error reporting"""
    try:
        full_url = f"{BASE_URL}{url}"
        response = requests.get(full_url, timeout=10, allow_redirects=True)
        
        # Check for different error types
        is_html_404 = (
            response.status_code == 404 and 
            'text/html' in response.headers.get('Content-Type', '') and
            ('404' in response.text.lower() or 'not found' in response.text.lower())
        )
        
        is_500_error = response.status_code == 500
        is_403_error = response.status_code == 403
        is_401_error = response.status_code == 401
        
        # Check for JSON errors in API responses
        json_error = None
        if is_api and response.headers.get('Content-Type', '').startswith('application/json'):
            try:
                data = response.json()
                if not data.get('success', True):
                    json_error = data.get('error', 'Unknown error')
            except:
                pass
        
        return {
            'url': url,
            'status_code': response.status_code,
            'is_html_404': is_html_404,
            'is_500_error': is_500_error,
            'is_403_error': is_403_error,
            'is_401_error': is_401_error,
            'json_error': json_error,
            'content_type': response.headers.get('Content-Type', ''),
            'content_length': len(response.content),
            'success': response.status_code == 200 and not is_html_404 and not json_error,
            'error_type': (
                'HTML 404' if is_html_404 else
                '500 Server Error' if is_500_error else
                '403 Forbidden' if is_403_error else
                '401 Unauthorized' if is_401_error else
                f'JSON Error: {json_error}' if json_error else
                f'HTTP {response.status_code}' if response.status_code != 200 else None
            )
        }
    except requests.exceptions.Timeout:
        return {
            'url': url,
            'status_code': None,
            'error': 'Timeout',
            'success': False,
            'error_type': 'Timeout'
        }
    except requests.exceptions.ConnectionError:
        return {
            'url': url,
            'status_code': None,
            'error': 'Connection Error',
            'success': False,
            'error_type': 'Connection Error'
        }
    except Exception as e:
        return {
            'url': url,
            'status_code': None,
            'error': str(e),
            'success': False,
            'error_type': 'Exception'
        }

def main():
    """Run comprehensive reality check"""
    print("=" * 70)
    print("COMPREHENSIVE REALITY CHECK")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print()
    
    # Test pages
    print("Testing Pages...")
    print("-" * 70)
    page_results = []
    for url in PAGES_TO_TEST:
        print(f"Testing: {url}...", end=" ")
        result = test_url(url, is_api=False)
        page_results.append(result)
        
        if result.get('success'):
            print(f"[OK] {result['status_code']}")
        else:
            error_type = result.get('error_type', 'Unknown')
            print(f"[FAIL] {error_type}")
    
    print()
    
    # Test APIs
    print("Testing API Endpoints...")
    print("-" * 70)
    api_results = []
    for url in API_ENDPOINTS_TO_TEST:
        print(f"Testing: {url}...", end=" ")
        result = test_url(url, is_api=True)
        api_results.append(result)
        
        if result.get('success'):
            print(f"[OK] {result['status_code']}")
        else:
            error_type = result.get('error_type', 'Unknown')
            print(f"[FAIL] {error_type}")
    
    print()
    print("=" * 70)
    print("REALITY CHECK RESULTS")
    print("=" * 70)
    
    # Page statistics
    all_page_results = page_results
    page_passed = sum(1 for r in all_page_results if r.get('success'))
    page_failed = len(all_page_results) - page_passed
    
    print(f"\nPAGES:")
    print(f"  Total tested: {len(all_page_results)}")
    print(f"  Passed: {page_passed}")
    print(f"  Failed: {page_failed}")
    print(f"  Success rate: {(page_passed/len(all_page_results)*100):.1f}%")
    
    # API statistics
    api_passed = sum(1 for r in api_results if r.get('success'))
    api_failed = len(api_results) - api_passed
    
    print(f"\nAPI ENDPOINTS:")
    print(f"  Total tested: {len(api_results)}")
    print(f"  Passed: {api_passed}")
    print(f"  Failed: {api_failed}")
    print(f"  Success rate: {(api_passed/len(api_results)*100):.1f}%")
    
    # Overall statistics
    all_results = all_page_results + api_results
    total_passed = sum(1 for r in all_results if r.get('success'))
    total_failed = len(all_results) - total_passed
    
    print(f"\nOVERALL:")
    print(f"  Total tested: {len(all_results)}")
    print(f"  Passed: {total_passed}")
    print(f"  Failed: {total_failed}")
    print(f"  Success rate: {(total_passed/len(all_results)*100):.1f}%")
    
    # Error breakdown
    print(f"\nERROR BREAKDOWN:")
    error_types = {}
    for result in all_results:
        if not result.get('success'):
            error_type = result.get('error_type', 'Unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
    
    for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {error_type}: {count}")
    
    # Failed URLs by type
    print(f"\nFAILED URLS BY TYPE:")
    for error_type in sorted(set(r.get('error_type') for r in all_results if not r.get('success'))):
        failed_urls = [r['url'] for r in all_results if not r.get('success') and r.get('error_type') == error_type]
        print(f"\n  {error_type} ({len(failed_urls)}):")
        for url in failed_urls[:10]:  # Show first 10
            print(f"    - {url}")
        if len(failed_urls) > 10:
            print(f"    ... and {len(failed_urls) - 10} more")
    
    # Save detailed results
    output_file = f"reality_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'base_url': BASE_URL,
            'summary': {
                'total_tested': len(all_results),
                'total_passed': total_passed,
                'total_failed': total_failed,
                'success_rate': total_passed/len(all_results)*100,
                'pages': {
                    'tested': len(all_page_results),
                    'passed': page_passed,
                    'failed': page_failed,
                    'success_rate': page_passed/len(all_page_results)*100
                },
                'apis': {
                    'tested': len(api_results),
                    'passed': api_passed,
                    'failed': api_failed,
                    'success_rate': api_passed/len(api_results)*100
                },
                'error_breakdown': error_types
            },
            'page_results': all_page_results,
            'api_results': api_results
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    
    return total_failed == 0

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
