"""Action feed for the fast USDT watcher.

Each tick reads the public Binance and NonKYC books for XRP, XLM, ALGO, TRX, and SOL
and writes one plain-language line. It does not withdraw and does not send an order
unless a later caller asks for a paper fill.

``snapshot()`` also attaches read-only ladder / maker / daemon stats for the desk UI.
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


def _ladder_venue_stats(venue: str) -> Dict[str, Any]:
    from backend.services.exchange_ladder_service import load_state, state_path

    st = load_state(state_path(None, venue))
    orders = [
        o for o in (st.get("orders") or {}).values()
        if isinstance(o, dict) and not o.get("cancelled")
    ]
    buys = sum(1 for o in orders if str(o.get("side") or "").lower() == "buy")
    sells = sum(1 for o in orders if str(o.get("side") or "").lower() == "sell")
    by_sym: Dict[str, int] = {}
    for o in orders:
        sym = str(o.get("symbol") or "?").upper()
        by_sym[sym] = by_sym.get(sym, 0) + 1
    pending = list(st.get("pending") or [])
    return {
        "venue": venue,
        "open": len(orders),
        "buys": buys,
        "sells": sells,
        "pending_exits": len(pending),
        "realized_usd": round(float(st.get("realized_usd") or 0), 4),
        "symbols": by_sym,
    }


def _maker_stats() -> Dict[str, Any]:
    from backend.services.exchange_maker_quote_service import load_config, load_state

    cfg = load_config()
    state = load_state()
    quotes = []
    for key, row in (state or {}).items():
        if not isinstance(row, dict) or not row.get("coid"):
            continue
        quotes.append({
            "key": key,
            "symbol": str(row.get("symbol") or key.split(":")[0]).upper(),
            "side": str(row.get("side") or (key.split(":")[-1] if ":" in key else "")).lower(),
            "price": row.get("price"),
            "qty": row.get("qty"),
            "age_sec": row.get("age_sec"),
        })
    return {
        "venue": cfg.get("venue"),
        "quote": cfg.get("quote"),
        "execute": bool(cfg.get("execute")),
        "symbols": list(cfg.get("symbols") or []),
        "sides": list(cfg.get("sides") or []),
        "clip_usd": cfg.get("clip_usd"),
        "edge_bps": cfg.get("edge_bps"),
        "open": len(quotes),
        "quotes": quotes[:12],
    }


def _daemon_stats() -> Dict[str, Any]:
    try:
        from backend.services.profit_daemon_paths import heartbeat_path
        hb = ex._read_json(heartbeat_path(), {}) or {}
    except Exception:
        hb = {}
    if not isinstance(hb, dict):
        hb = {}
    loops = hb.get("loops") or hb.get("summaries") or {}
    if isinstance(loops, list):
        loop_map = {str(x.get("id") or x.get("name") or i): x for i, x in enumerate(loops) if isinstance(x, dict)}
    elif isinstance(loops, dict):
        loop_map = loops
    else:
        loop_map = {}
    compact = {}
    for name, row in loop_map.items():
        if not isinstance(row, dict):
            compact[name] = {"summary": str(row)[:120]}
            continue
        compact[name] = {
            "summary": str(row.get("summary") or row.get("last") or "")[:160],
            "updated_at": row.get("updated_at") or row.get("ts"),
            "extra": {k: row.get(k) for k in ("zero_fill_streak", "best_bps", "arb_exec") if k in row},
        }
    return {
        "updated_at": hb.get("updated_at") or hb.get("ts"),
        "profile": hb.get("profile") or os.environ.get("EXCHANGE_PROFIT_PROFILE"),
        "mode": hb.get("mode") or os.environ.get("EXCHANGE_DAEMON_MODE"),
        "zero_fill_streak": hb.get("zero_fill_streak"),
        "loops": compact,
    }


def _threshold_stats() -> Dict[str, Any]:
    path = os.path.join(ex._DATA_DIR, "arb_threshold_state.json")
    raw = ex._read_json(path, {})
    return raw if isinstance(raw, dict) else {}


def _fill_model_stats() -> Dict[str, Any]:
    path = os.path.join(ex._DATA_DIR, "fill_model_meta.json")
    raw = ex._read_json(path, {})
    return raw if isinstance(raw, dict) else {}


def _desk_maint_stats() -> Dict[str, Any]:
    path = os.path.join(ex._DATA_DIR, "desk_maintenance_state.json")
    raw = ex._read_json(path, {})
    return raw if isinstance(raw, dict) else {}


def _gap_spark(coins: List[Dict[str, Any]], lines: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compact series for the UI: best net bps per recent pass + current book."""
    series = []
    for row in (lines or [])[-24:]:
        series.append({
            "ts": row.get("ts"),
            "tradable": int(row.get("tradable_count") or 0),
        })
    ranked = sorted(
        [c for c in coins if isinstance(c, dict) and c.get("net_bps") is not None],
        key=lambda c: float(c.get("net_bps") or -1e9),
        reverse=True,
    )
    best = ranked[0] if ranked else None
    return {
        "tradable_series": series,
        "best_symbol": (best or {}).get("symbol"),
        "best_net_bps": (best or {}).get("net_bps"),
        "best_route": (best or {}).get("route"),
        "best_book_usd": (best or {}).get("executable_usd"),
        "ready_count": sum(1 for c in coins if c.get("decision") == "paper_candidate"),
        "thin_count": sum(1 for c in coins if c.get("decision") == "book_too_thin"),
        "fee_blocked": sum(1 for c in coins if c.get("decision") == "below_fees"),
    }


def interesting_stats(state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Read-only desk KPIs from ladder / maker / daemon / fill-model state files."""
    st = state if isinstance(state, dict) else {}
    coins = list(st.get("coins") or [])
    lines = list(st.get("lines") or [])
    ladders = {}
    for venue in ("nonkyc", "binance"):
        try:
            ladders[venue] = _ladder_venue_stats(venue)
        except Exception as exc:
            ladders[venue] = {"venue": venue, "error": str(exc)[:120]}
    try:
        maker = _maker_stats()
    except Exception as exc:
        maker = {"error": str(exc)[:120]}
    try:
        daemon = _daemon_stats()
    except Exception as exc:
        daemon = {"error": str(exc)[:120]}
    open_ladder = sum(int((ladders.get(v) or {}).get("open") or 0) for v in ladders)
    realized = sum(float((ladders.get(v) or {}).get("realized_usd") or 0) for v in ladders)
    gap = _gap_spark(coins, lines)
    return {
        "gap": gap,
        "ladders": ladders,
        "ladder_open": open_ladder,
        "ladder_realized_usd": round(realized, 4),
        "maker": maker,
        "daemon": daemon,
        "threshold": _threshold_stats(),
        "fill_model": _fill_model_stats(),
        "desk_maintenance": _desk_maint_stats(),
        "kpis": {
            "ready": gap.get("ready_count") or 0,
            "best_net_bps": gap.get("best_net_bps"),
            "ladder_open": open_ladder,
            "ladder_realized_usd": round(realized, 4),
            "maker_open": int((maker or {}).get("open") or 0),
            "zero_fill_streak": (daemon or {}).get("zero_fill_streak"),
            "threshold_ready": bool((_threshold_stats() or {}).get("ready")),
            "fill_model_n": (_fill_model_stats() or {}).get("n"),
        },
    }


def snapshot() -> Dict[str, Any]:
    state = _read_state()
    if not state:
        empty = {
            "success": True,
            "running": False,
            "lines": [],
            "coins": [],
            "note": "Daemon has not ticked yet.",
            "withdrawal_broadcast": False,
        }
        empty["stats"] = interesting_stats(empty)
        return empty
    state["success"] = True
    state["stats"] = interesting_stats(state)
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
    best = None
    ranked = [c for c in coins if c.get("net_bps") is not None]
    if ranked:
        best = max(ranked, key=lambda c: float(c.get("net_bps") or -1e9))
    lines.append({
        "ts": now,
        "text": text,
        "tradable_count": int(scan.get("tradable_count") or 0),
        "best_net_bps": (best or {}).get("net_bps"),
        "best_symbol": (best or {}).get("symbol"),
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
    try:
        from backend.services.venue_search_ledger_service import ledger_snapshot, run_search
        run_search(probe=False, notional_usd=notional_usd, scan=scan)
        state["ledgers"] = ledger_snapshot(limit=6)
    except Exception as exc:
        state["ledgers"] = {"error": str(exc)[:180]}
    state["stats"] = interesting_stats(state)
    _write_state(state)
    return state
