#!/usr/bin/env python3
"""
Test https://masternoder.dk/ (primary) and optionally save a screenshot.
Run from project root:  python scripts/test_url_and_screenshot.py

Uses long timeouts (120s) so first request can complete. If playwright is installed,
saves a screenshot to scripts/screenshot_masternoder.png.
"""
import os
import sys

BASE_URL = os.environ.get("BASE_URL", "https://masternoder.dk").rstrip("/")
TIMEOUT = 120


def test_url():
    import urllib.request
    import ssl

    url = f"{BASE_URL}/"
    print(f"Testing {url} (timeout={TIMEOUT}s)...")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0"})
    try:
        r = urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx)
        body = r.read()
        code = r.getcode()
        print(f"  HTTP {code}, {len(body)} bytes")
        # Try to get title
        try:
            text = body.decode("utf-8", errors="replace")
            if "<title>" in text:
                start = text.index("<title>") + 7
                end = text.index("</title>", start)
                print(f"  Title: {text[start:end].strip()[:80]}")
        except Exception:
            pass
        return code == 200, body
    except Exception as e:
        print(f"  Error: {e}")
        return False, None


def take_screenshot():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed. Screenshot skipped. Install with: pip install playwright && playwright install chromium")
        return None
    url = f"{BASE_URL}/"
    out_path = os.path.join(os.path.dirname(__file__), "screenshot_masternoder.png")
    print(f"Screenshot: {url} -> {out_path} (timeout={TIMEOUT}s)...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 720})
            page.goto(url, timeout=TIMEOUT * 1000, wait_until="domcontentloaded")
            page.screenshot(path=out_path, full_page=False)
            browser.close()
        print(f"  Saved: {out_path}")
        return out_path
    except Exception as e:
        print(f"  Screenshot error: {e}")
        return None


def main():
    print("=" * 60)
    print("Test URL and screenshot")
    print("=" * 60)
    ok, _ = test_url()
    if not ok:
        print("\nURL test failed (timeout or error). Try:")
        print("  1. python scripts/fix_502_nginx_only.py   # 300s nginx timeouts")
        print("  2. python fix_502.py                       # restart app + nginx fixes")
        print("  3. Run this script again after the site responds.")
        sys.exit(1)
    take_screenshot()
    print("\nDone.")


if __name__ == "__main__":
    main()
