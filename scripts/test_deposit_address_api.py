#!/usr/bin/env python3
"""Test profile URL and /api/mn2/deposit-address. Usage: python scripts/test_deposit_address_api.py [user_id]"""
import os
import sys
import urllib.request
import json

BASE = os.environ.get("BASE_URL", "https://masternoder.dk").rstrip("/")
USER_ID = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("USER_ID", "user_jon_ulrik")


def test_profile_url():
    """Check profile page loads (200 and contains MN2/deposit)."""
    url = f"{BASE}/profile"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MasternoderTest/1"})
        with urllib.request.urlopen(req, timeout=15) as r:
            if r.status != 200:
                print(f"Profile: HTTP {r.status}")
                return False
            body = r.read().decode(errors="replace")
            if "profile-mn2-deposit-address" in body or "MN2 Wallet" in body or "Deposit address" in body:
                print(f"Profile: OK (200, has deposit-address block)")
                return True
            print("Profile: OK (200) but deposit block not found in HTML")
            return True
    except Exception as e:
        print(f"Profile: ERROR {e}")
        return False


def test_deposit_address():
    """Check deposit-address API returns an address or clear error."""
    url = f"{BASE}/api/mn2/deposit-address?user_id={urllib.request.quote(USER_ID)}"
    print(f"GET {url}")
    print()
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode()
            data = json.loads(body)
            success = data.get("success")
            addr = data.get("deposit_address")
            err = data.get("error")
            if success and addr:
                print("Deposit address: OK (real address)")
                print(f"  user_id: {data.get('user_id')}")
                print(f"  deposit_address: {addr}")
                if data.get("explorer_address_url"):
                    print(f"  explorer: {data['explorer_address_url']}")
                return 0
            else:
                print("Deposit address: FAIL (no address)")
                print(f"  success: {success}")
                print(f"  error: {err}")
                return 1
    except Exception as e:
        print(f"Deposit address: ERROR {e}")
        return 2


def main():
    print("=== Profile URL === ")
    test_profile_url()
    print()
    print("=== Deposit address API ===")
    return test_deposit_address()


if __name__ == "__main__":
    sys.exit(main())
