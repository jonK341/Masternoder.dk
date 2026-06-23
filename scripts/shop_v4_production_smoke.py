#!/usr/bin/env python3
"""
Smoke-test Shop v4.0 HTTP API against any base URL (default: production).

Keep GET paths aligned with shop/index.html ShopV9.runProductLineChecks() so CLI and UI test the same line.

Read-only by default: lists shop items, inventory, purchases, and coin balance.
Optional purchase requires sufficient coins and --attempt-purchase.

--full-line hits monetization, MN2, points, and shop payment-health — use it only against the
real deployed app with all routes registered. It will fail if you point it at a minimal Flask
process that only loads shop_bp; local shop unit tests (minimal app) are the right check for that.

Examples:
  python scripts/shop_v4_production_smoke.py
  python scripts/shop_v4_production_smoke.py --full-line
  python scripts/shop_v4_production_smoke.py --base-url https://masternoder.dk --user-id my_user_id
  python scripts/shop_v4_production_smoke.py --attempt-purchase --item-id some_item_id

Requires: requests (see requirements.txt).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from urllib.parse import quote

from backend.services.shop_api_line_checks import (  # noqa: E402
    expand_path_template,
    kind_ok,
    load_shop_v4_api_line_checks,
)


def _check_full_line(
    s: Any,
    base: str,
    uid: str,
    to: float,
) -> tuple[list[dict[str, Any]], bool]:
    """Same GET sequence as data/shop_v4_api_line_checks.json + ShopV9.runProductLineChecks()."""
    data = load_shop_v4_api_line_checks()
    checks = data.get("checks") or []
    rows: list[dict[str, Any]] = []
    all_ok = True
    for c in checks:
        label = str(c.get("label") or "")
        path = expand_path_template(str(c.get("path_template") or "/"), uid)
        kind = str(c.get("kind") or "success_not_false")
        t0 = time.perf_counter()
        try:
            r = s.get(base + path, timeout=to)
            ms = int((time.perf_counter() - t0) * 1000)
            ok = r.ok
            detail = str(r.status_code)
            ct = r.headers.get("content-type") or ""
            if r.ok and "application/json" in ct:
                j = r.json()
                if isinstance(j, dict):
                    ok = ok and kind_ok(kind, j)
                    err = j.get("error")
                    if err:
                        detail += " " + str(err)[:120]
                else:
                    ok = False
            elif r.ok:
                r.text[:200]
                ok = False
            if not ok:
                all_ok = False
            rows.append({"label": label, "ok": ok, "ms": ms, "detail": detail})
        except Exception as e:
            all_ok = False
            rows.append({"label": label, "ok": False, "ms": 0, "detail": str(e)[:200]})
    return rows, all_ok


def main() -> int:
    p = argparse.ArgumentParser(description="Shop v4 API smoke (production or staging)")
    p.add_argument("--base-url", default="https://masternoder.dk", help="Origin without trailing slash")
    p.add_argument("--user-id", default="smoke_shop_v4_user", help="game_user_id for API calls")
    p.add_argument("--timeout", type=float, default=25.0, help="HTTP timeout seconds per request")
    p.add_argument(
        "--full-line",
        action="store_true",
        help=(
            "Run GET checks matching shop ShopV9.runProductLineChecks() (shop + monetization + MN2 + points); "
            "requires full production stack — not a shop-only Flask app"
        ),
    )
    p.add_argument("--attempt-purchase", action="store_true", help="POST purchase for --item-id if balance allows")
    p.add_argument("--item-id", default="", help="Item id for --attempt-purchase")
    p.add_argument(
        "--promo-check",
        action="store_true",
        help="With --full-line: POST promo validate + apply (checkout + discord paths)",
    )
    args = p.parse_args()

    try:
        import requests
    except ImportError:
        print("Install requests: pip install requests", file=sys.stderr)
        return 1

    base = args.base_url.rstrip("/")
    uid = args.user_id
    to = float(args.timeout)
    print(f"Shop v4 API smoke: base={base} user_id={uid!r} timeout={to}s", flush=True)
    s = requests.Session()
    s.headers.update({"Accept": "application/json"})

    if args.full_line:
        print("Full API line (same as shop page Run checks):", flush=True)
        rows, all_ok = _check_full_line(s, base, uid, to)
        ok_n = sum(1 for r in rows if r["ok"])
        for row in rows:
            mark = "OK " if row["ok"] else "FAIL"
            print(f"  [{mark}] {row['label']}  {row['ms']}ms  {row['detail']}", flush=True)
        print(f"Summary: {ok_n}/{len(rows)} passed", flush=True)
        promo_ok = True
        if args.promo_check:
            print("Promo apply smoke:", flush=True)
            for label, code, expect_mode in (
                ("validate GENERATE10", "GENERATE10", None),
                ("apply GENERATE10", "GENERATE10", "checkout_discount"),
            ):
                t0 = time.perf_counter()
                try:
                    r = s.post(
                        base + ("/api/shop/promo/validate" if label.startswith("validate") else "/api/shop/promo/apply"),
                        json={"code": code, "user_id": uid, "amount_usd": 9.99},
                        headers={"Content-Type": "application/json"},
                        timeout=to,
                    )
                    ms = int((time.perf_counter() - t0) * 1000)
                    ok = r.status_code == 200 and isinstance(r.json(), dict) and r.json().get("success")
                    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
                    if expect_mode and body.get("mode") != expect_mode:
                        ok = False
                    if not ok:
                        promo_ok = False
                    print(f"  [{'OK ' if ok else 'FAIL'}] {label}  {ms}ms  HTTP {r.status_code}", flush=True)
                except Exception as e:
                    promo_ok = False
                    print(f"  [FAIL] {label}  0ms  {e}", flush=True)
        return 0 if all_ok and promo_ok else 1

    def get_json(path: str, **kw):
        r = s.get(base + path, timeout=to, **kw)
        print(f"GET {path} -> {r.status_code}")
        try:
            return r.json()
        except Exception:
            print(r.text[:500])
            return {}

    items = get_json("/api/game/shop/items")
    item_list = items.get("items") or []
    print(f"  items count: {len(item_list)}")
    if item_list:
        sample = item_list[0]
        print(f"  sample: id={sample.get('id')!r} price={sample.get('price')!r}")

    inv = get_json(f"/api/shop/inventory?user_id={quote(uid, safe='')}")
    print(f"  inventory rows: {len((inv or {}).get('inventory') or [])}")

    pur = get_json(f"/api/shop/purchases?user_id={quote(uid, safe='')}&limit=10")
    print(f"  purchases rows: {len((pur or {}).get('purchases') or [])}")

    cur = get_json(f"/api/game/shop/currency?user_id={quote(uid, safe='')}")
    coins = None
    if isinstance(cur, dict):
        coins = cur.get("coins")
        if coins is None and isinstance(cur.get("balance"), dict):
            coins = cur["balance"].get("coins")
    print(f"  coins (if reported): {coins!r}")

    if args.attempt_purchase:
        iid = args.item_id.strip()
        if not iid and item_list:
            for it in item_list:
                pr = it.get("price")
                if isinstance(pr, int) and pr > 0:
                    iid = it.get("id") or ""
                    break
        if not iid:
            print("No --item-id and no coin-priced item found; skipping POST.")
            return 0
        body = {"user_id": uid, "item_id": iid, "quantity": 1}
        r = s.post(
            base + "/api/game/shop/purchase",
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=to,
        )
        print(f"POST /api/game/shop/purchase -> {r.status_code}")
        try:
            print(json.dumps(r.json(), indent=2)[:2000])
        except Exception:
            print(r.text[:500])
        inv2 = get_json(f"/api/shop/inventory?user_id={quote(uid, safe='')}")
        print(f"  inventory rows after: {len((inv2 or {}).get('inventory') or [])}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
