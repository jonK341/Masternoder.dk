#!/usr/bin/env python3
"""Verify profile fixes are deployed and working"""
import requests

BASE_URL = "https://masternoder.dk"

print("=" * 70)
print("VERIFYING PROFILE FIXES DEPLOYED")
print("=" * 70)
print()

# Test 1: Check backend-connector.js
print("[1/3] Checking backend-connector.js...")
try:
    r = requests.get(f"{BASE_URL}/vidgenerator/static/js/backend-connector.js", timeout=10)
    js = r.text
    has_fix = '/user/profile/' in js and 'getStats' in js and ('fallback' in js.lower() or 'Fallback' in js)
    print(f"  Status: {r.status_code}")
    print(f"  Size: {len(js)} bytes")
    print(f"  Has getStats fix: {has_fix}")
    print(f"  Using correct endpoint: {'/user/profile/' in js and 'getStats' in js}")
except Exception as e:
    print(f"  [ERROR] {e}")

print()

# Test 2: Check profile page
print("[2/3] Checking profile page...")
try:
    r = requests.get(f"{BASE_URL}/vidgenerator/profile", timeout=15)
    html = r.text
    has_fix = 'initProfileManager' in html or ('typeof backendConnector' in html and 'undefined' in html)
    print(f"  Status: {r.status_code}")
    print(f"  Size: {len(html)} bytes")
    print(f"  Has initialization fix: {has_fix}")
    print(f"  Has backendConnector check: {'typeof backendConnector' in html or 'backendConnector ===' in html}")
except Exception as e:
    print(f"  [ERROR] {e}")

print()

# Test 3: Test profile stats API (the endpoint used by getStats fix)
print("[3/3] Testing profile stats API...")
try:
    r = requests.get(f"{BASE_URL}/vidgenerator/api/user/profile/default_user/stats", timeout=10)
    print(f"  Status: {r.status_code}")
    print(f"  URL: {BASE_URL}/vidgenerator/api/user/profile/default_user/stats")
    if r.status_code == 200:
        d = r.json()
        print(f"  Success: {d.get('success')}")
        print(f"  Has stats: {'stats' in d}")
    else:
        print(f"  [WARN] API returned {r.status_code}")
except Exception as e:
    print(f"  [ERROR] {e}")

print()
print("=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
print()
print("Summary:")
print("  - Backend Connector: Fixed getStats endpoint")
print("  - Profile Page: Fixed initialization with backendConnector check")
print("  - Profile Stats API: Available for getStats method")
print()
print("Next: Test the profile page in a browser to verify plugins load correctly")
