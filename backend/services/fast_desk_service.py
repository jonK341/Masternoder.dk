"""Action feed for the fast USDT watcher.

Each tick reads the public Binance and NonKYC books for XRP, XLM, ALGO, TRX, and SOL
and writes one plain-language line. It does not withdraw and does not send an order
unless a later caller asks for a paper fill.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_STATE_PATH = os.path.join(ex._DATA_DIR, "fast_desk_state.json")
_MAX_LINES = 40


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def describe_coin(row: Dict[str, Any], *, notional_usd: float = 25.0) -> str:
    """One sentence for a coin row from preview_fast_usdt."""
    sym = str(row.get("symbol") or "?").upper()
    decision = str(row.get("decision") or "")
    net = row.get("net_bps")
    usd = float(row.get("executable_usd") or 0)
    net_txt = f"{net} bps" if net is not None else "no price"
    if decision == "paper_candidate":
        return (
            f"{sym}: gap is {net_txt} and ${usd:.2f} can fill a ${notional_usd:.0f} clip. "
            "Ready for a paper fill."
        )
    if decision == "book_too_thin":
        return (
            f"{sym}: gap is {net_txt}, but only ${usd:.2f} sits on that price. "
            f"Need ${notional_usd:.0f}. Waiting."
        )
    if decision == "below_fees":
        return f"{sym}: prices sit inside the fees ({net_txt}). Waiting."
    return f"{sym}: no book yet. Waiting."


def summarize_tick(coins: List[Dict[str, Any]], *, notional_usd: float = 25.0) -> str:
    parts = [describe_coin(row, notional_usd=notional_usd) for row in coins]
    ready = [str(row.get("symbol") or "").upper() for row in coins if row.get("decision") == "paper_candidate"]
    if ready:
        head = "Paper fill ready for " + ", ".join(ready) + "."
    else:
        head = "No trade."
    return head + " " + " ".join(parts)


def _read_state() -> Dict[str, Any]:
    state = ex._read_json(_STATE_PATH, {})
    return state if isinstance(state, dict) else {}


def _write_state(state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    ex._write_json(_STATE_PATH, state)


def snapshot() -> Dict[str, Any]:
    state = _read_state()
    if not state:
        return {
            "success": True,
            "running": False,
            "lines": [],
            "coins": [],
            "note": "Daemon has not ticked yet.",
            "withdrawal_broadcast": False,
        }
    state["success"] = True
    return state


def tick(*, notional_usd: float = 25.0, min_net_bps: float = 18.0) -> Dict[str, Any]:
    """One watch pass. Public books only. No withdrawal."""
    from backend.services.exchange_cross_trade_service import (
        cross_trade_live_enabled,
        preview_fast_usdt,
    )

    scan = preview_fast_usdt(notional_usd=notional_usd, min_net_bps=min_net_bps)
    coins = list(scan.get("coins") or [])
    text = summarize_tick(coins, notional_usd=notional_usd)
    now = _iso()
    prev = _read_state()
    lines = list(prev.get("lines") or [])
    lines.append({
        "ts": now,
        "text": text,
        "tradable_count": int(scan.get("tradable_count") or 0),
    })
    lines = lines[-_MAX_LINES:]
    state = {
        "success": True,
        "running": True,
        "updated_at": now,
        "mode": "live" if cross_trade_live_enabled() else "paper",
        "live_orders": bool(cross_trade_live_enabled()),
        "withdrawal_broadcast": False,
        "notional_usd": notional_usd,
        "min_net_bps": min_net_bps,
        "fee_bps": scan.get("fee_bps"),
        "tradable_count": int(scan.get("tradable_count") or 0),
        "coins": coins,
        "lines": lines,
        "latest": text,
        "note": (
            "Watching XRP, XLM, ALGO, TRX, and SOL on the public books. "
            "A line is written every pass. No withdrawal is sent from this desk."
        ),
    }
    _write_state(state)
    return state
