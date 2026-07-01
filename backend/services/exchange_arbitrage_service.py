"""Cross-venue margin scanner + paper arbitrage agents.

Computes the best buy/sell spread for each symbol across external venues (and the
internal exchange), nets out taker fees + transfer cost, and ranks profitable
opportunities. Paper agents "execute" the spread by crediting a per-agent profit
account — no real funds move until the live gates are satisfied.

Live trading gate: BOTH ``EXCHANGE_ARBITRAGE_LIVE=1`` AND a per-venue API key present
in the encrypted vault. This module never places real orders in Phase 1.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services import external_exchange_connector_service as conn

_ACCOUNTS_DIR = os.path.join(ex._DATA_DIR, "agent_accounts")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def live_enabled() -> bool:
    cfg = conn.load_connectors_config()
    flag = cfg.get("live_env_flag") or "EXCHANGE_ARBITRAGE_LIVE"
    if str(os.environ.get(flag, "")).strip() != "1":
        return False
    try:
        from backend.services import mn2_spork_service as spork
        ok, _reason = spork.exchange_live_spork_ok()
        return ok
    except Exception:
        return True


def _internal_fee_bps() -> float:
    fees = (ex.load_config().get("fees") or {})
    return float(fees.get("taker_bps") or fees.get("taker") or 25)


def _account_path(agent_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(agent_id))
    return os.path.join(_ACCOUNTS_DIR, f"{safe}.json")


def read_account(agent_id: str) -> Dict[str, Any]:
    acct = ex._read_json(_account_path(agent_id), {})
    if not isinstance(acct, dict) or not acct:
        acct = {
            "agent_id": agent_id,
            "realized_profit_usd": 0.0,
            "trade_count": 0,
            "notional_traded_usd": 0.0,
            "by_venue": {},
            "wallet_label": "",
            "game_time_sec": 0,
            "ticks": 0,
            "agent_level": 1,
            "last_action": None,
            "created_at": _iso(),
        }
    return acct


def write_account(acct: Dict[str, Any]) -> None:
    ex._write_json(_account_path(acct["agent_id"]), acct)


def _prices_for_symbol(
    prices: Dict[str, Dict[str, Dict[str, float]]],
    symbol: str,
    venue_ids: List[str],
    vmap: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for vid in venue_ids:
        if vid == "internal":
            px = ex._price_usd(symbol)
            if px > 0:
                rows.append({"venue": "internal", "bid": px, "ask": px, "fee_bps": _internal_fee_bps()})
            continue
        t = (prices.get(vid) or {}).get(symbol)
        v = vmap.get(vid) or {}
        if t and t.get("bid", 0) > 0 and t.get("ask", 0) > 0:
            rows.append({
                "venue": vid,
                "bid": float(t["bid"]),
                "ask": float(t["ask"]),
                "fee_bps": float(v.get("fee_taker_bps") or 10),
            })
    return rows


def _best_opportunity(
    symbol: str,
    rows: List[Dict[str, Any]],
    *,
    transfer_cost_bps: float,
    notional_usd: float,
) -> Optional[Dict[str, Any]]:
    if len(rows) < 2:
        return None
    buy = min(rows, key=lambda r: r["ask"])      # cheapest place to buy
    sell = max(rows, key=lambda r: r["bid"])     # most expensive place to sell
    if buy["venue"] == sell["venue"] or buy["ask"] <= 0:
        return None
    gross_bps = (sell["bid"] - buy["ask"]) / buy["ask"] * 10000.0
    fee_bps = buy["fee_bps"] + sell["fee_bps"] + transfer_cost_bps
    net_bps = gross_bps - fee_bps
    return {
        "symbol": symbol,
        "buy_venue": buy["venue"],
        "buy_ask": round(buy["ask"], 8),
        "sell_venue": sell["venue"],
        "sell_bid": round(sell["bid"], 8),
        "gross_bps": round(gross_bps, 2),
        "fee_bps": round(fee_bps, 2),
        "net_bps": round(net_bps, 2),
        "notional_usd": round(notional_usd, 2),
        "est_profit_usd": round(notional_usd * net_bps / 10000.0, 4),
    }


def scan_opportunities(
    symbols: Optional[List[str]] = None,
    venues: Optional[List[str]] = None,
    *,
    injected: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None,
    notional_usd: Optional[float] = None,
) -> Dict[str, Any]:
    cfg = conn.load_connectors_config()
    symbols = [str(s).upper() for s in (symbols or cfg.get("supported_symbols") or [])]
    vmap = conn._venue_map(cfg)
    venue_ids = venues or ([vid for vid, v in vmap.items() if v.get("enabled", True)] + ["internal"])
    transfer_cost_bps = float(cfg.get("transfer_cost_bps") or 20)
    min_margin_bps = float(cfg.get("min_margin_bps") or 30)
    notional = float(notional_usd or cfg.get("paper_trade_usd") or 250)

    fetched = conn.fetch_prices(
        symbols,
        [v for v in venue_ids if v != "internal"],
        injected=injected,
        use_cache=not live_enabled() if injected is None else False,
    )
    prices = fetched.get("prices") or {}

    opportunities: List[Dict[str, Any]] = []
    for sym in symbols:
        rows = _prices_for_symbol(prices, sym, venue_ids, vmap)
        opp = _best_opportunity(sym, rows, transfer_cost_bps=transfer_cost_bps, notional_usd=notional)
        if opp:
            opp["profitable"] = opp["net_bps"] >= min_margin_bps
            opportunities.append(opp)

    opportunities.sort(key=lambda o: o["net_bps"], reverse=True)
    return {
        "success": True,
        "scanned_at": _iso(),
        "source": fetched.get("source"),
        "min_margin_bps": min_margin_bps,
        "opportunity_count": len(opportunities),
        "profitable_count": sum(1 for o in opportunities if o["profitable"]),
        "opportunities": opportunities,
    }


def run_paper_tick(*, injected: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None) -> Dict[str, Any]:
    """Scan per-agent and credit paper profit for the best profitable opportunity."""
    cfg = conn.load_connectors_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "connectors_disabled"}
    vmap = conn._venue_map(cfg)
    transfer_cost_bps = float(cfg.get("transfer_cost_bps") or 20)
    min_margin_bps = float(cfg.get("min_margin_bps") or 30)
    default_notional = float(cfg.get("paper_trade_usd") or 250)

    fetched = conn.fetch_prices(
        injected=injected,
        use_cache=not live_enabled() if injected is None else False,
    )
    prices = fetched.get("prices") or {}

    try:
        from backend.services.exchange_live_execution_service import sync_internal_prices_to_external_mid
        sync_internal_prices_to_external_mid(prices if not injected else None)
    except Exception:
        pass

    actions: List[Dict[str, Any]] = []

    for agent in cfg.get("arbitrage_agents") or []:
        if not isinstance(agent, dict):
            continue
        agent_id = str(agent.get("id") or "").strip()
        if not agent_id:
            continue
        a_symbols = [str(s).upper() for s in (agent.get("symbols") or cfg.get("supported_symbols") or [])]
        a_venues = list(agent.get("venues") or list(vmap.keys()))
        notional = float(agent.get("paper_trade_usd") or default_notional)

        best: Optional[Dict[str, Any]] = None
        for sym in a_symbols:
            rows = _prices_for_symbol(prices, sym, a_venues, vmap)
            opp = _best_opportunity(sym, rows, transfer_cost_bps=transfer_cost_bps, notional_usd=notional)
            if opp and (best is None or opp["net_bps"] > best["net_bps"]):
                best = opp

        acct = read_account(agent_id)
        acct["wallet_label"] = agent.get("wallet_label") or acct.get("wallet_label") or ""
        acct["ticks"] = int(acct.get("ticks") or 0) + 1
        acct["game_time_sec"] = int(acct.get("game_time_sec") or 0) + 3600
        acct["agent_level"] = 1 + int(acct.get("ticks") or 0) // 50
        if best and best["net_bps"] >= min_margin_bps and best["est_profit_usd"] > 0:
            from backend.services.exchange_live_execution_service import execute_spatial_arbitrage, book_agent_profit
            from backend.services import exchange_venue_api_service as vapi
            if live_enabled():
                funding = vapi.opportunity_funded(best)
                if not funding.get("ok"):
                    action = {
                        "agent_id": agent_id,
                        "executed": False,
                        "reason": "insufficient_venue_balance",
                        "best": best,
                        "funding": funding,
                        "mode": "live",
                    }
                    acct["last_action"] = action
                    write_account(acct)
                    actions.append(action)
                    continue
            exec_res = execute_spatial_arbitrage(best, agent_id=agent_id)
            acct = book_agent_profit(agent_id, best, exec_res)
            action = acct.get("last_action") or {"agent_id": agent_id, "executed": exec_res.get("success")}
        else:
            action = {"agent_id": agent_id, "executed": False, "reason": "no_profitable_spread",
                      "best": best, "mode": "paper"}
            acct["last_action"] = action
        write_account(acct)
        actions.append(action)

    return {
        "success": True,
        "ticked_at": _iso(),
        "live": live_enabled(),
        "source": fetched.get("source"),
        "agent_count": len(actions),
        "executed_count": sum(1 for a in actions if a.get("executed")),
        "actions": actions,
    }


def agent_accounts() -> Dict[str, Any]:
    cfg = conn.load_connectors_config()
    accounts: List[Dict[str, Any]] = []
    total_profit = 0.0
    for agent in cfg.get("arbitrage_agents") or []:
        if not isinstance(agent, dict) or not agent.get("id"):
            continue
        acct = read_account(str(agent["id"]))
        acct["name"] = agent.get("name") or agent["id"]
        total_profit += float(acct.get("realized_profit_usd") or 0)
        accounts.append(acct)
    return {
        "success": True,
        "agent_count": len(accounts),
        "total_realized_profit_usd": round(total_profit, 6),
        "accounts": accounts,
    }


def arbitrage_overview() -> Dict[str, Any]:
    from backend.services import exchange_secrets_vault_service as vault
    venues = conn.list_venues()
    accounts = agent_accounts()
    return {
        "success": True,
        "live": live_enabled(),
        "mode": venues.get("mode"),
        "venue_count": venues.get("venue_count"),
        "agent_count": accounts.get("agent_count"),
        "total_realized_profit_usd": accounts.get("total_realized_profit_usd"),
        "vault": vault.vault_status(),
    }
