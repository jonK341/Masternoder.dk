"""Profit Path Protocol (PPP) — structured logging for arb/trade research.

Append-only ledger rows capture scan → execute → stash/sweep decisions so routes
can be searched, compared, and improved over time.
"""
from __future__ import annotations

import json
import os
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_CFG_PATH = os.path.join(ex._DATA_DIR, "profit_path_protocol.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "profit_path_ledger.jsonl")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _short_id() -> str:
    return uuid.uuid4().hex[:8]


def _parse_ts(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def load_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CFG_PATH, {})
    if not isinstance(cfg, dict):
        cfg = {}
    cfg.setdefault("enabled", True)
    cfg.setdefault("max_ledger_rows", 50000)
    cfg.setdefault("retention_days", 90)
    cfg.setdefault("default_threshold_bps", 30)
    cfg.setdefault("default_ledger_mode", "auto")
    cfg.setdefault("skill_evolution_on_profit", True)
    cfg.setdefault("mask_balances", True)
    cfg.setdefault("balance_summary_venues", ["binance", "nonkyc", "coinbase", "bingx", "xeggex"])
    cfg.setdefault("suggestion_lookback_hours", 168)
    cfg.setdefault("export_default_limit", 200)
    cfg.setdefault("rotation_lookback_hours", 24)
    cfg.setdefault("rotation_live_enabled", False)
    cfg.setdefault("rotation_auto_execute", False)
    cfg.setdefault("rotation_auto_max_usd_per_tick", 100)
    cfg.setdefault("rotation_auto_types", [
        "internal_stable_swap", "external_market_buy", "external_market_sell", "reduce_notional",
    ])
    return cfg


def save_config_patch(patch: Dict[str, Any]) -> Dict[str, Any]:
    cfg = load_config()
    for k, v in patch.items():
        if v is not None:
            cfg[k] = v
    ex._write_json(_CFG_PATH, cfg)
    return {"success": True, "config": load_config()}


def ledger_mode(explicit: Optional[str] = None) -> str:
    """Resolve PPP row mode: live when arb live gate is on (unless forced in config)."""
    if explicit in ("live", "paper"):
        return explicit
    cfg = load_config()
    forced = str(cfg.get("default_ledger_mode") or "auto").lower()
    if forced in ("live", "paper"):
        return forced
    try:
        from backend.services.exchange_arbitrage_service import live_enabled
        return "live" if live_enabled() else "paper"
    except Exception:
        return "paper"


def _maybe_evolve_skills(row: Dict[str, Any]) -> None:
    cfg = load_config()
    if not cfg.get("skill_evolution_on_profit", True):
        return
    try:
        from backend.services.exchange_profit_agent_skills_service import on_ledger_profit_event
        on_ledger_profit_event(row)
    except Exception:
        pass


def _read_ledger(*, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    if not os.path.isfile(_LEDGER_PATH):
        return []
    rows: List[Dict[str, Any]] = []
    with open(_LEDGER_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                rows.append(row)
    if limit and len(rows) > limit:
        return rows[-limit:]
    return rows


def _append_row(row: Dict[str, Any]) -> None:
    cfg = load_config()
    if not cfg.get("enabled", True):
        return
    if "mode" not in row or row.get("mode") in (None, "", "auto"):
        row["mode"] = ledger_mode(str(row.get("mode") or ""))
    ex._append_jsonl(_LEDGER_PATH, row)
    exec_block = row.get("execution") or {}
    if row.get("phase") == "execute" and exec_block.get("success"):
        if float(exec_block.get("realized_pnl_usd") or 0) > 0 or float(row.get("notional_usd") or 0) > 0:
            _maybe_evolve_skills(row)
    max_rows = int(cfg.get("max_ledger_rows") or 50000)
    if max_rows <= 0:
        return
    try:
        if os.path.isfile(_LEDGER_PATH):
            with open(_LEDGER_PATH, "r", encoding="utf-8") as f:
                count = sum(1 for _ in f)
            if count > max_rows:
                trimmed = _read_ledger(limit=max_rows)
                tmp = _LEDGER_PATH + ".tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    for r in trimmed:
                        f.write(json.dumps(r, default=str) + "\n")
                os.replace(tmp, _LEDGER_PATH)
    except Exception:
        pass


def _mask_amount(value: float) -> str:
    """Bucket balance into coarse bands — no exact secrets."""
    v = float(value or 0)
    if v <= 0:
        return "0"
    if v < 25:
        return "<25"
    if v < 100:
        return "25-99"
    if v < 500:
        return "100-499"
    if v < 2000:
        return "500-1999"
    return "2000+"


def balances_snapshot(*, venues: Optional[List[str]] = None) -> Dict[str, str]:
    """Masked quote/base summary for configured venues."""
    cfg = load_config()
    venue_ids = venues or list(cfg.get("balance_summary_venues") or [])
    out: Dict[str, str] = {}
    try:
        from backend.services import exchange_venue_api_service as vapi
        for vid in venue_ids:
            if not vapi.venue_has_credentials(vid):
                out[f"{vid}_status"] = "no_creds"
                continue
            bal = vapi.get_account_balance(vid, dry_run=False)
            if not bal.get("success"):
                err = str(bal.get("error") or "api_error")
                if "401" in err:
                    out[f"{vid}_status"] = "401"
                else:
                    out[f"{vid}_status"] = "error"
                continue
            bals = vapi.parse_spot_balances(vid, dry_run=False)
            quote = vapi.venue_quote_asset(vid)
            key = f"{vid}_{quote.lower()}"
            out[key] = _mask_amount(float(bals.get(quote) or 0))
            for sym in ("USDC", "USDT", "BTC", "XRP"):
                if sym in bals and float(bals.get(sym) or 0) > 0:
                    out[f"{vid}_{sym.lower()}"] = _mask_amount(float(bals[sym]))
    except Exception:
        pass
    return out


def _split_bps(opp: Optional[Dict[str, Any]], threshold_bps: float) -> Dict[str, float]:
    if not opp:
        return {
            "gross_bps": 0.0,
            "fee_bps": 0.0,
            "transfer_bps": 0.0,
            "net_bps": 0.0,
            "threshold_bps": threshold_bps,
        }
    gross = float(opp.get("gross_bps") or 0)
    total_fee = float(opp.get("fee_bps") or 0)
    transfer = float(opp.get("transfer_bps") or opp.get("transfer_cost_bps") or 0)
    if transfer <= 0 and opp.get("taker_fee_bps") is not None:
        transfer = max(0.0, total_fee - float(opp.get("taker_fee_bps") or 0))
    elif transfer <= 0:
        transfer = max(0.0, total_fee * 0.25)
    taker = max(0.0, total_fee - transfer)
    return {
        "gross_bps": round(gross, 2),
        "fee_bps": round(taker, 2),
        "transfer_bps": round(transfer, 2),
        "net_bps": round(float(opp.get("net_bps") or gross - total_fee), 2),
        "threshold_bps": round(threshold_bps, 2),
    }


def _venues_from_opp(opp: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not opp:
        return {"buy": "", "sell": ""}
    return {
        "buy": str(opp.get("buy_venue") or ""),
        "sell": str(opp.get("sell_venue") or ""),
    }


def record_scan(
    *,
    agent_id: str,
    strategy: str = "spatial_arb",
    best: Optional[Dict[str, Any]] = None,
    threshold_bps: Optional[float] = None,
    mode: str = "",
    decision: str = "skip",
    skip_reason: Optional[str] = None,
    notional_usd: Optional[float] = None,
    latency_ms: Optional[int] = None,
    venues: Optional[List[str]] = None,
    path_id: Optional[str] = None,
) -> str:
    """Log one scan evaluation row (max one per agent per tick at call site)."""
    cfg = load_config()
    if not cfg.get("enabled", True):
        return path_id or _short_id()
    pid = path_id or _short_id()
    thr = float(threshold_bps if threshold_bps is not None else cfg.get("default_threshold_bps") or 30)
    bps = _split_bps(best, thr)
    sym = str((best or {}).get("symbol") or "")
    notion = float(notional_usd if notional_usd is not None else (best or {}).get("notional_usd") or 0)
    row = {
        "ts": _iso(),
        "path_id": pid,
        "phase": "scan",
        "agent_id": agent_id,
        "strategy": strategy,
        "venues": _venues_from_opp(best),
        "symbol": sym,
        "notional_usd": round(notion, 2),
        **bps,
        "decision": decision,
        "skip_reason": skip_reason or "",
        "balances_snapshot": balances_snapshot(venues=venues),
        "execution": {},
        "mode": mode,
        "latency_ms": latency_ms,
    }
    _append_row(row)
    return pid


def record_execution(
    *,
    path_id: str,
    agent_id: str,
    opp: Optional[Dict[str, Any]] = None,
    exec_res: Optional[Dict[str, Any]] = None,
    strategy: str = "spatial_arb",
    threshold_bps: Optional[float] = None,
    mode: Optional[str] = None,
    decision: Optional[str] = None,
    skip_reason: Optional[str] = None,
    phase: str = "execute",
    latency_ms: Optional[int] = None,
    venues: Optional[List[str]] = None,
) -> str:
    """Log fill or failed attempt."""
    cfg = load_config()
    if not cfg.get("enabled", True):
        return path_id
    thr = float(threshold_bps if threshold_bps is not None else cfg.get("default_threshold_bps") or 30)
    bps = _split_bps(opp, thr)
    res = exec_res or {}
    ok = bool(res.get("success"))
    profit = float(res.get("est_profit_usd") or res.get("realized_pnl_usd") or 0) if ok else 0.0
    trade_id = str(res.get("trade_id") or res.get("order_id") or "")
    if not trade_id:
        buy_o = (res.get("buy_order") or {})
        sell_o = (res.get("sell_order") or {})
        trade_id = str(buy_o.get("order_id") or sell_o.get("order_id") or res.get("executed_at") or "")[:32]
    dec = decision
    if not dec:
        if ok:
            dec = str(res.get("mode") or mode or "paper")
            if dec not in ("fill", "paper", "live"):
                dec = "live" if dec == "live" else "paper"
        else:
            dec = "attempt"
    exec_mode = str(mode or res.get("mode") or "paper")
    row = {
        "ts": _iso(),
        "path_id": path_id,
        "phase": phase,
        "agent_id": agent_id,
        "strategy": strategy,
        "venues": _venues_from_opp(opp),
        "symbol": str((opp or {}).get("symbol") or ""),
        "notional_usd": round(float((opp or {}).get("notional_usd") or res.get("notional_usd") or 0), 2),
        **bps,
        "decision": dec,
        "skip_reason": skip_reason or (str(res.get("error") or "") if not ok else ""),
        "balances_snapshot": balances_snapshot(venues=venues),
        "execution": {
            "trade_id": trade_id,
            "fill_usd": round(float(res.get("notional_usd") or (opp or {}).get("notional_usd") or 0), 2) if ok else 0.0,
            "realized_pnl_usd": round(profit, 4),
            "success": ok,
        },
        "mode": exec_mode,
        "latency_ms": latency_ms,
    }
    _append_row(row)
    return path_id


def record_event(
    *,
    phase: str,
    agent_id: str = "",
    strategy: str = "",
    symbol: str = "",
    mode: str = "",
    decision: str = "attempt",
    skip_reason: str = "",
    notional_usd: float = 0,
    execution: Optional[Dict[str, Any]] = None,
    path_id: Optional[str] = None,
) -> str:
    """Lightweight row for stash/sweep/cross-trade events."""
    cfg = load_config()
    pid = path_id or _short_id()
    if not cfg.get("enabled", True):
        return pid
    row = {
        "ts": _iso(),
        "path_id": pid,
        "phase": phase,
        "agent_id": agent_id,
        "strategy": strategy,
        "venues": {"buy": "", "sell": ""},
        "symbol": symbol,
        "notional_usd": round(float(notional_usd or 0), 2),
        "gross_bps": 0.0,
        "fee_bps": 0.0,
        "transfer_bps": 0.0,
        "net_bps": 0.0,
        "threshold_bps": float(cfg.get("default_threshold_bps") or 30),
        "decision": decision,
        "skip_reason": skip_reason,
        "balances_snapshot": {},
        "execution": execution or {},
        "mode": mode,
        "latency_ms": None,
    }
    _append_row(row)
    return pid


def search_paths(
    *,
    agent_id: Optional[str] = None,
    symbol: Optional[str] = None,
    hours: Optional[float] = None,
    min_net_bps: Optional[float] = None,
    decision: Optional[str] = None,
    venue: Optional[str] = None,
    phase: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """Query ledger with common research filters."""
    rows = _read_ledger()
    cutoff: Optional[datetime] = None
    if hours is not None and hours > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=float(hours))
    out: List[Dict[str, Any]] = []
    for row in reversed(rows):
        if cutoff:
            ts = _parse_ts(str(row.get("ts") or ""))
            if ts and ts < cutoff:
                continue
        if agent_id and str(row.get("agent_id") or "") != agent_id:
            continue
        if symbol and str(row.get("symbol") or "").upper() != symbol.upper():
            continue
        if min_net_bps is not None and float(row.get("net_bps") or 0) < float(min_net_bps):
            continue
        if decision and str(row.get("decision") or "") != decision:
            continue
        if phase and str(row.get("phase") or "") != phase:
            continue
        if venue:
            v = str(venue).lower()
            venues = row.get("venues") or {}
            if v not in (str(venues.get("buy") or "").lower(), str(venues.get("sell") or "").lower()):
                continue
        out.append(row)
        if len(out) >= max(1, int(limit or 50)):
            break
    return {"success": True, "count": len(out), "paths": out}


def profit_path_summary(*, hours: Optional[float] = None) -> Dict[str, Any]:
    """Aggregates for hit rate, avg net bps, skip reasons, best routes."""
    h24 = hours if hours is not None else 24
    rows = search_paths(hours=h24, limit=10000).get("paths") or []
    rows7d = search_paths(hours=168, limit=10000).get("paths") or []

    scans = [r for r in rows if r.get("phase") == "scan"]
    attempts = [r for r in rows if r.get("phase") == "execute"]
    fills = [r for r in attempts if r.get("decision") in ("fill", "paper", "live") and (r.get("execution") or {}).get("success")]

    skip_reasons = Counter(str(r.get("skip_reason") or "unknown") for r in rows if r.get("decision") == "skip" and r.get("skip_reason"))
    route_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"scans": 0, "attempts": 0, "fills": 0, "net_bps_sum": 0.0})

    for r in rows:
        v = r.get("venues") or {}
        route = f"{v.get('buy','?')}→{v.get('sell','?')}"
        sym = str(r.get("symbol") or "")
        key = f"{sym}:{route}" if sym else route
        route_stats[key]["scans"] += 1 if r.get("phase") == "scan" else 0
        if r.get("phase") == "execute":
            route_stats[key]["attempts"] += 1
            route_stats[key]["net_bps_sum"] += float(r.get("net_bps") or 0)
            if (r.get("execution") or {}).get("success"):
                route_stats[key]["fills"] += 1

    def _avg_net(route_rows: List[Dict[str, Any]]) -> float:
        execs = [r for r in route_rows if r.get("phase") == "execute"]
        if not execs:
            scans_only = [r for r in route_rows if r.get("phase") == "scan"]
            if not scans_only:
                return 0.0
            return round(sum(float(r.get("net_bps") or 0) for r in scans_only) / len(scans_only), 2)
        return round(sum(float(r.get("net_bps") or 0) for r in execs) / len(execs), 2)

    routes_24h = []
    route_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        v = r.get("venues") or {}
        key = f"{r.get('symbol','')}:{v.get('buy','?')}→{v.get('sell','?')}"
        route_groups[key].append(r)
    for key, grp in route_groups.items():
        st = route_stats[key]
        routes_24h.append({
            "route": key,
            "scans": st["scans"],
            "attempts": st["attempts"],
            "fills": st["fills"],
            "avg_net_bps": _avg_net(grp),
            "hit_rate_pct": round(100.0 * st["fills"] / st["attempts"], 1) if st["attempts"] else 0.0,
        })
    routes_24h.sort(key=lambda x: (x["fills"], x["avg_net_bps"]), reverse=True)

    routes_7d = []
    route_groups7: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows7d:
        v = r.get("venues") or {}
        key = f"{r.get('symbol','')}:{v.get('buy','?')}→{v.get('sell','?')}"
        route_groups7[key].append(r)
    for key, grp in route_groups7.items():
        execs = [r for r in grp if r.get("phase") == "execute"]
        fills_n = sum(1 for r in execs if (r.get("execution") or {}).get("success"))
        routes_7d.append({
            "route": key,
            "attempts": len(execs),
            "fills": fills_n,
            "avg_net_bps": _avg_net(grp),
        })
    routes_7d.sort(key=lambda x: (x["fills"], x["avg_net_bps"]), reverse=True)

    hit_rate = round(100.0 * len(fills) / len(attempts), 1) if attempts else 0.0
    avg_net = 0.0
    net_rows = [r for r in rows if float(r.get("net_bps") or 0) != 0]
    if net_rows:
        avg_net = round(sum(float(r.get("net_bps") or 0) for r in net_rows) / len(net_rows), 2)

    return {
        "success": True,
        "window_hours": h24,
        "scan_count": len(scans),
        "attempt_count": len(attempts),
        "fill_count": len(fills),
        "hit_rate_pct": hit_rate,
        "avg_net_bps": avg_net,
        "top_skip_reasons": [{"reason": k, "count": v} for k, v in skip_reasons.most_common(8)],
        "best_routes_24h": routes_24h[:10],
        "best_routes_7d": routes_7d[:10],
    }


def suggest_improvements(*, hours: Optional[float] = None) -> Dict[str, Any]:
    """Rule-based hints from recent ledger patterns."""
    cfg = load_config()
    lookback = float(hours if hours is not None else cfg.get("suggestion_lookback_hours") or 168)
    rows = search_paths(hours=lookback, limit=5000).get("paths") or []
    suggestions: List[Dict[str, Any]] = []

    skip_reasons = Counter(str(r.get("skip_reason") or "") for r in rows if r.get("skip_reason"))
    for reason, count in skip_reasons.most_common(5):
        if count < 2:
            continue
        if reason == "below_threshold" or reason == "no_profitable_spread":
            suggestions.append({
                "priority": "medium",
                "category": "threshold",
                "message": f"{count} scans skipped — spread below threshold; consider lowering min_margin_bps or focusing hotter symbols.",
                "evidence": {"skip_reason": reason, "count": count},
            })
        elif reason == "insufficient_venue_balance" or reason == "insufficient_balance":
            suggestions.append({
                "priority": "high",
                "category": "funding",
                "message": f"{count} skips from insufficient balance — pre-fund quote on buy venue and base coin on sell venue.",
                "evidence": {"skip_reason": reason, "count": count},
            })
        elif "401" in reason:
            suggestions.append({
                "priority": "high",
                "category": "api",
                "message": f"API auth failures ({reason}) — refresh vault keys or disable blocked venue.",
                "evidence": {"skip_reason": reason, "count": count},
            })
        elif reason == "api_error" or reason == "no_quote":
            suggestions.append({
                "priority": "medium",
                "category": "connectivity",
                "message": f"{count} failures from {reason} — check venue ticker/API health.",
                "evidence": {"skip_reason": reason, "count": count},
            })

    # Balance snapshot hints from recent scans
    fund_hints: Counter = Counter()
    for r in rows:
        if r.get("skip_reason") not in ("insufficient_venue_balance", "insufficient_balance"):
            continue
        sym = str(r.get("symbol") or "")
        v = r.get("venues") or {}
        if sym:
            fund_hints[f"fund {sym} on {v.get('sell') or 'sell venue'}"] += 1
        snap = r.get("balances_snapshot") or {}
        for k, band in snap.items():
            if k.endswith("_status") and band in ("401", "error"):
                venue = k.replace("_status", "")
                suggestions.append({
                    "priority": "high",
                    "category": "api",
                    "message": f"{venue} {band} blocks routes — fix credentials or remove from agent venues.",
                    "evidence": {"venue": venue, "status": band},
                })
            if band in ("0", "<25") and "_usdc" in k or "_usdt" in k:
                suggestions.append({
                    "priority": "high",
                    "category": "funding",
                    "message": f"Low {k.replace('_', ' ')} ({band}) — increase quote inventory to fit configured notional.",
                    "evidence": {"balance_key": k, "band": band},
                })

    for hint, count in fund_hints.most_common(3):
        suggestions.append({
            "priority": "high",
            "category": "funding",
            "message": f"{hint} ({count} recent skips).",
            "evidence": {"hint": hint, "count": count},
        })

    # Notional vs balance band
    for r in rows:
        if r.get("skip_reason") != "insufficient_venue_balance":
            continue
        notion = float(r.get("notional_usd") or 0)
        snap = r.get("balances_snapshot") or {}
        for k, band in snap.items():
            if band == "25-99" and notion > 79:
                suggestions.append({
                    "priority": "medium",
                    "category": "sizing",
                    "message": f"Lower notional to fit ~$79 on {k.replace('_', ' ')} (current ${notion:.0f}).",
                    "evidence": {"notional_usd": notion, "balance_key": k, "band": band},
                })
                break

    # Swap rotation hints from funding gaps
    try:
        from backend.services.exchange_swap_rotation_service import suggest_swap_actions

        rot = suggest_swap_actions(hours=min(lookback, 48), limit=5)
        for act in (rot.get("actions") or [])[:5]:
            suggestions.append({
                "priority": act.get("priority") or "high",
                "category": "rotation",
                "message": act.get("label") or act.get("reason") or "Swap rotation action",
                "evidence": {
                    "type": act.get("type"),
                    "reason": act.get("reason"),
                    "top25_items": act.get("top25_items"),
                },
            })
    except Exception:
        pass

    # Route performance
    summary = profit_path_summary(hours=min(lookback, 168))
    for route in (summary.get("best_routes_24h") or [])[:5]:
        if route.get("attempts", 0) >= 3 and route.get("hit_rate_pct", 0) < 25:
            suggestions.append({
                "priority": "low",
                "category": "route",
                "message": f"Route {route['route']} hit rate {route['hit_rate_pct']}% — review fees/sizing or pause.",
                "evidence": route,
            })

    # De-dupe messages
    seen = set()
    unique: List[Dict[str, Any]] = []
    for s in suggestions:
        msg = s.get("message") or ""
        if msg in seen:
            continue
        seen.add(msg)
        unique.append(s)
    priority_order = {"high": 0, "medium": 1, "low": 2}
    unique.sort(key=lambda x: priority_order.get(str(x.get("priority")), 9))

    return {"success": True, "lookback_hours": lookback, "suggestion_count": len(unique), "suggestions": unique[:15]}


def export_rows(*, limit: Optional[int] = None) -> Dict[str, Any]:
    cfg = load_config()
    lim = int(limit if limit is not None else cfg.get("export_default_limit") or 200)
    rows = _read_ledger(limit=lim)
    return {"success": True, "count": len(rows), "rows": rows}
