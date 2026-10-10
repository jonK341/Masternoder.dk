#!/usr/bin/env python3
"""
Production smoke: MN hosting PayPal checkout rail (quote → PayPal order → approve URL).

Does not complete payment in the browser. Set MN2_HOSTING_PAYPAL_CAPTURE=1 and pass
PAYPAL_ORDER_ID after manual approval to exercise capture + provision via ops.

Usage:
  set MN2_TEST_BASE=https://masternoder.dk
  python scripts/mn_hosting_paypal_smoke.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("MN2_TEST_BASE", "https://masternoder.dk").rstrip("/")
USER = os.environ.get("MN2_TEST_USER", "shop_mn_purchase_test")
DO_CAPTURE = os.environ.get("MN2_HOSTING_PAYPAL_CAPTURE", "").strip().lower() in ("1", "true", "yes")
CAPTURE_ORDER = (os.environ.get("PAYPAL_HOSTING_ORDER_ID") or os.environ.get("MN2_HOSTING_ORDER_ID") or "").strip()


def load_secret() -> str:
    for key in ("MN2_OPS_SECRET", "MN2_SCAN_SECRET"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            for key in ("MN2_OPS_SECRET=", "MN2_SCAN_SECRET="):
                if line.startswith(key):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def req(method: str, path: str, body: dict | None = None, headers: dict | None = None, timeout: int = 90):
    hdrs = {"Accept": "application/json"}
    if body is not None:
        hdrs["Content-Type"] = "application/json"
    if headers:
        hdrs.update(headers)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
    request = urllib.request.Request(BASE + path, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, {"raw": raw[:1000]}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, {"raw": raw[:1000]}


def main() -> int:
    secret = load_secret()
    print(f"=== MN hosting PayPal smoke base={BASE} user={USER} ===")

    code, cfg = req("GET", "/api/mn2/masternode/checkout/config")
    if code != 200 or not isinstance(cfg, dict):
        print(f"FAIL config HTTP {code} {cfg}")
        return 2
    sample = cfg.get("pricing_sample") or {}
    rails = cfg.get("payment_rails") or sample.get("payment_rails") or []
    print(f"slots_available={cfg.get('slots_available')} hosted_count={cfg.get('hosted_count')}")
    print(f"price_usd_per_slot={cfg.get('price_usd_per_slot')} paypal_enabled={cfg.get('enabled')}")
    print(f"payment_rails={rails}")
    if "paypal" not in [str(r).lower() for r in rails]:
        print("FAIL: paypal not in payment_rails")
        return 2
    if cfg.get("enabled") is False:
        print("FAIL: PayPal hosting checkout disabled")
        return 2
    if int(cfg.get("slots_available") or 0) < 1:
        print("WARN: no slots_available — quote may fail")

    if DO_CAPTURE and CAPTURE_ORDER:
        print(f"=== CAPTURE order_id={CAPTURE_ORDER} ===")
        code, cap = req(
            "POST",
            "/api/mn2/masternode/checkout/capture",
            {"user_id": USER, "order_id": CAPTURE_ORDER},
        )
        print(f"capture HTTP {code}")
        print(json.dumps(cap, indent=2)[:2500])
        if secret and cap.get("success"):
            code, prov = req(
                "POST",
                "/api/mn2/masternode/provision-pending?limit=2",
                {},
                headers={"X-Ops-Secret": secret},
                timeout=120,
            )
            print(f"provision HTTP {code} {json.dumps(prov)[:1500]}")
        return 0 if cap.get("success") else 1

    print("=== QUOTE (1 slot) ===")
    code, quote = req("POST", "/api/mn2/masternode/checkout/quote", {"user_id": USER, "slots": 1})
    print(f"quote HTTP {code}")
    print(json.dumps(quote, indent=2)[:2000])
    quote_id = (quote or {}).get("quote_id") or (quote or {}).get("order_id")
    if not quote_id:
        print("FAIL: no quote_id")
        return 2

    print("=== PAYPAL ORDER ===")
    code, order = req(
        "POST",
        "/api/mn2/masternode/checkout/order",
        {"user_id": USER, "quote_id": quote_id},
    )
    print(f"order HTTP {code}")
    print(json.dumps(order, indent=2)[:2500])
    if not order.get("success"):
        print("FAIL: PayPal order creation")
        return 1
    approve = order.get("approve_url") or ""
    if not approve:
        print("FAIL: missing approve_url")
        return 1

    print("=== OK ===")
    print(f"order_id={order.get('order_id')} paypal_order_id={order.get('paypal_order_id')}")
    print(f"approve_url={approve[:120]}...")
    print("Complete payment in browser, then:")
    print(f"  set MN2_HOSTING_PAYPAL_CAPTURE=1 & set MN2_HOSTING_ORDER_ID={order.get('order_id')}")
    print("  python scripts/mn_hosting_paypal_smoke.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
