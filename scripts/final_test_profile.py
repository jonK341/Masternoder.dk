#!/usr/bin/env python3
"""
Final Test Profile - Test with cache-busting headers
"""
import requests
import re

url = "https://masternoder.dk/vidgenerator/profile"
headers = {
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0'
}

print("=" * 70)
print("FINAL TEST WITH CACHE-BUSTING HEADERS")
print("=" * 70)
print()

response = requests.get(url, headers=headers, timeout=10)
html = response.text

print(f"URL: {url}")
print(f"Status: {response.status_code}")
print(f"Size: {len(html)} bytes")
print()

checks = {
    'loadPointsStats': 'loadPointsStats' in html,
    'initProfileManager': 'initProfileManager' in html,
    'loadDetailedStats': 'loadDetailedStats' in html,
    'class ProfileManager': 'class ProfileManager' in html,
}

print("Key Indicators:")
for check, found in checks.items():
    status = "[OK]" if found else "[MISS]"
    print(f"  {status} {check}: {found}")

cache_match = re.search(r'backend-connector\.js\?v=(\d+)', html)
print(f"\nCache version: {cache_match.group(1) if cache_match else 'NOT FOUND'}")

if checks['loadPointsStats'] and checks['initProfileManager']:
    print("\n[SUCCESS] All methods found!")
else:
    print("\n[FAIL] Some methods are missing!")
    print("\nThis suggests:")
    print("  1. Nginx is caching the response")
    print("  2. There's a CDN/proxy in front")
    print("  3. Flask is reading from a different file path")
    print("\nPlease check:")
    print("  - Nginx cache configuration")
    print("  - Flask app file path resolution")
    print("  - Any CDN/proxy settings")
