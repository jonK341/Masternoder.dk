#!/usr/bin/env python3
"""Check live-trading readiness and optionally import API keys from .env into vault."""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _load_dotenv() -> None:
    path = os.path.join(ROOT, ".env")
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def main() -> int:
    parser = argparse.ArgumentParser(description="Live exchange trading readiness")
    parser.add_argument("--import-keys", action="store_true", help="Import *_API_KEY/SECRET from .env to vault")
    args = parser.parse_args()
    _load_dotenv()

    from backend.services.exchange_live_execution_service import live_readiness
    from backend.services.exchange_treasury_service import treasury_status

    if args.import_keys:
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
        print("Imported vault keys for:", imported or "(none found in .env)")

    ready = live_readiness()
    tre = treasury_status()
    print("=== Live readiness ===")
    print(f"  EXCHANGE_ARBITRAGE_LIVE gate: {ready.get('live_gate')}")
    print(f"  Live-ready venues: {ready.get('live_venue_count')}")
    print(f"  Can trade external-only arb: {ready.get('can_trade_external')}")
    for v in ready.get("venues") or []:
        if v.get("credentials_configured") or v.get("live_ready"):
            print(f"    {v['venue_id']}: creds={v['credentials_configured']} live_ready={v['live_ready']}")
    print("=== Treasury (MasterNoder stash) ===")
    print(f"  User: {tre.get('treasury_user_id')}")
    print(f"  MN2 balance: {tre.get('mn2_balance')}")
    print(f"  Stashed USD (ledger): {tre.get('ledger_stashed_usd')}")
    if not ready.get("live_gate"):
        print("\nTo enable live: set EXCHANGE_ARBITRAGE_LIVE=1 in .env and restart daemons.")
    if ready.get("live_venue_count", 0) < 2:
        print("Need API keys for at least 2 venues (e.g. binance + nonkyc) in vault.")
        print("Run: python scripts/configure_live_trading.py --import-keys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
