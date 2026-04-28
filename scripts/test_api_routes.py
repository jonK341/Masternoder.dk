#!/usr/bin/env python3
"""
Quick test of API routes after restart
"""

import requests
import sys

BASE_URL = "https://masternoder.dk/vidgenerator"

def test_api_routes():
    """Test API routes"""
    print("=" * 60)
    print("Testing API Routes")
    print("=" * 60)
    print()
    
    routes = [
        "/api/gallery/list",
        "/api/generator/create",
        "/api/game/xp",
        "/api/debug/errors/scan"
    ]
    
    for route in routes:
        url = BASE_URL + route
        try:
            response = requests.get(url, timeout=10, verify=False)
            status = "✅" if response.status_code != 404 else "❌"
            print(f"{status} {route}: {response.status_code}")
            if response.status_code == 404:
                print(f"   → Still 404 - backend blueprints not registered")
        except Exception as e:
            print(f"❌ {route}: Error - {e}")
    
    print()
    print("=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == '__main__':
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    test_api_routes()

