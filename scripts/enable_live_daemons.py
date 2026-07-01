#!/usr/bin/env python3
"""Switch exchange daemons from paper to live cash-transfer mode."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.daemon_env import load_dotenv, live_status


def _ensure_env_flag(key: str, value: str) -> bool:
    path = os.path.join(ROOT, ".env")
    if not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    found = False
    out = []
    for line in lines:
        if line.strip().startswith(f"{key}="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{key}={value}")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out).rstrip() + "\n")
    os.environ[key] = value
    return True


def main() -> int:
    load_dotenv()
    _ensure_env_flag("EXCHANGE_ARBITRAGE_LIVE", "1")
    _ensure_env_flag("EXCHANGE_PAYOUT_PAYPAL_LIVE", "1")
    if not os.environ.get("EXCHANGE_VAULT_KEY", "").strip():
        fallback = os.environ.get("AGENT_CASINO_SECRET", "").strip()
        if fallback:
            _ensure_env_flag("EXCHANGE_VAULT_KEY", fallback)

    conn_path = os.path.join(ROOT, "data", "exchange_connectors_config.json")
    with open(conn_path, encoding="utf-8") as fh:
        conn = json.load(fh)
    conn["mode"] = "live"
    with open(conn_path, "w", encoding="utf-8") as fh:
        json.dump(conn, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    payout_path = os.path.join(ROOT, "data", "crypto_exchange", "payout_config.json")
    payout = {}
    if os.path.isfile(payout_path):
        with open(payout_path, encoding="utf-8") as fh:
            payout = json.load(fh)
    payout["auto_sweep"] = True
    payout.setdefault("destination", "paypal")
    payout.setdefault("paypal", {"email": "", "share_pct": 0.5, "connected": False})
    payout.setdefault("min_sweep_usd", 50.0)
    with open(payout_path, "w", encoding="utf-8") as fh:
        json.dump(payout, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    email = (os.environ.get("EXCHANGE_PAYOUT_PAYPAL_EMAIL") or "").strip()
    if email:
        from backend.services.exchange_payout_service import configure_paypal

        share = os.environ.get("EXCHANGE_PAYOUT_PAYPAL_SHARE_PCT", "50")
        configure_paypal(email, share_pct=float(share))

    if os.environ.get("EXCHANGE_VAULT_KEY"):
        from backend.services import exchange_secrets_vault_service as vault
        venues = ["binance", "okx", "bybit", "nonkyc", "kucoin", "xeggex"]
        imported = []
        for vid in venues:
            key = os.environ.get(f"{vid.upper()}_API_KEY") or os.environ.get(f"{vid}_api_key")
            sec = os.environ.get(f"{vid.upper()}_API_SECRET") or os.environ.get(f"{vid}_api_secret")
            if key and sec:
                vault.set_secret(f"{vid}_api_key", key)
                vault.set_secret(f"{vid}_api_secret", sec)
                imported.append(vid)
        if imported:
            print("Imported vault keys for:", imported)

    st = live_status()
    print("=== Live daemon mode enabled ===")
    print(json.dumps(st, indent=2))
    if not email:
        print("\nSet EXCHANGE_PAYOUT_PAYPAL_EMAIL in .env, then run:")
        print("  python scripts/configure_paypal_payout.py")
    if not st.get("can_trade_external"):
        print("\nAdd venue API keys to .env (BINANCE_API_KEY/SECRET, etc.) and run:")
        print("  python scripts/configure_live_trading.py --import-keys")
    print("\nRestart daemons (option 7/9 in run_daemons.cmd) to pick up live mode.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
