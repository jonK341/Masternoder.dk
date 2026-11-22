#!/usr/bin/env python3
"""One multi-daemon for ALL exchange coin wallets.

Handles balances, deposit address sync, deposit crediting, and withdraw readiness
for every tradeable coin. Do NOT run one daemon per coin — this covers them all.

Also folds in the MN2 on-chain deposit scanner tick so MN2 stays in the same loop.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")

try:
    from scripts.daemon_env import load_dotenv
except Exception:
    def load_dotenv() -> None:
        return None


def _mode_banner() -> str:
    try:
        from backend.services.exchange_binance_withdraw_service import (
            binance_credentials,
            binance_withdraw_live_enabled,
            binance_withdraw_live_gate_reason,
        )
        creds = binance_credentials()
        has = bool(creds.get("api_key") and creds.get("api_secret"))
        live = binance_withdraw_live_enabled()
        if not has:
            return "PAPER (no BINANCE_API_KEY/SECRET or vault binance_api_key/secret)"
        if not live:
            reason = binance_withdraw_live_gate_reason() or "unknown_gate"
            return f"READ-ONLY keys present; withdraw gated ({reason})"
        return "LIVE-ready (credentials + payout gates on)"
    except Exception as exc:
        return f"unknown ({exc})"


def run_once(*, force: bool = False) -> dict:
    from backend.services.exchange_multi_wallet_service import run_multi_wallet_tick
    return run_multi_wallet_tick(force=force)


def main() -> int:
    parser = argparse.ArgumentParser(description="Exchange multi-wallet daemon (all coins)")
    parser.add_argument("--once", action="store_true", help="Run one tick and exit")
    parser.add_argument("--force", action="store_true", help="Force deposit intent scan")
    parser.add_argument("--interval", type=int, default=120, help="Seconds between ticks")
    args = parser.parse_args()
    load_dotenv()

    mode = _mode_banner()
    if args.once:
        res = run_once(force=args.force)
        print(f"[multi-wallet-daemon] mode={mode}")
        print(res)
        return 0

    print(f"[multi-wallet-daemon] interval={args.interval}s mode={mode}")
    while True:
        try:
            res = run_once(force=args.force)
            dep = res.get("deposit_addresses") or {}
            modes = {(row or {}).get("mode") for row in (dep.get("synced") or [])}
            print(
                f"[multi-wallet-daemon] tick={res.get('tick_count')} "
                f"credited={(res.get('deposit_scan') or {}).get('credited')} "
                f"users={res.get('ensure_users')} "
                f"addr_modes={sorted(m for m in modes if m)}"
            )
        except KeyboardInterrupt:
            print("[multi-wallet-daemon] stopped")
            return 0
        except Exception as exc:
            print(f"[multi-wallet-daemon] error: {exc}")
        time.sleep(max(30, int(args.interval)))


if __name__ == "__main__":
    raise SystemExit(main())
