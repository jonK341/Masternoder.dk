#!/usr/bin/env python3
"""Page scan QA — HTTP status, static assets, API smoke, optional Playwright console."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

BASE = os.environ.get("PLATFORM_BASE_URL", "http://127.0.0.1:5000").rstrip("/")

DEFAULT_PAGES = {
    "aggregator": "/aggregator/",
    "profile": "/profile/",
    "camgirls": "/camgirls/",
    "shop": "/shop/",
    "game": "/game/",
}

PAGE_APIS: Dict[str, List[str]] = {
    "aggregator": ["/api/aggregators/catalog?limit=5", "/api/aggregators/progress?user_id=default_user"],
    "profile": ["/api/mn2/balance?user_id=default_user"],
    "camgirls": ["/api/camgirls/performers?user_id=default_user", "/api/camgirls/studio/catalog"],
}


class AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.scripts: List[str] = []
        self.styles: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        attr = dict(attrs)
        if tag == "script" and attr.get("src"):
            self.scripts.append(attr["src"])
        if tag == "link" and attr.get("rel") == "stylesheet" and attr.get("href"):
            self.styles.append(attr["href"])


def fetch(url: str, timeout: int = 20) -> tuple[int, str, Optional[dict]]:
    req = Request(url, headers={"User-Agent": "page-scan-qa/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            ctype = resp.headers.get("Content-Type", "")
            if "json" in ctype:
                try:
                    return resp.status, body, json.loads(body)
                except Exception:
                    return resp.status, body, None
            return resp.status, body, None
    except Exception as e:
        return 0, str(e), None


def scan_page(slug: str, path: str) -> Dict[str, Any]:
    report: Dict[str, Any] = {"page": slug, "path": path, "issues": []}
    url = BASE + path
    status, html, _ = fetch(url)
    report["http_status"] = status
    if status != 200:
        report["issues"].append(f"HTTP {status} for {path}")
        return report

    parser = AssetParser()
    parser.feed(html)
    missing_scripts: List[str] = []
    missing_styles: List[str] = []
    for src in parser.scripts:
        if not src.startswith("/"):
            continue
        s, _, _ = fetch(BASE + src.split("?")[0])
        if s != 200:
            missing_scripts.append(src)
    for href in parser.styles:
        if not href.startswith("/"):
            continue
        s, _, _ = fetch(BASE + href.split("?")[0])
        if s != 200:
            missing_styles.append(href)
    if missing_scripts:
        report["missing_scripts"] = missing_scripts
        report["issues"].append(f"{len(missing_scripts)} missing script(s)")
    if missing_styles:
        report["missing_styles"] = missing_styles
        report["issues"].append(f"{len(missing_styles)} missing stylesheet(s)")

    for api in PAGE_APIS.get(slug, []):
        a_status, _, data = fetch(BASE + api)
        entry = {"url": api, "status": a_status}
        if a_status != 200:
            entry["ok"] = False
            report["issues"].append(f"API {api} -> {a_status}")
        elif isinstance(data, dict) and "success" in data and not data.get("success"):
            entry["ok"] = False
            report["issues"].append(f"API {api} success=false")
        else:
            entry["ok"] = True
        report.setdefault("api_smoke", []).append(entry)

    return report


def playwright_console(pages: List[str]) -> Dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return {"skipped": True, "reason": "playwright not installed"}

    out: Dict[str, Any] = {"skipped": False, "pages": {}}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for slug in pages:
            path = DEFAULT_PAGES[slug]
            page = browser.new_page()
            errors: List[str] = []
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda exc: errors.append(str(exc)))
            try:
                page.goto(BASE + path, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1500)
            except Exception as e:
                errors.append(f"navigation: {e}")
            out["pages"][slug] = errors
            page.close()
        browser.close()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Page scan QA")
    ap.add_argument("--pages", default=",".join(DEFAULT_PAGES.keys()), help="Comma-separated page keys")
    ap.add_argument("--json-out", default="", help="Write full report JSON here")
    ap.add_argument("--no-playwright", action="store_true")
    args = ap.parse_args()

    slugs = [s.strip() for s in args.pages.split(",") if s.strip()]
    reports = []
    total_issues = 0
    for slug in slugs:
        path = DEFAULT_PAGES.get(slug)
        if not path:
            print(f"[SKIP] unknown page key: {slug}")
            continue
        rep = scan_page(slug, path)
        reports.append(rep)
        n = len(rep.get("issues") or [])
        total_issues += n
        tag = "OK" if n == 0 else "ISSUES"
        print(f"[{tag}] {slug} ({path}) — {n} issue(s)")
        for issue in rep.get("issues") or []:
            print(f"       - {issue}")

    pw = {"skipped": True}
    if not args.no_playwright:
        pw = playwright_console(slugs)
        if not pw.get("skipped"):
            for slug, errs in (pw.get("pages") or {}).items():
                if errs:
                    total_issues += len(errs)
                    print(f"[CONSOLE] {slug}: {len(errs)} error(s)")
                    for e in errs[:5]:
                        print(f"       - {e[:120]}")

    full = {"base": BASE, "reports": reports, "playwright": pw}
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(full, f, indent=2)
        print(f"Wrote {args.json_out}")

    if total_issues:
        print(f"\nPage scan finished with {total_issues} issue(s).")
        return 1
    print("\nPage scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
