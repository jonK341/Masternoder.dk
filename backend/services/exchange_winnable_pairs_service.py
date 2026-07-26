"""Winnable Pairs Executor — supervisor tick: search ranked routes, execute live/paper arb.

Uses profit pair search hits above score/bps thresholds, then runs spatial arb
execution on those symbol/venue routes only.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_arbitrage_service as arb

_CFG_KEY = "winnable_pairs_supervisor"
_DEFAULT_AGENT = "arb_winnable_pairs"


def load_config() -> Dict[str, Any]:
    from backend.services.exchange_profit_path_service import load_config as ppp_cfg

    raw = dict((ppp_cfg().get(_CFG_KEY) or {}))
    raw.setdefault("enabled", True)
    raw.setdefault("min_net_bps", 12.0)
    raw.setdefault("min_search_score", 15.0)
    raw.setdefault("max_executions_per_tick", 3)
    raw.setdefault("notional_usd", float(os.environ.get("EXCHANGE_LIVE_MICRO_USD", "75") or 75))
    raw.setdefault("agent_id", _DEFAULT_AGENT)
    raw.setdefault("refresh_search_each_tick", True)
    return raw


def enabled() -> bool:
    env = os.environ.get("EXCHANGE_WINNABLE_PAIRS", "").strip().lower()
    if env in ("0", "false", "no", "off"):
        return False
    if env in ("1", "true", "yes", "on"):
        return True
    return bool(load_config().get("enabled", True))


def _hit_net_bps(hit: Dict[str, Any]) -> float:
    for key in ("avg_net_bps", "live_net_bps", "net_bps"):
        val = hit.get(key)
        if val is not None:
            return float(val)
    return 0.0


def _filter_winnable(hits: List[Dict[str, Any]], *, min_bps: float, min_score: float) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in hits:
        if not isinstance(row, dict):
            continue
        if _hit_net_bps(row) < min_bps:
            continue
        if float(row.get("search_score") or 0) < min_score:
            continue
        sym = str(row.get("symbol") or "").upper()
        buy_v = str(row.get("buy_venue") or "").lower()
        sell_v = str(row.get("sell_venue") or "").lower()
        if not sym or not buy_v or not sell_v:
            continue
        out.append(row)
    return out


def _ensure_agent_account(agent_id: str) -> None:
    acct = arb.read_account(agent_id)
    if acct.get("agent_id"):
        return
    arb.write_account({
        "agent_id": agent_id,
        "name": "Winnable Pairs Executor",
        "realized_profit_usd": 0.0,
        "trade_count": 0,
        "notional_traded_usd": 0.0,
        "by_venue": {},
        "wallet_label": "",
        "last_action": None,
    })


def run_winnable_pairs_tick(
    *,
    pair_search: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Rank winnable routes and execute up to max_executions_per_tick."""
    if not enabled():
        return {"success": False, "error": "winnable_pairs_disabled"}

    cfg = load_config()
    agent_id = str(cfg.get("agent_id") or _DEFAULT_AGENT)
    min_bps = float(cfg.get("min_net_bps") or 12)
    min_score = float(cfg.get("min_search_score") or 18)
    max_exec = max(1, int(cfg.get("max_executions_per_tick") or 3))
    notional = float(cfg.get("notional_usd") or 75)

    search = pair_search
    if search is None:
        from backend.services.exchange_profit_pair_search_service import (
            enabled as pps_enabled,
            read_index,
            run_profit_pair_search,
        )

        if not pps_enabled():
            return {"success": False, "error": "profit_pair_search_disabled"}
        if cfg.get("refresh_search_each_tick", True):
            search = run_profit_pair_search()
        else:
            idx = read_index()
            search = {
                "success": True,
                "hits": idx.get("hits") or [],
                "hot_symbols": idx.get("hot_symbols") or [],
            }

    if not search or not search.get("success"):
        return {
            "success": False,
            "error": (search or {}).get("error") or "pair_search_failed",
            "profit_pair_search": search,
        }

    hits = list(search.get("hits") or [])
    winnable = _filter_winnable(hits, min_bps=min_bps, min_score=min_score)
    near_winnable = [
        h for h in hits
        if isinstance(h, dict)
        and _hit_net_bps(h) >= min_bps
        and float(h.get("search_score") or 0) < min_score
    ]

    from backend.services.exchange_live_execution_service import book_agent_profit, execute_spatial_arbitrage

    _ensure_agent_account(agent_id)
    executions: List[Dict[str, Any]] = []
    executed_count = 0
    best_opp: Optional[Dict[str, Any]] = None

    for hit in winnable:
        if executed_count >= max_exec:
            break
        sym = str(hit.get("symbol") or "").upper()
        buy_v = str(hit.get("buy_venue") or "").lower()
        sell_v = str(hit.get("sell_venue") or "").lower()
        venues = list(dict.fromkeys([buy_v, sell_v]))
        scan = arb.scan_opportunities(symbols=[sym], venues=venues, notional_usd=notional)
        opps = [
            o for o in (scan.get("opportunities") or [])
            if str(o.get("buy_venue") or "").lower() == buy_v
            and str(o.get("sell_venue") or "").lower() == sell_v
            and float(o.get("net_bps") or 0) >= min_bps
        ]
        if not opps:
            executions.append({
                "symbol": sym,
                "route": f"{buy_v}->{sell_v}",
                "success": False,
                "error": "no_live_opp_at_threshold",
            })
            continue

        opp = max(opps, key=lambda o: float(o.get("net_bps") or 0))
        trade_opp = opp
        if arb.live_enabled():
            prepared = arb.prepare_live_opportunity(
                opp, configured_usd=notional, buffer_pct=0.03, min_live_usd=10.0,
            )
            if not prepared.get("ok"):
                executions.append({
                    "symbol": sym,
                    "route": f"{buy_v}->{sell_v}",
                    "success": False,
                    "error": prepared.get("reason") or "prepare_failed",
                })
                continue
            trade_opp = prepared["opportunity"]

        if best_opp is None or float(trade_opp.get("net_bps") or 0) > float(best_opp.get("net_bps") or 0):
            best_opp = trade_opp

        exec_res = execute_spatial_arbitrage(trade_opp, agent_id=agent_id)
        book_agent_profit(agent_id, trade_opp, exec_res)
        ok = bool(exec_res.get("success"))
        if ok:
            executed_count += 1
        executions.append({
            "symbol": sym,
            "route": f"{buy_v}->{sell_v}",
            "success": ok,
            "mode": exec_res.get("mode"),
            "net_bps": trade_opp.get("net_bps"),
            "error": exec_res.get("error"),
        })

    try:
        from backend.services.exchange_extended_profit_service import write_arb_threshold_state

        write_arb_threshold_state(
            best=best_opp,
            threshold_bps=min_bps,
            source="winnable_pairs",
            hot_symbols=list(search.get("hot_symbols") or []),
        )
    except Exception:
        pass

    ex._audit(
        "winnable_pairs_tick",
        user_id="owner",
        executed=executed_count,
        winnable=len(winnable),
        agent_id=agent_id,
    )

    return {
        "success": True,
        "agent_id": agent_id,
        "winnable_count": len(winnable),
        "near_winnable_count": len(near_winnable),
        "executed_count": executed_count,
        "executions": executions,
        "profit_pair_search": {
            "success": True,
            "hot_symbols": list(search.get("hot_symbols") or []),
            "hit_count": len(hits),
        },
    }
