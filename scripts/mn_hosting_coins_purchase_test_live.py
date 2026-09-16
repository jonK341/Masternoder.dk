#!/usr/bin/env python3
"""One-off production smoke: top up test user coins + MN hosting pay-coins checkout."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("MN2_TEST_BASE", "https://masternoder.dk")
USER = os.environ.get("MN2_TEST_USER", "shop_mn_purchase_test")
SKIP_PURCHASE = os.environ.get("MN2_TEST_SKIP_PURCHASE", "").strip().lower() in ("1", "true", "yes")


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


def req(method: str, path: str, body: dict | None = None, headers: dict | None = None, timeout: int = 60):
    hdrs = {"Accept": "application/json", "Content-Type": "application/json"}
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


def coins_from_currency(payload: dict | None) -> int:
    if not isinstance(payload, dict):
        return 0
    coins = payload.get("coins")
    if coins is None and isinstance(payload.get("balance"), dict):
        coins = payload["balance"].get("coins")
    if coins is None and isinstance(payload.get("points"), dict):
        coins = payload["points"].get("coins")
    return int(coins or 0)


def main() -> int:
    secret = load_secret()
    print("=== CONFIG ===")
    print(f"base={BASE}")
    print(f"user_id={USER}")
    print(f"ops_secret_loaded={bool(secret)}")

    _, cfg = req("GET", "/api/mn2/masternode/checkout/config")
    sample = (cfg or {}).get("pricing_sample") or {}
    coins_needed = int(sample.get("coins_total") or sample.get("coins_per_slot") or 95)
    print(f"coins_per_slot={sample.get('coins_per_slot')}")
    print(f"coins_total_1slot={sample.get('coins_total', coins_needed)}")
    print(f"slots_available={cfg.get('slots_available') if isinstance(cfg, dict) else None}")

    _, cur_before = req("GET", f"/api/game/shop/currency?user_id={USER}")
    coins_before = coins_from_currency(cur_before)
    print(f"coins_before={coins_before}")

    if coins_before < coins_needed:
        topup = max(coins_needed + 10, 120) - coins_before
        print(f"=== TOP UP +{topup} coins ===")
        for label, path, body in (
            (
                "debugger_add_points",
                "/api/debugger/profile/add-points",
                {
                    "user_id": USER,
                    "point_type": "coins",
                    "amount": topup,
                    "source": "mn_hosting_purchase_test",
                },
            ),
            (
                "points_increment",
                "/api/points/json/increment",
                {"user_id": USER, "point_type": "coins", "amount": topup},
            ),
        ):
            code, res = req("POST", path, body)
            print(f"{label}: HTTP {code} {json.dumps(res)[:300]}")
            if code == 200 and res.get("success") is not False:
                break
        _, cur_mid = req("GET", f"/api/game/shop/currency?user_id={USER}")
        coins_before = coins_from_currency(cur_mid)
        print(f"coins_after_topup={coins_before}")
    else:
        print("skip topup: sufficient balance")

    if SKIP_PURCHASE:
        print("=== SKIP PURCHASE (MN2_TEST_SKIP_PURCHASE=1) ===")
        _, status_list = req("GET", f"/api/shop/purchases?user_id={USER}&limit=5")
        print(json.dumps(status_list, indent=2)[:1500])
        return 0

    print("=== QUOTE ===")
    code, quote = req("POST", "/api/mn2/masternode/checkout/quote", {"user_id": USER, "slots": 1})
    print(f"quote HTTP {code}")
    print(json.dumps(quote, indent=2)[:2000])
    quote_id = (quote or {}).get("quote_id") or (quote or {}).get("order_id")
    if not quote_id:
        print("FAIL: no quote_id")
        return 2

    print("=== PAY COINS ===")
    code, pay = req(
        "POST",
        "/api/mn2/masternode/checkout/pay-coins",
        {"user_id": USER, "quote_id": quote_id},
    )
    print(f"pay HTTP {code}")
    print(json.dumps(pay, indent=2)[:3000])

    _, cur_after = req("GET", f"/api/game/shop/currency?user_id={USER}")
    coins_after = coins_from_currency(cur_after)
    print(f"coins_after={coins_after}")

    print("=== ORDER STATUS ===")
    order_id = pay.get("order_id") or quote_id
    _, status = req("GET", f"/api/mn2/masternode/checkout/status?user_id={USER}&order_id={order_id}")
    print(json.dumps(status, indent=2)[:2000])

    host_ids = pay.get("host_ids") or status.get("host_ids") or []
    print(f"host_ids={host_ids}")

    if secret and host_ids:
        print("=== OPS HOSTS (filtered) ===")
        code, hosts = req("GET", "/api/mn2/masternode/hosts", headers={"X-Ops-Secret": secret})
        print(f"hosts HTTP {code}")
        if isinstance(hosts, dict):
            rows = hosts.get("hosts") or []
            for hid in host_ids:
                match = next(
                    (h for h in rows if h.get("host_id") == hid or h.get("id") == hid),
                    None,
                )
                print(f"host {hid}: {json.dumps(match)[:500] if match else 'NOT FOUND IN REGISTRY'}")

    if secret and pay.get("success"):
        print("=== PROVISION PENDING ===")
        code, provision = req(
            "POST",
            "/api/mn2/masternode/provision-pending?limit=3",
            {},
            headers={"X-Ops-Secret": secret},
            timeout=120,
        )
        print(f"provision HTTP {code}")
        print(json.dumps(provision, indent=2)[:2500])

    summary = {
        "user_id": USER,
        "coins_before": coins_before,
        "coins_after": coins_after,
        "quote_id": quote_id,
        "pay_success": pay.get("success"),
        "pay_error": pay.get("error"),
        "host_ids": host_ids,
        "order_status": status.get("status") if isinstance(status, dict) else None,
    }
    print("=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    if not pay.get("success"):
        return 1
    if status.get("status") != "paid" and not pay.get("already_paid"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
