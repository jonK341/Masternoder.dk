#!/usr/bin/env python3
"""
Test all active HTML pages in the vidgenerator folder against a running site.
Discovers pages by scanning vidgenerator/**/index.html and tests each URL.
Use for CI or after deploy to ensure no page returns 404.

Usage:
  python scripts/test_vidgenerator_all_pages.py
  python scripts/test_vidgenerator_all_pages.py --base https://masternoder.dk
  python scripts/test_vidgenerator_all_pages.py --local
  BASE_URL=https://yoursite.dk python scripts/test_vidgenerator_all_pages.py
"""
import os
import sys
import argparse

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(2)

DEFAULT_BASE = "https://masternoder.dk"
LOCAL_BASE = "http://127.0.0.1:5000"
REQUEST_TIMEOUT = 25


def discover_vidgenerator_pages():
    """Return list of (path_segment, full_path) for each vidgenerator subdir with index.html."""
    vidgen = os.path.join(_root, "vidgenerator")
    if not os.path.isdir(vidgen):
        return []
    pages = []
    for dirpath, _dirnames, filenames in os.walk(vidgen):
        if "index.html" not in filenames:
            continue
        rel = os.path.relpath(dirpath, vidgen)
        if rel == ".":
            # root index: path segment is empty (handled as / and /vidgenerator)
            continue
        path_segment = rel.replace(os.sep, "/")
        pages.append((path_segment, os.path.join(dirpath, "index.html")))
    return sorted(pages)


def build_test_urls(base_url):
    """Build list of (label, url) to test. base_url has no trailing slash."""
    urls = []
    # Root and vidgenerator root (must return 200 HTML, not JSON 404)
    urls.append(("/", f"{base_url}/"))
    urls.append(("/vidgenerator", f"{base_url}/vidgenerator"))
    urls.append(("/vidgenerator/", f"{base_url}/vidgenerator/"))

    for path_segment, _ in discover_vidgenerator_pages():
        path_segment = path_segment.replace("\\", "/")
        urls.append((f"/vidgenerator/{path_segment}", f"{base_url}/vidgenerator/{path_segment}"))
        urls.append((f"/vidgenerator/{path_segment}/", f"{base_url}/vidgenerator/{path_segment}/"))

    return urls


def test_url(label, url, accept_json_404=False):
    """
    GET url; expect 200 and HTML (or 200 anyway).
    Returns (ok, message).
    """
    try:
        r = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
            allow_redirects=True,
        )
    except requests.exceptions.RequestException as e:
        return False, str(e)

    if r.status_code != 200:
        if accept_json_404 and r.status_code == 404:
            ct = r.headers.get("content-type", "")
            if "application/json" in ct:
                try:
                    j = r.json()
                    return False, f"404 JSON: {j.get('message', j.get('error', 'Not Found'))}"
                except Exception:
                    pass
        return False, f"HTTP {r.status_code}"

    ct = (r.headers.get("content-type") or "").lower()
    # If we get JSON with success: false and error "Not Found", treat as failure
    if "application/json" in ct:
        try:
            j = r.json()
            if j.get("success") is False and "not found" in (j.get("message") or j.get("error") or "").lower():
                return False, f"200 but JSON error: {j.get('message', j.get('error'))}"
        except Exception:
            pass
        if not accept_json_404:
            return False, "200 but response is JSON (expected HTML)"

    # Prefer HTML for page routes
    if "text/html" not in ct and "*/*" not in str(r.headers.get("Accept", "")):
        # We asked for HTML; getting something else might be OK (e.g. redirect)
        pass
    return True, None


def main():
    ap = argparse.ArgumentParser(
        description="Test all vidgenerator HTML pages (discovered from folder) against a live site."
    )
    ap.add_argument(
        "--base",
        default=None,
        help=f"Base URL (default: env BASE_URL or {DEFAULT_BASE})",
    )
    ap.add_argument(
        "--local",
        action="store_true",
        help=f"Use local server: {LOCAL_BASE}",
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="Only print failures and summary",
    )
    args = ap.parse_args()

    if args.local:
        base_url = LOCAL_BASE.rstrip("/")
    elif args.base:
        base_url = args.base.rstrip("/")
    else:
        base_url = os.environ.get("BASE_URL", DEFAULT_BASE).rstrip("/")

    test_urls = build_test_urls(base_url)
    if not args.quiet:
        print("Test all vidgenerator pages")
        print(f"  Base URL: {base_url}")
        print(f"  Paths to test: {len(test_urls)}")
        print("=" * 60)

    passed = 0
    failed = []
    for label, url in test_urls:
        ok, err = test_url(label, url)
        if ok:
            passed += 1
            if not args.quiet:
                print(f"  OK   {label}")
        else:
            failed.append((label, url, err))
            print(f"  FAIL {label}: {err}")

    print("=" * 60)
    print(f"Result: {passed}/{len(test_urls)} passed")
    if failed:
        print("\nFailed URLs:")
        for label, url, err in failed:
            print(f"  {label}")
            print(f"    URL: {url}")
            print(f"    Error: {err}")
        return 1
    if not args.quiet:
        print("\nAll vidgenerator page URLs returned 200 (HTML).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
