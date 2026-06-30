"""Live spatial-arbitrage execution + profit stash on MasterNoder exchange.

Routes each leg to the correct venue:
  - External venues → signed REST (``exchange_venue_api_service``)
  - ``internal`` → MasterNoder exchange swap for the agent/treasury wallet

When ``EXCHANGE_ARBITRAGE_LIVE=1`` and vault keys exist for a venue, that leg
goes live; other legs stay paper-simulated until credentialed.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.services import crypto_exchange_service as ex
from backend.services import exchange_arbitrage_service as arb
from backend.services import external_exchange_connector_service as conn


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def venue_live_ready(venue_id: str) -> bool:
    if venue_id == "internal":
        return True
    from backend.services import exchange_venue_api_service as vapi
    return arb.live_enabled() and vapi.venue_has_credentials(venue_id)


def live_readiness() -> Dict[str, Any]:
    from backend.services import exchange_venue_api_service as vapi
    cfg = conn.load_connectors_config()
    venues = []
    ready_count = 0
    for v in cfg.get("venues") or []:
        if not isinstance(v, dict) or not v.get("id"):
            continue
        vid = str(v["id"])
        creds = vapi.venue_has_credentials(vid)
        live_sup = bool((vapi.load_api_config().get("venues") or {}).get(vid, {}).get("live_supported", False))
        ready = live_sup and creds and arb.live_enabled()
        if ready:
            ready_count += 1
        venues.append({
            "venue_id": vid,
            "name": v.get("name"),
            "credentials_configured": creds,
            "live_supported": live_sup,
            "live_ready": ready,
        })
    return {
        "success": True,
        "live_gate": arb.live_enabled(),
        "live_venue_count": ready_count,
        "venues": venues,
        "can_trade_external": ready_count >= 2,
        "hint": "Set EXCHANGE_ARBITRAGE_LIVE=1 and store {venue}_api_key + {venue}_api_secret in vault.",
    }


def sync_internal_prices_to_external_mid(
    prices: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None,
) -> Dict[str, Any]:
    """Align internal exchange drift with global venue mids (stops fake internal spreads)."""
    from backend.services.exchange_treasury_service import load_config as treasury_cfg
    if not treasury_cfg().get("sync_internal_to_external_mid", True):
        return {"success": True, "skipped": True}

    cfg = conn.load_connectors_config()
    symbols = [str(s).upper() for s in (cfg.get("supported_symbols") or [])]
    if prices is None:
        fetched = conn.fetch_prices(symbols, use_cache=False)
        prices = fetched.get("prices") or {}

    assets = ex._asset_map()
    cache = ex._read_json(os.path.join(ex._DATA_DIR, "price_cache.json"), {})
    if not isinstance(cache, dict):
        cache = {}

    updated: Dict[str, float] = {}
    for sym in symbols:
        mids = []
        for _vid, ticks in (prices or {}).items():
            t = (ticks or {}).get(sym)
            if t and t.get("bid", 0) > 0 and t.get("ask", 0) > 0:
                mids.append((float(t["bid"]) + float(t["ask"])) / 2.0)
        asset = assets.get(sym)
        base = float((asset or {}).get("base_price_usd") or 0)
        if mids and base > 0:
            mid = sum(mids) / len(mids)
            drift = round(mid / base, 8)
            cache[sym] = drift
            updated[sym] = drift

    ex._write_json(os.path.join(ex._DATA_DIR, "price_cache.json"), cache)
    return {"success": True, "updated_symbols": updated, "count": len(updated)}


def _internal_swap(agent_id: str, symbol: str, side: str, amount: float) -> Dict[str, Any]:
    qid = uuid.uuid4().hex[:16]
    q = ex.quote_swap(agent_id, symbol, side, amount, "MN2")
    if not q.get("success"):
        return q
    return ex.execute_swap(agent_id, qid, symbol, side, amount, "MN2")


def execute_spatial_arbitrage(
    opp: Dict[str, Any],
    *,
    agent_id: str,
    dry_run: Optional[bool] = None,
) -> Dict[str, Any]:
    """Execute both legs; stash profit to platform treasury when configured."""
    from backend.services import exchange_venue_api_service as vapi
    from backend.services.exchange_treasury_service import load_config as treasury_cfg, stash_profit_usd

    symbol = str(opp.get("symbol") or "BTC").upper()
    buy_venue = str(opp.get("buy_venue") or "")
    sell_venue = str(opp.get("sell_venue") or "")
    notional = float(opp.get("notional_usd") or opp.get("sized_notional_usd") or 250)
    buy_price = float(opp.get("buy_ask") or 0)
    if buy_price <= 0 or not buy_venue or not sell_venue:
        return {"success": False, "error": "invalid_opportunity"}

    qty = round(notional / buy_price, 8)
    global_live = arb.live_enabled() and dry_run is not False

    def _leg(venue: str, side: str) -> Dict[str, Any]:
        if venue == "internal":
            if global_live and not dry_run:
                return _internal_swap(agent_id, symbol, side, qty)
            return {"success": True, "mode": "paper", "simulated": True, "venue": "internal", "side": side, "quantity": qty}
        use_live = global_live and venue_live_ready(venue) and dry_run is not False
        return vapi.place_market_order(venue, symbol, side, qty, dry_run=not use_live)

    buy_res = _leg(buy_venue, "buy")
    sell_res = _leg(sell_venue, "sell")
    ok = bool(buy_res.get("success")) and bool(sell_res.get("success"))

    live_legs = sum(
        1 for v in (buy_venue, sell_venue)
        if v != "internal" and venue_live_ready(v)
    )
    if live_legs >= 2:
        mode = "live"
    elif live_legs == 1:
        mode = "hybrid"
    else:
        mode = "paper"

    profit = float(opp.get("est_profit_usd") or 0) if ok else 0.0
    stash = None
    tc = treasury_cfg()
    if ok and profit > 0 and tc.get("auto_stash_on_trade", True):
        stash = stash_profit_usd(
            profit,
            source="live_arbitrage" if mode == "live" else "paper_arbitrage",
            agent_id=agent_id,
            mode=mode,
            meta={"symbol": symbol, "buy_venue": buy_venue, "sell_venue": sell_venue, "net_bps": opp.get("net_bps")},
        )

    return {
        "success": ok,
        "mode": mode,
        "symbol": symbol,
        "quantity": qty,
        "notional_usd": notional,
        "est_profit_usd": profit,
        "buy_venue": buy_venue,
        "sell_venue": sell_venue,
        "buy_order": buy_res,
        "sell_order": sell_res,
        "stash": stash,
        "executed_at": _iso(),
    }


def book_agent_profit(
    agent_id: str,
    opp: Dict[str, Any],
    exec_res: Dict[str, Any],
) -> Dict[str, Any]:
    """Update agent account + audit after execution."""
    profit = float(exec_res.get("est_profit_usd") or 0) if exec_res.get("success") else 0.0
    acct = arb.read_account(agent_id)
    if exec_res.get("success") and profit > 0:
        acct["realized_profit_usd"] = round(float(acct.get("realized_profit_usd") or 0) + profit, 6)
        acct["trade_count"] = int(acct.get("trade_count") or 0) + 1
        acct["notional_traded_usd"] = round(float(acct.get("notional_traded_usd") or 0) + float(opp.get("notional_usd") or 0), 2)
        action = {"agent_id": agent_id, "executed": True, "mode": exec_res.get("mode"), **opp, "execution": exec_res}
        ex._audit(
            "arbitrage_live_trade" if exec_res.get("mode") == "live" else "arbitrage_paper_trade",
            user_id=agent_id,
            amount_usd=profit,
            symbol=opp.get("symbol"),
            buy_venue=opp.get("buy_venue"),
            sell_venue=opp.get("sell_venue"),
            net_bps=opp.get("net_bps"),
            mode=exec_res.get("mode"),
        )
    else:
        action = {"agent_id": agent_id, "executed": False, "mode": exec_res.get("mode"), "best": opp, "execution": exec_res}
    acct["last_action"] = action
    arb.write_account(acct)
    return acct


def try_farm_execution_for_agent(
    user_id: str,
    agent_id: str,
    agent: Dict[str, Any],
    *,
    daemon_cfg: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """When live gates are on, scan configured venues and execute the best spread."""
    if not arb.live_enabled():
        return None
    try:
        from backend.services.exchange_user_daemon_service import _agent_farm_params
        fp = _agent_farm_params(agent, daemon_cfg or {})
    except Exception:
        return None
    if not fp.get("venues"):
        return None

    from backend.services.exchange_arbitrage_service import scan_opportunities

    scan = scan_opportunities(
        symbols=fp["symbols"],
        venues=fp["venues"],
        notional_usd=fp["notional_usd"],
    )
    opps = [o for o in (scan.get("opportunities") or []) if o.get("profitable")]
    if not opps:
        return None

    best = opps[0]
    exec_res = execute_spatial_arbitrage(best, agent_id=agent_id)
    if not exec_res.get("success"):
        return None

    profit = float(exec_res.get("est_profit_usd") or 0)
    ex._audit(
        "agent_live_trade" if exec_res.get("mode") == "live" else "arbitrage_paper_trade",
        user_id=user_id,
        agent_id=agent_id,
        amount_usd=profit,
        mode=exec_res.get("mode"),
        symbol=best.get("symbol"),
    )
    return {
        "profit_usd": profit,
        "mode": exec_res.get("mode"),
        "best": best,
        "execution": exec_res,
        "scan": {"opportunity_count": scan.get("opportunity_count"), "profitable_count": scan.get("profitable_count")},
    }
