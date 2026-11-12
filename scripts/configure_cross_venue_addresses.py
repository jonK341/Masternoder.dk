#!/usr/bin/env python3
"""Sync Binance ↔ NonKYC deposit/withdraw address book for circle cross-trades.

Usage (on PPP host with vault credentials):
  .venv/bin/python scripts/configure_cross_venue_addresses.py
  .venv/bin/python scripts/configure_cross_venue_addresses.py --json
  .venv/bin/python scripts/configure_cross_venue_addresses.py --enable-xfer-env
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _safe(s: Any) -> str:
    return str(s or "")


def main() -> int:
    ap = argparse.ArgumentParser(description="Configure cross-venue withdraw/deposit addresses")
    ap.add_argument("--json", action="store_true", help="Print full registry JSON")
    ap.add_argument(
        "--enable-xfer-env",
        action="store_true",
        help="Print export lines for CYCLE_CIRCLES_XFER_LIVE when USDC BSC is ready",
    )
    args = ap.parse_args()

    from backend.services.venue_cross_transfer_service import sync_cross_venue_addresses

    out = sync_cross_venue_addresses()
    if args.json:
        print(json.dumps(out, indent=2, default=str))
        return 0 if out.get("success") else 1

    print(
        f"ready_routes={len(out.get('ready_routes') or [])} "
        f"binance_whitelist_rows={out.get('binance_whitelist_count')}"
    )
    for r in out.get("ready_routes") or []:
        print(
            f"  READY {r['from']}→{r['to']} {r['asset']}/{r['network']} "
            f"{_safe(r.get('address_masked'))}"
        )
    cfg = out.get("configure") or {}
    for row in cfg.get("needs_binance_ui") or []:
        print(f"  NEED_BN_UI_WL {row['asset']}/{row['network']} {_safe(row.get('address_masked'))}")
    for row in cfg.get("needs_nonkyc_ui") or []:
        print(f"  NEED_NK_UI_WL {row['asset']}/{row['network']} {_safe(row.get('address_masked'))}")
    for venue, res in (cfg.get("configured") or {}).items():
        print(f"  configured[{venue}]={res.get('configured_coins')}")
    env = cfg.get("env_hint") or {}
    if args.enable_xfer_env and env:
        for k, v in env.items():
            print(f"export {k}={v}")
    elif env.get("CYCLE_CIRCLES_XFER_LIVE") == "1":
        print("USDC BSC BN→NK ready — set CYCLE_CIRCLES_XFER_LIVE=1 to fund circles")
    return 0 if out.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
