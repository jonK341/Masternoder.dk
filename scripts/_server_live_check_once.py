#!/usr/bin/env python3
"""Remote or local one-shot: verify USDC Binance live path."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")

from scripts.daemon_env import load_dotenv

load_dotenv()

from backend.services.external_exchange_connector_service import build_pair, _venue_map, fetch_ticker
from backend.services.exchange_venue_api_service import parse_spot_balances, opportunity_funded
from backend.services.exchange_arbitrage_service import scan_opportunities, live_enabled


def main() -> int:
    v = _venue_map()
    print("=== SERVER/LIVE CHECK ===")
    print(f"live_enabled={live_enabled()} BINANCE_QUOTE={os.environ.get('BINANCE_QUOTE', '?')}")
    print(f"binance pair DOGE -> {build_pair(v['binance'], 'DOGE')}")
    print(f"binance ticker DOGE -> {fetch_ticker('binance', 'DOGE')}")
    b = parse_spot_balances("binance", dry_run=False)
    n = parse_spot_balances("nonkyc", dry_run=False)
    from backend.services.exchange_venue_api_service import get_account_balance, venue_has_credentials
    nk = get_account_balance("nonkyc", dry_run=False)
    print(f"nonkyc creds={venue_has_credentials('nonkyc')} api_ok={nk.get('success')} status={nk.get('status_code')}")
    print(f"binance USDC={b.get('USDC')} DOGE={b.get('DOGE')}")
    print(f"nonkyc USDT={n.get('USDT')} DOGE={n.get('DOGE')}")
    scan = scan_opportunities(["DOGE"], ["binance", "nonkyc"], notional_usd=25)
    opps = [o for o in (scan.get("opportunities") or []) if o.get("profitable")]
    print(f"scan source={scan.get('source')} profitable={scan.get('profitable_count')}")
    if scan.get("opportunities"):
        top = scan["opportunities"][0]
        print(f"best DOGE net_bps={top.get('net_bps')} route={top.get('buy_venue')}->{top.get('sell_venue')}")
        if opps:
            print(f"funding={opportunity_funded(opps[0])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
