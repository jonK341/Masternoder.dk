"""Extended profit strategies beyond core spatial arb + cross-trade rotation.

Adds stablecoin peg capture, triangular paper loops, live dual-venue farming,
meme/payments/defi specialty scans, and treasury rotation — all gated by
``data/exchange_extended_profit_config.json`` profiles.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_arbitrage_service as arb
from backend.services import external_exchange_connector_service as conn

_CFG_PATH = os.path.join(ex._BASE, "data", "exchange_extended_profit_config.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CFG_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def _strategy_cfg(name: str) -> Dict[str, Any]:
    return dict((load_config().get("strategies") or {}).get(name) or {})


def _book(agent_id: str, profit_usd: float, action: Dict[str, Any]) -> Dict[str, Any]:
    acct = arb.read_account(agent_id)
    if profit_usd > 0:
        acct["realized_profit_usd"] = round(float(acct.get("realized_profit_usd") or 0) + profit_usd, 6)
        acct["trade_count"] = int(acct.get("trade_count") or 0) + 1
        acct["notional_traded_usd"] = round(float(acct.get("notional_traded_usd") or 0) + float(action.get("notional_usd") or 0), 4)
    acct["ticks"] = int(acct.get("ticks") or 0) + 1
    acct["last_action"] = action
    arb.write_account(acct)
    if profit_usd > 0:
        try:
            from backend.services.exchange_treasury_service import stash_profit_usd

            stash_profit_usd(profit_usd, source=action.get("strategy", "extended"), agent_id=agent_id, mode=action.get("mode", "paper"))
        except Exception:
            pass
    return acct


def tick_live_dual_venue(scfg: Dict[str, Any]) -> Dict[str, Any]:
    venues = list(scfg.get("venues") or ["binance", "nonkyc"])
    symbols = [str(s).upper() for s in (scfg.get("symbols") or [])]
    min_bps = float(scfg.get("min_net_bps") or 15)
    notional = float(scfg.get("notional_usd") or 350)
    agent_id = str(scfg.get("agent_id") or "arb_live_dual_farm")
    max_exec = int(scfg.get("max_executions_per_tick") or 2)

    scan = arb.scan_opportunities(symbols=symbols, venues=venues, notional_usd=notional)
    opps = [o for o in (scan.get("opportunities") or []) if float(o.get("net_bps") or 0) >= min_bps]
    executed = 0
    actions: List[Dict[str, Any]] = []
    for opp in opps[:max_exec]:
        from backend.services.exchange_live_execution_service import execute_spatial_arbitrage, book_agent_profit

        exec_res = execute_spatial_arbitrage(opp, agent_id=agent_id)
        book_agent_profit(agent_id, opp, exec_res)
        executed += 1 if exec_res.get("success") else 0
        actions.append({"executed": exec_res.get("success"), "opp": opp, "mode": exec_res.get("mode")})
    return {"success": True, "strategy": "live_dual_venue", "executed": executed, "candidates": len(opps), "actions": actions}


def tick_stablecoin_peg(scfg: Dict[str, Any]) -> Dict[str, Any]:
    min_bps = float(scfg.get("min_deviation_bps") or 8)
    notional = float(scfg.get("notional_usd") or 200)
    agent_id = str(scfg.get("agent_id") or "arb_stablecoin_peg")
    usdt = float(ex._price_usd("USDT") or 1.0)
    usdc = float(ex._price_usd("USDC") or 1.0)
    dev_bps = abs(usdt - usdc) * 10000.0
    if dev_bps < min_bps:
        return {"success": True, "strategy": "stablecoin_peg", "executed": False, "deviation_bps": round(dev_bps, 2)}
    profit = notional * (dev_bps / 10000.0) * 0.6
    cheap, rich = ("USDT", "USDC") if usdt < usdc else ("USDC", "USDT")
    action = {
        "strategy": "stablecoin_peg",
        "mode": "internal",
        "buy": cheap,
        "sell": rich,
        "deviation_bps": round(dev_bps, 2),
        "notional_usd": notional,
        "est_profit_usd": round(profit, 4),
    }
    _book(agent_id, profit, action)
    return {"success": True, "strategy": "stablecoin_peg", "executed": True, **action}


def _triangular_edge(prices: Dict[str, Dict[str, float]], a: str, b: str, c: str) -> Optional[float]:
    pa, pb, pc = prices.get(a), prices.get(b), prices.get(c)
    if not pa or not pb or not pc:
        return None
    la, lb, lc = float(pa.get("last") or pa.get("ask") or 0), float(pb.get("last") or pb.get("ask") or 0), float(pc.get("last") or pc.get("ask") or 0)
    if la <= 0 or lb <= 0 or lc <= 0:
        return None
    loop = (la / lb) * (lb / lc) * (lc / la)
    return (loop - 1.0) * 10000.0


def tick_triangular_paper(scfg: Dict[str, Any]) -> Dict[str, Any]:
    venues = list(scfg.get("venues") or ["binance", "nonkyc"])
    loops = scfg.get("loops") or [["BTC", "ETH", "SOL"]]
    min_edge = float(scfg.get("min_edge_bps") or 12)
    notional = float(scfg.get("notional_usd") or 150)
    agent_id = str(scfg.get("agent_id") or "arb_triangular_paper")
    symbols = sorted({s for loop in loops for s in loop})
    fetched = conn.fetch_prices(symbols, venues)
    prices_map = fetched.get("prices") or {}
    best: Optional[Dict[str, Any]] = None
    for vid in venues:
        vprices = prices_map.get(vid) or {}
        for loop in loops:
            if len(loop) != 3:
                continue
            edge = _triangular_edge(vprices, loop[0], loop[1], loop[2])
            if edge is None:
                continue
            row = {"venue": vid, "loop": loop, "edge_bps": round(edge, 2)}
            if best is None or edge > best["edge_bps"]:
                best = row
    if not best or best["edge_bps"] < min_edge:
        return {"success": True, "strategy": "triangular_paper", "executed": False, "best": best}
    profit = notional * (best["edge_bps"] / 10000.0) * 0.5
    action = {"strategy": "triangular_paper", "mode": "paper", "notional_usd": notional, **best, "est_profit_usd": round(profit, 4)}
    _book(agent_id, profit, action)
    return {"success": True, "strategy": "triangular_paper", "executed": True, **action}


def tick_spatial_special(scfg: Dict[str, Any], strategy_name: str) -> Dict[str, Any]:
    symbols = [str(s).upper() for s in (scfg.get("symbols") or [])]
    venues = list(scfg.get("venues") or [])
    min_bps = float(scfg.get("min_net_bps") or 20)
    notional = float(scfg.get("notional_usd") or 120)
    agent_id = str(scfg.get("agent_id") or f"arb_{strategy_name}")
    scan = arb.scan_opportunities(symbols=symbols, venues=venues, notional_usd=notional)
    opps = [o for o in (scan.get("opportunities") or []) if float(o.get("net_bps") or 0) >= min_bps]
    if not opps:
        return {"success": True, "strategy": strategy_name, "executed": False, "profitable_count": 0}
    best = opps[0]
    from backend.services.exchange_live_execution_service import execute_spatial_arbitrage, book_agent_profit

    exec_res = execute_spatial_arbitrage(best, agent_id=agent_id)
    book_agent_profit(agent_id, best, exec_res)
    return {"success": True, "strategy": strategy_name, "executed": bool(exec_res.get("success")), "best": best, "mode": exec_res.get("mode")}


def tick_defi_rotation(scfg: Dict[str, Any]) -> Dict[str, Any]:
    assets = [str(a).upper() for a in (scfg.get("assets") or [])]
    trade_mn2 = float(scfg.get("trade_mn2") or 1.5)
    uid = str(scfg.get("treasury_user_id") or "platform_treasury")
    if not assets:
        return {"success": False, "error": "no_assets"}
    tick_n = int(ex._read_json(os.path.join(ex._DATA_DIR, "extended_defi_tick.json"), {}).get("n") or 0) + 1
    symbol = assets[tick_n % len(assets)]
    ex._write_json(os.path.join(ex._DATA_DIR, "extended_defi_tick.json"), {"n": tick_n})
    price_mn2 = max(float(ex._price_in_quote(symbol, "MN2") or 0), 0.00000001)
    amount = round(trade_mn2 / price_mn2, 12)
    side = "buy" if tick_n % 2 else "sell"
    if side == "sell":
        holding = float((ex.get_wallet(uid).get("assets") or {}).get(symbol) or 0)
        amount = min(amount, holding) if holding > 0 else amount
    res = ex.execute_swap(uid, uuid.uuid4().hex[:12], symbol, side, amount, "MN2")
    return {"success": bool(res.get("success")), "strategy": "defi_rotation", "symbol": symbol, "side": side, "trade": res.get("trade")}


def tick_fast_arb_rescan(scfg: Dict[str, Any]) -> Dict[str, Any]:
    min_bps = float(scfg.get("min_net_bps") or 10)
    venues = list(scfg.get("venues") or ["binance", "nonkyc"])
    notional = float(scfg.get("notional_usd") or 250)
    scan = arb.scan_opportunities(venues=venues, notional_usd=notional)
    opps = [o for o in (scan.get("opportunities") or []) if float(o.get("net_bps") or 0) >= min_bps]
    return {
        "success": True,
        "strategy": "fast_arb_rescan",
        "opportunity_count": scan.get("opportunity_count"),
        "profitable_count": len(opps),
        "top_net_bps": opps[0].get("net_bps") if opps else None,
        "top_symbol": opps[0].get("symbol") if opps else None,
    }


_STRATEGY_RUNNERS = {
    "live_dual_venue": tick_live_dual_venue,
    "stablecoin_peg": tick_stablecoin_peg,
    "triangular_paper": tick_triangular_paper,
    "meme_momentum": lambda s: tick_spatial_special(s, "meme_momentum"),
    "payments_spread": lambda s: tick_spatial_special(s, "payments_spread"),
    "defi_rotation": tick_defi_rotation,
    "fast_arb_rescan": tick_fast_arb_rescan,
}


def run_extended_profit_tick(*, profile: str = "standard") -> Dict[str, Any]:
    cfg = load_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "extended_profit_disabled"}
    prof = (cfg.get("profiles") or {}).get(profile) or (cfg.get("profiles") or {}).get("standard") or {}
    names = list(prof.get("strategies") or [])
    results: Dict[str, Any] = {}
    for name in names:
        scfg = _strategy_cfg(name)
        if not scfg.get("enabled", True):
            results[name] = {"success": False, "skipped": True, "reason": "strategy_disabled"}
            continue
        runner = _STRATEGY_RUNNERS.get(name)
        if not runner:
            results[name] = {"success": False, "error": "unknown_strategy"}
            continue
        try:
            results[name] = runner(scfg)
        except Exception as exc:
            results[name] = {"success": False, "error": str(exc)}
    executed = sum(1 for r in results.values() if isinstance(r, dict) and r.get("executed"))
    return {"success": True, "profile": profile, "ran_at": _iso(), "strategy_count": len(names), "executed_count": executed, "results": results}
