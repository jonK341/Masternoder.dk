#!/usr/bin/env python3
"""
Test All Endpoints - Comprehensive testing of all API endpoints
"""
import requests
import sys
import time
from collections import defaultdict

BASE_URL = "https://masternoder.dk"

# Comprehensive list of endpoints to test
ENDPOINTS = [
    # Agent endpoints
    ("Agent Controller Status", "/vidgenerator/api/agent-controller/status"),
    ("Agent Controller All Agents", "/vidgenerator/api/agent-controller/all-agents"),
    ("Agent Skillset Stats", "/vidgenerator/api/agent/skillset/stats"),
    ("Agent Skillset All", "/vidgenerator/api/agent/skillset/all"),
    ("Agent Automation Status", "/vidgenerator/api/agent/automation/status"),
    
    # User Profile endpoints
    ("User Agent Skills", "/vidgenerator/api/user/agent-skills/test_user_1"),
    ("User Profile", "/vidgenerator/api/user/profile/test_user_1"),
    ("User Scraped Info", "/vidgenerator/api/user/scraped-info/test_user_1"),
    
    # Points endpoints
    ("Points Comprehensive", "/vidgenerator/api/points/comprehensive?user_id=test_user_1"),
    ("Points Statistics", "/vidgenerator/api/points/statistics?user_id=test_user_1&days=30"),
    ("Points History Analytics", "/vidgenerator/api/points/history/analytics?user_id=test_user_1&days=30"),
    
    # Monetization endpoints
    ("Monetization Top50", "/vidgenerator/api/monetization/top50?limit=6"),
    ("Monetization Cash", "/vidgenerator/api/monetization/cash?user_id=test_user_1"),
    
    # Tech Tree endpoints
    ("Tech Tree Knowledge", "/vidgenerator/api/tech-tree/knowledge?user_id=test_user_1"),
    ("Tech Tree", "/vidgenerator/api/tech-tree?user_id=test_user_1"),
    
    # Game Mechanics endpoints
    ("Game Mechanics Progress", "/vidgenerator/api/game-mechanics/progress?user_id=test_user_1"),
    ("Game Achievements", "/vidgenerator/api/game/achievements?user_id=test_user_1"),
    
    # Ultra Resource endpoints
    ("Ultra Resource Energy", "/vidgenerator/api/ultra-resource/energy?user_id=test_user_1"),
    
    # Agent endpoints (other)
    ("Agent Get All", "/vidgenerator/api/agent/get-all?user_id=test_user_1"),
    ("Agent Recommendations", "/vidgenerator/api/agent/recommendations?user_id=test_user_1&context=general"),
    
    # Aggregator endpoints
    ("Aggregator Stats", "/vidgenerator/api/aggregator/stats/user/test_user_1"),
    ("Aggregator Unified Dashboard", "/vidgenerator/api/aggregator/unified-dashboard/data?user_id=test_user_1"),
    
    # Intelligence Aggregator
    ("Intelligence Aggregator", "/vidgenerator/api/intelligence-aggregator/status"),
    
    # Trophies
    ("Trophies", "/vidgenerator/api/trophies/user/test_user_1"),
    
    # Debug endpoints
    ("Debugger Status", "/vidgenerator/api/debug/status"),
    
    # Point Calculator
    ("Point Calculator Predict", "/vidgenerator/api/points/calculator/predict?user_id=test_user_1&activity_type=general&base_points=100&days=7"),
]

def test_endpoint(name, endpoint, timeout=10):
    """Test a single endpoint"""
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(url, timeout=timeout, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        })
        
        # Check if it's an HTML 404 page
        is_html_404 = (
            response.status_code == 404 and 
            ('text/html' in response.headers.get('Content-Type', '') or
             '<title>404' in response.text or
             '404 Not Found' in response.text)
        )
        
        if response.status_code == 200:
            return ('success', response)
        elif is_html_404:
            return ('html_404', response)
        elif response.status_code == 404:
            return ('json_404', response)
        else:
            return ('other_error', response)
            
    except requests.exceptions.Timeout:
        return ('timeout', None)
    except requests.exceptions.ConnectionError:
        return ('connection_error', None)
    except Exception as e:
        return ('exception', str(e))

def main():
    print("=" * 70)
    print("Comprehensive Endpoint Testing")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")
    print(f"Total Endpoints: {len(ENDPOINTS)}")
    print()
    
    results = defaultdict(list)
    
    for name, endpoint in ENDPOINTS:
        result_type, response = test_endpoint(name, endpoint)
        results[result_type].append((name, endpoint, response))
        
        # Print status
        if result_type == 'success':
            print(f"✅ {name}")
        elif result_type == 'html_404':
            print(f"❌ {name} - HTML 404 ERROR")
        elif result_type == 'json_404':
            print(f"⚠️  {name} - JSON 404 (expected for some endpoints)")
        elif result_type == 'timeout':
            print(f"⏱️  {name} - TIMEOUT")
        elif result_type == 'connection_error':
            print(f"🔌 {name} - CONNECTION ERROR")
        else:
            print(f"❓ {name} - {result_type}")
        
        time.sleep(0.2)  # Small delay between requests
    
    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    
    success_count = len(results['success'])
    html_404_count = len(results['html_404'])
    json_404_count = len(results['json_404'])
    other_errors = len(results['timeout']) + len(results['connection_error']) + len(results['exception'])
    
    print(f"✅ Working: {success_count}/{len(ENDPOINTS)}")
    print(f"❌ HTML 404 Errors: {html_404_count}/{len(ENDPOINTS)}")
    print(f"⚠️  JSON 404 (may be expected): {json_404_count}/{len(ENDPOINTS)}")
    print(f"❓ Other Errors: {other_errors}/{len(ENDPOINTS)}")
    print()
    
    # List HTML 404 errors (these are the critical ones)
    if results['html_404']:
        print("=" * 70)
        print("❌ CRITICAL: HTML 404 ERRORS (Route Not Found)")
        print("=" * 70)
        for name, endpoint, response in results['html_404']:
            print(f"  - {name}")
            print(f"    URL: {BASE_URL}{endpoint}")
            if response:
                print(f"    Response preview: {response.text[:150]}...")
            print()
    
    # List other issues
    if results['timeout']:
        print("=" * 70)
        print("⏱️  TIMEOUT ERRORS")
        print("=" * 70)
        for name, endpoint, _ in results['timeout']:
            print(f"  - {name}: {BASE_URL}{endpoint}")
        print()
    
    if results['connection_error']:
        print("=" * 70)
        print("🔌 CONNECTION ERRORS")
        print("=" * 70)
        for name, endpoint, _ in results['connection_error']:
            print(f"  - {name}: {BASE_URL}{endpoint}")
        print()
    
    return 0 if html_404_count == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
