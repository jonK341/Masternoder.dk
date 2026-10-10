#!/usr/bin/env python3
"""Post-deploy smoke for MN2 explorer APIs and pages (P4 #169–171, #177).

Usage:
  python scripts/smoke_explorer_deploy.py
  POST_DEPLOY_BASE_URL=https://example.com python scripts/smoke_explorer_deploy.py
  python scripts/smoke_explorer_deploy.py --base-url http://127.0.0.1:5000
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Tuple


DEFAULT_BASE = os.environ.get("POST_DEPLOY_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
SAMPLE_TX = "0" * 64  # invalid but route must respond


def _get(url: str, timeout: float = 15.0) -> Tuple[int, Any]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(body) if body else None
            except json.JSONDecodeError:
                data = body[:200]
            return resp.status, data
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(body) if body else None
        except json.JSONDecodeError:
            data = body[:200]
        return exc.code, data


def _head_status(url: str, timeout: float = 15.0) -> int:
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def run_checks(base: str) -> List[Tuple[str, bool, str]]:
    results: List[Tuple[str, bool, str]] = []

    code, data = _get(f"{base}/api/mn2/network-overview")
    ok = code == 200 and isinstance(data, dict) and data.get("block_height") is not None
    results.append(("network-overview", ok, f"HTTP {code}"))

    code, data = _get(f"{base}/api/mn2/recent-blocks?limit=3")
    ok = code == 200 and isinstance(data, dict) and data.get("success")
    results.append(("recent-blocks", ok, f"HTTP {code}"))

    code, data = _get(f"{base}/api/mn2/services")
    explorer_ok = False
    if code == 200 and isinstance(data, dict):
        svcs = data.get("services") or []
        explorer_ok = any(isinstance(s, dict) and s.get("id") == "explorer" for s in svcs)
    results.append(("services/explorer", explorer_ok, f"HTTP {code}"))

    code, data = _get(f"{base}/api/mn2/rich-list?limit=5")
    rich_ok = code == 200 and isinstance(data, dict) and data.get("success") is True
    note = "empty list ok if index syncing" if rich_ok and not (data.get("rich_list") or data.get("addresses")) else ""
    results.append(("rich-list", rich_ok, f"HTTP {code} {note}".strip()))

    code, data = _get(f"{base}/api/mn2/explorer/status")
    ok = code == 200 and isinstance(data, dict) and data.get("status") in ("healthy", "degraded")
    results.append(("explorer/status", ok, f"HTTP {code} status={data.get('status') if isinstance(data, dict) else '?'}"))
    if isinstance(data, dict):
        rich = ((data.get("checks") or {}).get("rich_list") or {})
        if rich.get("index_synced") is False:
            results.append(("rich-list/index", False, rich.get("note") or "index not synced"))

    page_code = _head_status(f"{base}/explorer/")
    results.append(("explorer hub page", page_code == 200, f"HTTP {page_code}"))

    tx_page = _head_status(f"{base}/explorer/tx/{SAMPLE_TX}")
    results.append(("explorer tx shell", tx_page == 200, f"HTTP {tx_page}"))

    return results


def main() -> int:
    p = argparse.ArgumentParser(description="MN2 explorer post-deploy smoke")
    p.add_argument("--base-url", default=DEFAULT_BASE)
    args = p.parse_args()
    base = args.base_url.rstrip("/")
    print(f"Explorer smoke @ {base}\n")
    failed = 0
    for name, ok, detail in run_checks(base):
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name} — {detail}")
        if not ok:
            failed += 1
    print()
    if failed:
        print(f"{failed} check(s) failed")
        return 1
    print("All explorer smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
