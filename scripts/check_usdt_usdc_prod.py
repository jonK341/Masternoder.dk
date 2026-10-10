#!/usr/bin/env python3
"""Probe USDT/USDC pool + swoop functionality (run on server)."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("DAEMON_QUIET", "1")

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_mn2_pool_service import mn2_pool_status
from backend.services.exchange_swoop_service import quote_swoop


def main() -> int:
    pool = mn2_pool_status()
    wallet = ex.get_wallet("default_user")
    assets = wallet.get("assets") or {}

    pairs = [("USDT", "MN2"), ("USDC", "MN2"), ("USDT", "USDC"), ("USDC", "USDT")]
    quotes = {}
    for fr, to in pairs:
        q = quote_swoop("default_user", fr, to, 10.0)
        quotes[f"{fr}->{to}"] = {
            "success": q.get("success"),
            "error": q.get("error"),
            "to_amount": q.get("to_amount"),
            "pool_backed": q.get("pool_backed"),
        }

    test_user = "stable_test_probe"
    ex._adjust_balance(test_user, "USDT", 50.0)
    ex._adjust_balance(test_user, "USDC", 50.0)
    q_exec = quote_swoop(test_user, "USDT", "USDC", 5.0)
    exec_res = None
    if q_exec.get("success"):
        exec_res = ex.execute_swap(
            test_user,
            q_exec["quote_id"],
            q_exec["symbol"],
            q_exec["side"],
            float(q_exec["amount"]),
            q_exec["quote_currency"],
        )
    w_after = ex.get_wallet(test_user)

    out = {
        "pool": {
            "USDT": pool.get("pool_assets", {}).get("USDT"),
            "USDC": pool.get("pool_assets", {}).get("USDC"),
            "gaps": pool.get("pool_gaps"),
        },
        "default_user_balances": {"USDT": assets.get("USDT"), "USDC": assets.get("USDC")},
        "quotes": quotes,
        "usdt_usdc_swap_test": {
            "quote_ok": q_exec.get("success"),
            "execute_ok": bool(exec_res and exec_res.get("success")),
            "error": exec_res.get("error") if exec_res and not exec_res.get("success") else None,
            "usdc_after": (w_after.get("assets") or {}).get("USDC"),
        },
        "all_quotes_ok": all(v.get("success") for v in quotes.values()),
    }
    print(json.dumps(out, default=str))
    return 0 if out["all_quotes_ok"] and out["usdt_usdc_swap_test"]["execute_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
