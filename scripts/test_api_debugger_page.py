#!/usr/bin/env python3
"""
Test API Debugger page
"""

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://masternoder.dk/vidgenerator"

def test_api_debugger():
    """Test API debugger page"""
    print("=" * 70)
    print("Testing API Debugger Page")
    print("=" * 70)
    print()
    
    urls = [
        "/api/debugger",
        "/vidgenerator/api/debugger",
        "/api/rettigheder/list",
        "/vidgenerator/api/rettigheder/list",
    ]
    
    for url in urls:
        full_url = BASE_URL + url
        try:
            response = requests.get(full_url, timeout=10, verify=False)
            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} {url}: {response.status_code}")
            
            if response.status_code == 200:
                content = response.text[:200]
                if "API Debugger" in content or "Rettigheder" in content:
                    print(f"   → Page content found!")
                else:
                    print(f"   → Content preview: {content[:100]}...")
            elif response.status_code == 404:
                print(f"   → 404 - Route not found")
            else:
                print(f"   → Status: {response.status_code}")
        except Exception as e:
            print(f"❌ {url}: Error - {e}")
    
    print()
    print("=" * 70)
    print("Checking registered routes...")
    print("=" * 70)
    
    # Check if rettigheder routes exist
    test_urls = [
        "/api/rettigheder/slaa",
        "/api/rettigheder/list",
        "/api/rettigheder/status",
    ]
    
    for url in test_urls:
        full_url = BASE_URL + url
        try:
            # Try GET first (some might be POST only)
            response = requests.get(full_url, timeout=5, verify=False)
            if response.status_code == 405:
                print(f"✅ {url}: 405 (Method Not Allowed - endpoint exists!)")
            elif response.status_code == 200:
                print(f"✅ {url}: 200 OK")
            else:
                print(f"❌ {url}: {response.status_code}")
        except Exception as e:
            print(f"❌ {url}: Error - {e}")

if __name__ == '__main__':
    test_api_debugger()

