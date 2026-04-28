#!/usr/bin/env python3
"""
Optional browser smoke checks for profile/user account flows.

Requires Playwright and browser binaries. If unavailable, exits 2 with a clear
message so CI can choose to skip it.

Usage:
  set PLATFORM_BASE_URL=http://127.0.0.1:5000
  python scripts/browser_smoke_profile_user.py
"""
from __future__ import annotations

import os
import sys


BASE = os.environ.get("PLATFORM_BASE_URL", "http://127.0.0.1:5000").rstrip("/")


def main() -> int:
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except Exception:
        print("Playwright is not installed. Install it and browser binaries to run browser smoke checks.")
        return 2

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto(BASE + "/profile?tab=account", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("#profile-section-account", timeout=15000)
            assert page.locator("#profile-section-account").is_visible(), "account section should be visible"
            assert page.locator("#account-privacy-card").is_visible(), "privacy card should be visible"
            assert page.locator("#profile-section-activity").count() == 0 or not page.locator("#profile-section-activity").is_visible(), "activity should be hidden in account focus"

            page.goto(BASE + "/profile?tab=wallet", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("#profile-mn2-wallet-card", timeout=15000)
            assert page.locator("#profile-mn2-wallet-card").is_visible(), "wallet card should be visible"

            page.goto(BASE + "/user/", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("#privacy-title", timeout=15000)
            assert page.locator("#sync-user-btn").is_visible(), "sync button should be visible"
            assert page.locator("#save-privacy-btn").is_visible(), "privacy save button should be visible"

            browser.close()
    except PlaywrightError as exc:
        print(f"Playwright runtime unavailable or browser not installed: {exc}")
        return 2
    except AssertionError as exc:
        print(f"Browser smoke failed: {exc}")
        return 1

    print("Browser profile/user smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
