#!/usr/bin/env python3
"""
Check HTML Content - Verify what's actually being served
"""
import requests
import re

BASE_URL = "https://masternoder.dk"
url = f"{BASE_URL}/vidgenerator/profile"

response = requests.get(url, timeout=10)
html = response.text

print("=" * 70)
print("CHECKING HTML CONTENT")
print("=" * 70)
print(f"URL: {url}")
print(f"Status: {response.status_code}")
print(f"Size: {len(html)} bytes")
print()

# Search for specific methods
methods_to_find = [
    'loadPointsStats',
    'initProfileManager',
    'loadDetailedStats',
    'class ProfileManager',
    'backend-connector.js'
]

print("Searching for methods:")
for method in methods_to_find:
    found = method in html
    if found:
        # Find context around the method
        pattern = f'.{{0,100}}{re.escape(method)}.{{0,100}}'
        matches = re.findall(pattern, html, re.IGNORECASE)
        if matches:
            print(f"\n  [OK] {method} found:")
            print(f"    Context: ...{matches[0][:150]}...")
    else:
        print(f"  [MISS] {method} NOT FOUND")

# Check cache version
cache_match = re.search(r'backend-connector\.js\?v=(\d+)', html)
if cache_match:
    print(f"\nCache version found: {cache_match.group(1)}")
else:
    print("\nCache version NOT FOUND")

# Check if initProfileManager function exists
if 'function initProfileManager' in html:
    print("\n[OK] initProfileManager function found")
    # Get the function
    init_match = re.search(r'function initProfileManager\(\)\s*\{[^}]*\}', html, re.DOTALL)
    if init_match:
        print(f"  Function length: {len(init_match.group(0))} chars")
else:
    print("\n[MISS] initProfileManager function NOT found")
    # Check for variations
    if 'initProfileManager' in html:
        print("  But 'initProfileManager' string exists somewhere")
        # Find where it appears
        for i, line in enumerate(html.split('\n')):
            if 'initProfileManager' in line:
                print(f"  Found on line {i}: {line[:100]}")
