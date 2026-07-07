"""Cross-venue auto-trader — SEARCH continuously and EXECUTE the spatial arb the instant a
profitable price difference appears across Binance / NonKYC / XeggeX.

Unlike the read-only scanner, this acts: on every pass it finds the best cross-venue price
difference (buy cheap on one venue, sell dear on another), and if the edge clears the
configured threshold (net of both venues' fees) it fires both legs as market orders — as
fast as possible — via ``exchange_live_execution_service.execute_spatial_arbitrage``.

Safety:
  * Paper by default. Places REAL orders only when BOTH ``EXCHANGE_ARBITRAGE_LIVE=1`` and
    ``EXCHANGE_CROSS_TRADE_LIVE=1`` are set (plus credentials + funding on both legs).
  * Per-trade notional cap, per-route cooldown, and a daily realized-loss cap that halts.
  * Every decision and fill is written to an append-only audit ledger for later review
    ("examination of details") — symbol, route, gross/net bps, mode, order ids, P&L.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_CFG_PATH = os.path.join(ex._BASE, "data", "exchange_cross_trade_config.json")
_AUDIT_PATH = os.path.join(ex._DATA_DIR, "cross_trade_audit.jsonl")
_STATE_PATH = os.path.join(ex._DATA_DIR, "cross_trade_state.json")

_AGENT_ID = "cross_trade_auto"


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_config() -> Dict[str, Any]:
    return {
        "enabled": False,
        "venues": ["binance", "nonkyc", "xeggex"],
        "min_net_bps": 8.0,          # execute only when the edge (after fees) clears this
        "notional_usd": 25.0,        # per-trade size
        "cooldown_seconds": 3.0,     # min gap between executions on the same route
        "max_trades_per_run": 3,     # cap executions per search pass
        "daily_loss_cap_usd": 10.0,  # halt when realized losses for the day exceed this
    }


def _clampf(v, lo, hi, default):
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return default


def load_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CFG_PATH, None)
    if not isinstance(cfg, dict):
        cfg = _default_config()
        ex._write_json(_CFG_PATH, cfg)
    base = _default_config()
    base.update({k: v for k, v in cfg.items() if v is not None})
    base["min_net_bps"] = _clampf(base.get("min_net_bps"), 0.0, 1e5, 8.0)
    base["notional_usd"] = _clampf(base.get("notional_usd"), 1.0, 1e6, 25.0)
    base["cooldown_seconds"] = _clampf(base.get("cooldown_seconds"), 0.0, 3600.0, 3.0)
    base["max_trades_per_run"] = int(_clampf(base.get("max_trades_per_run"), 1, 50, 3))
    base["daily_loss_cap_usd"] = _clampf(base.get("daily_loss_cap_usd"), 0.0, 1e6, 10.0)
    if not isinstance(base.get("venues"), list) or not base["venues"]:
        base["venues"] = ["binance", "nonkyc", "xeggex"]
    return base


def save_config(patch: Dict[str, Any]) -> Dict[str, Any]:
    cfg = load_config()
    for k, v in (patch or {}).items():
        if k in cfg and v is not None:
            cfg[k] = v
    ex._write_json(_CFG_PATH, cfg)
    return cfg


def set_enabled(enabled: bool) -> Dict[str, Any]:
    cfg = save_config({"enabled": bool(enabled)})
    return {"success": True, "enabled": cfg["enabled"]}


def cross_trade_live_enabled() -> bool:
    """Real cross-venue orders require BOTH the arbitrage gate and the dedicated cross-trade
    gate. Missing either -> paper (search + simulate, no real orders)."""
    def _on(k: str) -> bool:
        return str(os.environ.get(k, "")).strip().lower() in ("1", "true", "yes")
    return _on("EXCHANGE_ARBITRAGE_LIVE") and _on("EXCHANGE_CROSS_TRADE_LIVE")


def _read_state() -> Dict[str, Any]:
    st = ex._read_json(_STATE_PATH, {})
    return st if isinstance(st, dict) else {}


def _write_state(st: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, st)


def _audit(row: Dict[str, Any]) -> None:
    try:
        ex._append_jsonl(_AUDIT_PATH, {"ts": _iso(), **row})
    except Exception:
        pass


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def find_opportunities(*, min_net_bps: Optional[float] = None,
                       notional: Optional[float] = None,
                       venues: Optional[List[str]] = None) -> Dict[str, Any]:
    """Search current cross-venue price differences (delegates to the grid scanner)."""
    from backend.services import exchange_grid_bot_service as grid
    cfg = load_config()
    return grid.scan_cross_venue_differences(
        venues=venues or cfg["venues"],
        min_net_bps=(min_net_bps if min_net_bps is not None else cfg["min_net_bps"]),
        notional_usd=notional or cfg["notional_usd"],
    )


def funding_status(diff: Dict[str, Any]) -> Dict[str, Any]:
    """Can this cross-venue difference actually be executed RIGHT NOW?

    There is no atomic trade that spans two exchanges — each leg settles on its own venue.
    So a cross-venue arb is only executable when BOTH sides are pre-funded: the buy venue holds
    enough quote (USDC/USDT) and the sell venue already holds enough of the coin. This reports
    that readiness per leg (the honest 'is there a real trade here' check)."""
    from backend.services import exchange_venue_api_service as vapi
    cfg = load_config()
    opp = {
        "symbol": diff.get("symbol"), "buy_venue": diff.get("buy_venue"),
        "sell_venue": diff.get("sell_venue"), "buy_ask": diff.get("buy_ask"),
        "notional_usd": float(cfg["notional_usd"]),
    }
    try:
        return vapi.opportunity_funded(opp)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def preview(*, min_net_bps: Optional[float] = None) -> Dict[str, Any]:
    """Search differences and annotate each with real executability (both legs pre-funded).

    ``executable_now_hedged`` = a genuine trade you can fire this instant against balances that
    already sit on both venues (you bank the spread; your net coin exposure stays ~flat).
    ``needs_funding_or_transfer`` = the edge exists but a side isn't funded — you'd have to move
    money onto a venue first (the slow part that no 'wormhole' removes)."""
    cfg = load_config()
    scan = find_opportunities(min_net_bps=(min_net_bps if min_net_bps is not None else 0.0))
    if not scan.get("success"):
        return {"success": False, "error": scan.get("error"), "candidates": []}
    out: List[Dict[str, Any]] = []
    for d in (scan.get("differences") or []):
        f = funding_status(d)
        both = bool(f.get("ok"))
        buy = f.get("buy") or {}
        sell = f.get("sell") or {}
        out.append({
            "symbol": d.get("symbol"), "route": d.get("route"),
            "buy_venue": d.get("buy_venue"), "sell_venue": d.get("sell_venue"),
            "net_bps": d.get("net_bps"), "est_profit_usd": d.get("est_profit_usd"),
            "buy_funded": bool(buy.get("ok")), "buy_need": buy.get("need"), "buy_free": buy.get("free"),
            "sell_funded": bool(sell.get("ok")), "sell_need": sell.get("need"), "sell_free": sell.get("free"),
            "executable_now": both,
            "verdict": "executable_now_hedged" if both else "needs_funding_or_transfer",
            "error": f.get("error"),
        })
    executable = sum(1 for c in out if c["executable_now"])
    return {"success": True, "count": len(out), "executable_now": executable,
            "min_net_bps": (min_net_bps if min_net_bps is not None else cfg["min_net_bps"]),
            "candidates": out,
            "note": "Cross-venue arb is pre-funded/hedged: both sides must hold inventory. "
                    "There is no single atomic trade across two exchanges."}


def rebalance_hint() -> Dict[str, Any]:
    """Summarize accumulated inventory skew from hedged trades and suggest transfers.

    Each hedged fill leaves the buy venue longer the coin and the sell venue shorter it; over
    many fills you must move coin buy→sell (and quote back) to keep trading — the periodic
    rebalance that replaces the impossible atomic cross-exchange trade."""
    state = _read_state()
    skew = state.get("skew") or {}
    moves: List[Dict[str, Any]] = []
    for venue, assets in skew.items():
        for asset, amt in (assets or {}).items():
            if abs(float(amt or 0)) > 1e-9:
                moves.append({"venue": venue, "asset": asset, "net_base": round(float(amt), 8),
                              "direction": "accumulating (move out)" if amt > 0 else "depleting (top up)"})
    moves.sort(key=lambda m: abs(m["net_base"]), reverse=True)
    return {"success": True, "skew": moves,
            "note": "Positive = venue is accumulating that coin (transfer some out); "
                    "negative = venue is running low (top it up)."}


def execute_opportunity(diff: Dict[str, Any], *, dry_run: Optional[bool] = None) -> Dict[str, Any]:
    """Fire both legs for one spotted difference and audit the result."""
    from backend.services.exchange_live_execution_service import execute_spatial_arbitrage
    cfg = load_config()
    opp = {
        "symbol": diff.get("symbol"),
        "buy_venue": diff.get("buy_venue"),
        "sell_venue": diff.get("sell_venue"),
        "buy_ask": diff.get("buy_ask"),
        "sell_bid": diff.get("sell_bid"),
        "net_bps": diff.get("net_bps"),
        "notional_usd": float(cfg["notional_usd"]),
    }
    live = cross_trade_live_enabled() if dry_run is None else (not dry_run)
    res = execute_spatial_arbitrage(opp, agent_id=_AGENT_ID, dry_run=(None if live else True))
    _audit({
        "event": "execute", "symbol": opp["symbol"],
        "route": f'{opp["buy_venue"]}\u2192{opp["sell_venue"]}',
        "net_bps": opp["net_bps"], "notional_usd": opp["notional_usd"],
        "mode": res.get("mode"), "success": res.get("success"), "error": res.get("error"),
        "est_profit_usd": res.get("est_profit_usd"),
        "buy_order_id": (res.get("buy_order") or {}).get("order_id"),
        "sell_order_id": (res.get("sell_order") or {}).get("order_id"),
    })
    return res


def run_once(*, dry_run: Optional[bool] = None, force: bool = False) -> Dict[str, Any]:
    """One search-and-execute pass: find the best differences and fire the ones that clear
    the threshold (respecting per-route cooldown and the daily loss cap)."""
    cfg = load_config()
    if not cfg.get("enabled") and not force:
        return {"success": True, "skipped": True, "reason": "disabled"}

    state = _read_state()
    day = _today()
    if state.get("loss_day") != day:
        state["loss_day"] = day
        state["realized_loss_usd"] = 0.0
    loss_cap = float(cfg["daily_loss_cap_usd"])
    if loss_cap > 0 and float(state.get("realized_loss_usd") or 0) >= loss_cap:
        _write_state(state)
        return {"success": True, "halted": True, "reason": "daily_loss_cap",
                "realized_loss_usd": state.get("realized_loss_usd")}

    scan = find_opportunities()
    if not scan.get("success"):
        _audit({"event": "search_error", "error": scan.get("error")})
        return {"success": False, "error": scan.get("error") or "search_failed",
                "searched": 0, "executed": []}
    diffs = scan.get("differences") or []
    live = cross_trade_live_enabled() if dry_run is None else (not dry_run)

    now = time.time()
    last_exec = dict(state.get("last_exec") or {})
    executed: List[Dict[str, Any]] = []
    min_bps = float(cfg["min_net_bps"])
    for d in diffs[: int(cfg["max_trades_per_run"])]:
        if float(d.get("net_bps") or 0) < min_bps:
            continue
        key = f'{d.get("symbol")}:{d.get("buy_venue")}->{d.get("sell_venue")}'
        if now - float(last_exec.get(key) or 0) < float(cfg["cooldown_seconds"]):
            continue
        res = execute_opportunity(d, dry_run=dry_run)
        last_exec[key] = now
        profit = float(res.get("est_profit_usd") or 0) if res.get("success") else 0.0
        if profit < 0:
            state["realized_loss_usd"] = round(float(state.get("realized_loss_usd") or 0) - profit, 6)
        # Track inventory skew: a hedged fill leaves the buy venue longer the coin and the sell
        # venue shorter it. Accumulated skew tells us when to rebalance across venues.
        if res.get("success"):
            qty = float(res.get("quantity") or 0)
            sym = str(d.get("symbol") or "").upper()
            skew = state.setdefault("skew", {})
            bv = skew.setdefault(str(d.get("buy_venue")), {})
            sv = skew.setdefault(str(d.get("sell_venue")), {})
            bv[sym] = round(float(bv.get(sym) or 0) + qty, 10)
            sv[sym] = round(float(sv.get(sym) or 0) - qty, 10)
        executed.append({
            "route": key, "symbol": d.get("symbol"), "net_bps": d.get("net_bps"),
            "mode": res.get("mode"), "success": res.get("success"),
            "error": res.get("error"), "est_profit_usd": res.get("est_profit_usd"),
        })
    state["last_exec"] = last_exec
    state["last_run_at"] = _iso()
    _write_state(state)
    return {"success": True, "searched": scan.get("count"), "candidates": len(diffs),
            "executed": executed, "live": live, "min_net_bps": min_bps}


def history(limit: int = 50) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    try:
        if os.path.isfile(_AUDIT_PATH):
            with open(_AUDIT_PATH, encoding="utf-8") as fh:
                lines = fh.readlines()[-int(limit):]
            import json as _json
            for ln in lines:
                ln = ln.strip()
                if ln:
                    try:
                        rows.append(_json.loads(ln))
                    except Exception:
                        pass
    except Exception:
        pass
    rows.reverse()
    return {"success": True, "count": len(rows), "events": rows}


def status() -> Dict[str, Any]:
    cfg = load_config()
    state = _read_state()
    hist = history(limit=200)["events"]
    fills = [e for e in hist if e.get("event") == "execute" and e.get("success")]
    realized = round(sum(float(e.get("est_profit_usd") or 0) for e in fills), 6)
    return {
        "success": True,
        "enabled": cfg.get("enabled"),
        "live": cross_trade_live_enabled(),
        "config": {k: cfg.get(k) for k in ("venues", "min_net_bps", "notional_usd",
                                           "cooldown_seconds", "max_trades_per_run",
                                           "daily_loss_cap_usd")},
        "last_run_at": state.get("last_run_at"),
        "realized_loss_usd_today": state.get("realized_loss_usd"),
        "executed_fills": len(fills),
        "realized_pnl_usd": realized,
        "rebalance": rebalance_hint().get("skew"),
        "recent": hist[:12],
    }
