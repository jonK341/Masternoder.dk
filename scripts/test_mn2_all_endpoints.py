#!/usr/bin/env python3
"""
Exercise all MN2-related URLs and report pass/fail for debugging.

Usage:
  python scripts/test_mn2_all_endpoints.py [user_id]
  BASE_URL=https://masternoder.dk  (default)
  MN2_SCAN_TOKEN=...  optional; if server has MN2_SCAN_SECRET, set this to test scan/ops

Loads MN2_SCAN_SECRET from project .env as MN2_SCAN_TOKEN if MN2_SCAN_TOKEN not set.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = os.environ.get("BASE_URL", "https://masternoder.dk").rstrip("/")
USER_ID = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("USER_ID", "user_jon_ulrik")
TIMEOUT = 25


def _load_dotenv_token():
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    if not env_path.is_file():
        return ""
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("MN2_SCAN_SECRET=") and not line.startswith("#"):
            _, _, v = line.partition("=")
            return v.strip().strip('"').strip("'")
    return ""


SCAN_TOKEN = (os.environ.get("MN2_SCAN_TOKEN") or _load_dotenv_token() or "").strip()


def get(url: str, headers: dict | None = None, max_body: int = 2000) -> tuple[int, str, dict | None]:
    req = urllib.request.Request(url, headers=headers or {"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read().decode(errors="replace")
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
        body = (e.read() or b"").decode(errors="replace")
    except Exception as e:
        return 0, str(e), None
    data = None
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        pass
    snippet = body if max_body <= 0 or len(body) <= max_body else body[:max_body]
    return code, snippet, data


def post_json(url: str, payload: dict, headers: dict | None = None) -> tuple[int, str, dict | None]:
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        h.update(headers)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read().decode(errors="replace")
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
        body = (e.read() or b"").decode(errors="replace")
    except Exception as e:
        return 0, str(e), None
    data = None
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        pass
    return code, body[:2000], data


def main() -> int:
    print(f"BASE_URL={BASE}")
    print(f"USER_ID={USER_ID}")
    print(f"MN2_SCAN_TOKEN={'(set)' if SCAN_TOKEN else '(not set — ops/scan may return 403)'}")
    print("=" * 60)

    results: list[tuple[str, str, str]] = []

    def ok(name: str, cond: bool, detail: str):
        status = "PASS" if cond else "FAIL"
        results.append((name, status, detail))
        print(f"[{status}] {name}")
        if detail:
            for line in detail.split("\n")[:12]:
                print(f"       {line}")

    # 1) System health (mn2_rpc) — 200 full OK; 503 when overall degraded but mn2 may use Chainz fallback
    code, raw, data = get(f"{BASE}/api/health/system")
    mn2 = (data or {}).get("components", {}).get("mn2_rpc") if isinstance(data, dict) else None
    health_ok = isinstance(data, dict) and mn2 is not None
    if code not in (200, 503):
        health_ok = False
    ok(
        "GET /api/health/system",
        health_ok,
        f"HTTP {code}; mn2_rpc={json.dumps(mn2)[:600] if mn2 else 'missing'}",
    )

    # 2) Price (public)
    code, raw, data = get(f"{BASE}/api/mn2/price")
    ok(
        "GET /api/mn2/price",
        code == 200 and isinstance(data, dict) and data.get("success"),
        f"HTTP {code}; keys={list((data or {}).keys())[:12]}",
    )

    # 3) Balance
    code, raw, data = get(f"{BASE}/api/mn2/balance?user_id={urllib.parse.quote(USER_ID, safe='')}")
    ok(
        "GET /api/mn2/balance",
        code == 200 and isinstance(data, dict) and data.get("success"),
        f"HTTP {code}; mn2_balance={ (data or {}).get('mn2_balance')!s} error={(data or {}).get('error')}",
    )

    # 4) Deposit address
    code, raw, data = get(f"{BASE}/api/mn2/deposit-address?user_id={urllib.parse.quote(USER_ID, safe='')}")
    addr_ok = (
        code == 200
        and isinstance(data, dict)
        and data.get("success")
        and bool((data.get("deposit_address") or "").strip())
    )
    ok(
        "GET /api/mn2/deposit-address",
        addr_ok,
        f"HTTP {code}; success={ (data or {}).get('success')} deposit={(data or {}).get('deposit_address')!s} err={(data or {}).get('error')}",
    )

    # 5) Transactions
    code, raw, data = get(
        f"{BASE}/api/mn2/transactions?user_id={urllib.parse.quote(USER_ID, safe='')}&limit=5"
    )
    ok(
        "GET /api/mn2/transactions",
        code == 200 and isinstance(data, dict) and data.get("success"),
        f"HTTP {code}; n_tx={len((data or {}).get('transactions') or [])}",
    )

    # 6) Profile page (MN2 block) — need enough HTML to find MN2 section
    code, raw, data = get(
        f"{BASE}/profile",
        headers={"User-Agent": "MN2Test/1", "Accept": "text/html"},
        max_body=500_000,
    )
    html_ok = code == 200 and raw and ("MN2 Wallet" in raw or "profile-mn2" in raw)
    ok(
        "GET /profile (MN2 UI)",
        html_ok,
        f"HTTP {code}; len={len(raw)} has_MN2_block={html_ok}",
    )

    # 7) Order payment (coin-priced item shop-1)
    op_url = f"{BASE}/api/mn2/order-payment"
    code, raw, data = post_json(
        op_url,
        {"item_id": "shop-1", "quantity": 1, "user_id": USER_ID},
    )
    # 200 + JSON: full success when RPC returns address; otherwise error explains (e.g. daemon down)
    op_ok = code == 200 and isinstance(data, dict)
    op_note = ""
    if op_ok and not data.get("success"):
        op_note = " (needs masternoder2d on 127.0.0.1:9332 for on-chain checkout)"
    ok(
        "POST /api/mn2/order-payment (shop-1)",
        op_ok,
        f"HTTP {code}; success={ (data or {}).get('success')} err={(data or {}).get('error')} ref={(data or {}).get('payment_ref')}{op_note}",
    )

    # 8) Order payment status (bogus ref → expect 404)
    code, raw, data = get(f"{BASE}/api/mn2/order-payment/status?payment_ref=test_invalid_ref_12345")
    ok(
        "GET /api/mn2/order-payment/status (invalid ref)",
        code == 404,
        f"HTTP {code}; body snippet={raw[:120]}",
    )

    # 9) Withdraw — validation only (amount above min; invalid address; must not succeed as real send)
    w_url = f"{BASE}/api/mn2/withdraw"
    code, raw, data = post_json(
        w_url,
        {"address": "MN2InvalidAddress123456789", "amount": 0.01, "user_id": USER_ID},
    )
    # Expect 400 invalid address, 403 verification, 429 rate limit, or 500 if RPC validateaddress unreachable
    withdraw_expected = (
        code in (400, 403, 429, 500)
        and isinstance(data, dict)
        and not data.get("success")
    )
    ok(
        "POST /api/mn2/withdraw (invalid addr — expect 4xx/5xx, no success)",
        withdraw_expected,
        f"HTTP {code}; error={(data or {}).get('error')}",
    )

    # 10) Ops / stats
    hdrs = {}
    if SCAN_TOKEN:
        hdrs["X-Scanner-Token"] = SCAN_TOKEN
    code, raw, data = get(f"{BASE}/api/mn2/ops/stats", headers=hdrs)
    ok(
        "GET /api/mn2/ops/stats",
        code == 200 and isinstance(data, dict) and data.get("success") is not False,
        f"HTTP {code}; success={ (data or {}).get('success')} err={(data or {}).get('error')}",
    )

    # 11) Ops verified-users
    code, raw, data = get(f"{BASE}/api/mn2/ops/verified-users", headers=hdrs)
    ok(
        "GET /api/mn2/ops/verified-users",
        code == 200 and isinstance(data, dict),
        f"HTTP {code}; success={ (data or {}).get('success')} err={(data or {}).get('error')}",
    )

    # 12) Ops create-addresses GET count=1 (needs RPC when pool empty; should always return 200 JSON after fix)
    code, raw, data = get(f"{BASE}/api/mn2/ops/create-addresses?count=1", headers=hdrs)
    create_ok = code == 200 and isinstance(data, dict)
    cnote = ""
    if create_ok and not data.get("success"):
        cnote = " (RPC required to mint new pool addresses)"
    ok(
        "GET /api/mn2/ops/create-addresses?count=1",
        create_ok,
        f"HTTP {code}; success={ (data or {}).get('success')} err={(data or {}).get('error')} count={ (data or {}).get('count')}{cnote}",
    )

    # 13) Scan deposits POST
    scan_headers: dict = {}
    if SCAN_TOKEN:
        scan_headers["X-Scanner-Token"] = SCAN_TOKEN
    code, raw, data = post_json(f"{BASE}/api/mn2/scan-deposits", {}, headers=scan_headers or None)
    # 200 + success = scanner ran; 403 = set MN2_SCAN_TOKEN; 500 = RPC/daemon issue (expected until daemon runs)
    scan_err = (data or {}).get("error") if isinstance(data, dict) else raw
    scan_ok = code == 200 and isinstance(data, dict) and data.get("success") is True
    if code == 403:
        scan_ok = True
        detail = f"HTTP 403 (set MN2_SCAN_TOKEN from .env to test authenticated scan) err={(data or {}).get('error') if isinstance(data, dict) else raw[:200]}"
    elif code == 500:
        scan_ok = False
        detail = f"HTTP 500 — start masternoder2d on 127.0.0.1:9332 and ensure MN2_RPC_* in app env. err={str(scan_err)[:320]}"
    else:
        detail = f"HTTP {code}; success={ (data or {}).get('success') if isinstance(data, dict) else None} err={str(scan_err)[:300]}"
    ok(
        "POST /api/mn2/scan-deposits",
        scan_ok,
        detail,
    )

    print("=" * 60)
    fails = [r for r in results if r[1] == "FAIL"]
    print(f"Summary: {len(results) - len(fails)}/{len(results)} passed, {len(fails)} failed")
    if fails:
        for name, st, det in fails:
            print(f"  FAIL: {name} — {det[:200]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
