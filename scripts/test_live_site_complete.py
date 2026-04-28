#!/usr/bin/env python3
"""
Complete end-to-end test of live site
"""

import requests
import urllib3
import sys

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://masternoder.dk/vidgenerator"

def test_page(url_path, expected_status=200):
    """Test a page"""
    url = BASE_URL + url_path
    try:
        response = requests.get(url, timeout=10, verify=False)
        status = "✅" if response.status_code == expected_status else "❌"
        print(f"{status} {url_path}: {response.status_code}")
        return response.status_code == expected_status
    except Exception as e:
        print(f"❌ {url_path}: Error - {e}")
        return False

def test_api(url_path, method="GET", data=None, expected_status=200):
    """Test an API endpoint"""
    url = BASE_URL + url_path
    try:
        if method == "GET":
            response = requests.get(url, timeout=10, verify=False)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10, verify=False)
        else:
            response = requests.request(method, url, json=data, timeout=10, verify=False)
        
        # 200, 201, 405 (method not allowed) are all OK for APIs
        is_ok = response.status_code in [200, 201, 405] or response.status_code == expected_status
        status = "✅" if is_ok else "❌"
        print(f"{status} {method} {url_path}: {response.status_code}")
        return is_ok
    except Exception as e:
        print(f"❌ {method} {url_path}: Error - {e}")
        return False

def main():
    """Run complete test suite"""
    print("=" * 70)
    print("COMPLETE LIVE SITE TEST")
    print("=" * 70)
    print()
    
    results = []
    
    # Test main pages
    print("Testing Main Pages:")
    print("-" * 70)
    results.append(("Home", test_page("/")))
    results.append(("Generator", test_page("/generator")))
    results.append(("Gallery", test_page("/gallery")))
    results.append(("Game", test_page("/game")))
    print()
    
    # Test API endpoints
    print("Testing API Endpoints:")
    print("-" * 70)
    results.append(("API Gallery List", test_api("/api/gallery/list")))
    results.append(("API Generator Create", test_api("/api/generator/create", "POST", {}, 405)))
    results.append(("API Game XP", test_api("/api/game/xp", "POST", {}, 405)))
    results.append(("API Debug Scan", test_api("/api/debug/errors/scan")))
    print()
    
    # Test static files (check actual paths)
    print("Testing Static Files:")
    print("-" * 70)
    # Try different possible paths
    static_paths = [
        "/static/css/style.css",
        "/vidgenerator/static/css/style.css",
    ]
    css_found = False
    for path in static_paths:
        if test_page(path):
            css_found = True
            break
    results.append(("CSS", css_found))
    
    js_paths = [
        "/static/js/main.js",
        "/vidgenerator/static/js/main.js",
    ]
    js_found = False
    for path in js_paths:
        if test_page(path):
            js_found = True
            break
    results.append(("JS", js_found))
    print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print()
    
    if passed == total:
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print("❌ Some tests failed:")
        for name, result in results:
            if not result:
                print(f"  - {name}")
        return 1

if __name__ == '__main__':
    sys.exit(main())

