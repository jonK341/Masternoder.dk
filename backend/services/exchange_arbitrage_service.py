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


def _effective_transfer_cost_bps(cfg: Dict[str, Any]) -> float:
    """Pre-funded inventory arb skips per-trade on-chain transfer — use lower cost in live mode."""
    if live_enabled():
        return float(cfg.get("prefunded_transfer_cost_bps") or cfg.get("transfer_cost_bps") or 20)
    return float(cfg.get("transfer_cost_bps") or 20)


def _live_api_ready_venues(venue_ids: List[str]) -> List[str]:
    """Drop venues whose private API fails (401, missing keys) during live scans."""
    if not live_enabled():
        return venue_ids
    from backend.services import exchange_venue_api_service as vapi
    ready: List[str] = []
    for vid in venue_ids:
        if vid == "internal":
            ready.append(vid)
            continue
        if not vapi.venue_has_credentials(vid):
            continue
        bal = vapi.get_account_balance(vid, dry_run=False)
        if bal.get("success"):
            ready.append(vid)
    return ready if len(ready) >= 2 or "internal" in ready else venue_ids


def _inventory_tradeable_symbols(
    venue_ids: List[str],
    symbols: List[str],
    *,
    min_quote_usd: float = 20.0,
    min_coin_usd: float = 12.0,
) -> List[str]:
    """Symbols where at least one venue can buy (quote) and one can sell (base coin)."""
    if not live_enabled():
        return symbols
    from backend.services import exchange_venue_api_service as vapi
    from backend.services.external_exchange_connector_service import fetch_ticker

    tradeable: List[str] = []
    external = [v for v in venue_ids if v != "internal"]
    for sym in symbols:
        can_buy = can_sell = False
        for vid in external:
            bals = vapi.parse_spot_balances(vid, dry_run=False)
            quote = vapi.venue_quote_asset(vid)
            if float(bals.get(quote) or 0) >= min_quote_usd:
                can_buy = True
            tick = fetch_ticker(vid, sym)
            mid = 0.0
            if tick and tick.get("bid"):
                mid = float(tick["bid"])
            coin = float(bals.get(sym) or 0)
            if mid > 0 and coin * mid >= min_coin_usd:
                can_sell = True
            elif coin >= 100 and sym in ("DOGE", "SHIB", "PEPE"):
                can_sell = True
        if can_buy and can_sell:
            tradeable.append(sym)
    return tradeable or symbols


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


def _scale_opportunity_notional(opp: Dict[str, Any], notional_usd: float) -> Dict[str, Any]:
    old = float(opp.get("notional_usd") or 0)
    if old <= 0 or abs(old - notional_usd) < 0.01:
        return opp
    ratio = notional_usd / old
    scaled = dict(opp)
    scaled["notional_usd"] = round(notional_usd, 2)
    scaled["sized_notional_usd"] = round(notional_usd, 2)
    scaled["est_profit_usd"] = round(float(opp.get("est_profit_usd") or 0) * ratio, 4)
    return scaled


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
    venue_ids = _live_api_ready_venues(venue_ids)
    transfer_cost_bps = _effective_transfer_cost_bps(cfg)
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
    transfer_cost_bps = _effective_transfer_cost_bps(cfg)
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
        a_venues = _live_api_ready_venues(list(agent.get("venues") or list(vmap.keys())))
        if live_enabled() and agent_id in ("arb_live_dual_farm", "arb_agent_meme"):
            a_symbols = _inventory_tradeable_symbols(a_venues, a_symbols)
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
                cap = vapi.max_funded_notional_usd(
                    best["symbol"],
                    best["buy_venue"],
                    best["sell_venue"],
                    float(best["buy_ask"]),
                    configured_usd=notional,
                )
                min_live_usd = 10.0
                if cap >= min_live_usd:
                    best = _scale_opportunity_notional(best, min(notional, cap))
                else:
                    action = {
                        "agent_id": agent_id,
                        "executed": False,
                        "reason": "insufficient_venue_balance",
                        "best": best,
                        "max_funded_usd": round(cap, 2),
                        "mode": "live",
                    }
                    acct["last_action"] = action
                    write_account(acct)
                    actions.append(action)
                    continue
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


def run_rebalance_tick(*, imbalance_ratio: float = 2.0) -> Dict[str, Any]:
    """Scan credentialed venue quote balances and flag cross-venue rebalance needs."""
    from backend.services import exchange_venue_api_service as vapi

    cfg = conn.load_connectors_config()
    venue_ids = [
        str(v["id"]) for v in (cfg.get("venues") or [])
        if isinstance(v, dict) and v.get("id") and v["id"] != "internal"
    ]
    quotes: List[Dict[str, Any]] = []
    for vid in venue_ids:
        if not vapi.venue_has_credentials(vid):
            continue
        bals = vapi.parse_spot_balances(vid, dry_run=False)
        quote = vapi.venue_quote_asset(vid)
        free = float(bals.get(quote) or 0)
        quotes.append({"venue_id": vid, "quote_asset": quote, "free_quote": round(free, 4)})

    if len(quotes) < 2:
        return {
            "success": True,
            "skipped": True,
            "reason": "need_two_credentialed_venues",
            "venues": quotes,
        }

    amounts = [q["free_quote"] for q in quotes if q["free_quote"] > 0]
    if not amounts:
        return {"success": True, "skipped": True, "reason": "no_quote_inventory", "venues": quotes}

    avg = sum(amounts) / len(amounts)
    rich = max(quotes, key=lambda q: q["free_quote"])
    poor = min(quotes, key=lambda q: q["free_quote"])
    ratio = (rich["free_quote"] / poor["free_quote"]) if poor["free_quote"] > 0 else float("inf")
    move_usd = round(max(0.0, rich["free_quote"] - avg), 4)
    rebalance_needed = ratio >= imbalance_ratio and move_usd >= 10.0
    result = {
        "success": True,
        "live": live_enabled(),
        "rebalance_needed": rebalance_needed,
        "imbalance_ratio": round(ratio, 4) if ratio != float("inf") else None,
        "target_quote_per_venue": round(avg, 4),
        "suggested_move_usd": move_usd if rebalance_needed else 0.0,
        "from_venue": rich if rebalance_needed else None,
        "to_venue": poor if rebalance_needed else None,
        "venues": quotes,
        "ticked_at": _iso(),
    }
    if rebalance_needed:
        ex._audit(
            "arb_rebalance_tick",
            from_venue=rich["venue_id"],
            to_venue=poor["venue_id"],
            move_usd=move_usd,
            ratio=round(ratio, 4),
        )
    return result


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
