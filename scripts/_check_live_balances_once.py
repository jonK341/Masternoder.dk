#!/usr/bin/env python3
"""One-shot live balance + arb readiness check (Path B: USDC Binance + USDT NonKYC)."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")

from scripts.daemon_env import load_dotenv

load_dotenv()

from backend.services.exchange_arbitrage_service import live_enabled, scan_opportunities
from backend.services.exchange_venue_api_service import get_account_balance, venue_has_credentials

STABLES = {"USDT", "USDC", "USDC.E", "BUSD", "FDUSD", "DAI"}
COINS = ["DOGE", "XRP", "ETH", "SOL", "BTC", "LTC", "AVAX", "LINK", "TRX"]


def _binance_nonzero() -> dict:
    r = get_account_balance("binance", dry_run=False)
    rows: dict = {}
    if r.get("success") and isinstance(r.get("body"), dict):
        for b in r["body"].get("balances") or []:
            free = float(b.get("free") or 0)
            locked = float(b.get("locked") or 0)
            if free + locked > 1e-8:
                rows[str(b.get("asset") or "").upper()] = {"free": free, "locked": locked, "total": free + locked}
    return {"ok": bool(r.get("success")), "status": r.get("status_code"), "assets": rows}


def _nonkyc_assets() -> dict:
    r = get_account_balance("nonkyc", dry_run=False)
    assets: dict = {}
    body = r.get("body")
    items = []
    if isinstance(body, list):
        items = body
    elif isinstance(body, dict):
        for key in ("balances", "data", "result", "assets"):
            if isinstance(body.get(key), list):
                items = body[key]
                break
        if not items:
            items = [body]
    for row in items:
        if not isinstance(row, dict):
            continue
        sym = str(row.get("symbol") or row.get("asset") or row.get("currency") or "").upper()
        free = float(row.get("available") or row.get("free") or row.get("balance") or 0)
        locked = float(row.get("locked") or row.get("hold") or 0)
        if not sym and row.get("ticker"):
            sym = str(row["ticker"]).upper()
        if free + locked > 1e-8 or sym in STABLES:
            if sym:
                assets[sym] = {"free": free, "locked": locked, "total": free + locked, "raw_keys": list(row.keys())}
    return {"ok": bool(r.get("success")), "status": r.get("status_code"), "assets": assets, "body_sample": body}


def _stable_usd(assets: dict, *names: str) -> float:
    total = 0.0
    for n in names:
        row = assets.get(n.upper()) or assets.get(n)
        if row:
            total += float(row.get("total") or row.get("free") or 0)
    return total


def _coin_total(assets: dict, symbol: str) -> float:
    row = assets.get(symbol.upper())
    return float(row.get("total") or row.get("free") or 0) if row else 0.0


def main() -> int:
    print("=== LIVE READINESS CHECK (Path B) ===")
    print(f"live_enabled: {live_enabled()}")
    print(f"credentials: binance={venue_has_credentials('binance')} nonkyc={venue_has_credentials('nonkyc')}")

    b = _binance_nonzero()
    n = _nonkyc_assets()

    print("\n--- Binance spot (non-zero) ---")
    print(f"API: ok={b['ok']} status={b['status']}")
    for sym, v in sorted(b["assets"].items(), key=lambda x: -x[1]["total"]):
        print(f"  {sym:8s} free={v['free']:.8f} locked={v['locked']:.8f}")

    print("\n--- NonKYC balances ---")
    print(f"API: ok={n['ok']} status={n['status']}")
    for sym, v in sorted(n["assets"].items(), key=lambda x: -x[1]["total"]):
        print(f"  {sym:8s} free={v['free']:.8f} locked={v['locked']:.8f}")

    b_usdc = _stable_usd(b["assets"], "USDC")
    b_usdt = _stable_usd(b["assets"], "USDT")
    n_usdt = _stable_usd(n["assets"], "USDT")
    n_usdc = _stable_usd(n["assets"], "USDC")

    print("\n--- Stable summary ---")
    print(f"  Binance USDC: ${b_usdc:.2f}")
    print(f"  Binance USDT: ${b_usdt:.2f}")
    print(f"  NonKYC USDT:  ${n_usdt:.2f}")
    print(f"  NonKYC USDC:  ${n_usdc:.2f}")

    print("\n--- Coin inventory (for sell legs) ---")
    for sym in COINS:
        bc = _coin_total(b["assets"], sym)
        nc = _coin_total(n["assets"], sym)
        if bc > 0 or nc > 0:
            print(f"  {sym}: binance={bc:.8f} nonkyc={nc:.8f}")

    blockers: list[str] = []
    ready_notes: list[str] = []

    if not b["ok"]:
        blockers.append("Binance API account read failed")
    if not n["ok"]:
        blockers.append("NonKYC API account read failed")
    if b_usdc + b_usdt < 20:
        blockers.append("Binance has low USDC/USDT for buy legs")
    elif b_usdc >= 20:
        ready_notes.append(f"Binance USDC ${b_usdc:.2f} OK for buy leg (USDC quote)")
    elif b_usdt >= 20:
        ready_notes.append(f"Binance USDT ${b_usdt:.2f} OK for buy leg")

    if n_usdt >= 20:
        ready_notes.append(f"NonKYC USDT ${n_usdt:.2f} OK for buy leg on NonKYC")
    elif n_usdt < 5:
        blockers.append(f"NonKYC USDT low (${n_usdt:.2f}) — Path B swap may not have completed")

    has_coin_b = any(_coin_total(b["assets"], s) > 0 for s in COINS)
    has_coin_n = any(_coin_total(n["assets"], s) > 0 for s in COINS)
    if not has_coin_b and not has_coin_n:
        blockers.append("No altcoin inventory on either venue — sell legs will fail until you hold e.g. DOGE/XRP on both")
    else:
        ready_notes.append("Some coin inventory detected")

    scan = scan_opportunities(symbols=COINS[:6], venues=["binance", "nonkyc"], notional_usd=25)
    best = (scan.get("opportunities") or [{}])[0] if scan.get("opportunities") else {}
    prof = scan.get("profitable_count") or 0

    print("\n--- Market (binance + nonkyc, $25 notional) ---")
    print(f"  min_margin_bps: {scan.get('min_margin_bps')}")
    print(f"  profitable_count: {prof}")
    if best:
        print(
            f"  best: {best.get('symbol')} {best.get('net_bps')} bps "
            f"{best.get('buy_venue')} -> {best.get('sell_venue')} "
            f"~${best.get('est_profit_usd')}"
        )
    if prof == 0:
        blockers.append("No spread above margin right now (normal — daemon will wait)")

    print("\n=== VERDICT ===")
    for note in ready_notes:
        print(f"  OK: {note}")
    for bl in blockers:
        print(f"  BLOCKER: {bl}")

    if not blockers or (len(blockers) == 1 and "spread" in blockers[0].lower()):
        print("\n  Funding/API: READY or READY-EXCEPT-MARKET")
    else:
        print("\n  Funding/API: NOT FULLY READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
