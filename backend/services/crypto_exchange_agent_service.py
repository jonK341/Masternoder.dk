"""Exchange cross-trading agents and daemon tick helpers.

When ``EXCHANGE_ARBITRAGE_LIVE=1`` and Binance is credentialed, agents place real
spot market orders on the venue (funded from the sales-pool USDC that mirrors
Binance free). Otherwise they fall back to internal MN2 ledger swaps.
"""
from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.services import crypto_exchange_service as ex

_STATE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "crypto_exchange",
    "agent_state.json",
)

_VENUE_SKIP_ASSETS = frozenset({"MN2", "COINS"})


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_state() -> Dict[str, Any]:
    return ex._read_json(_STATE_PATH, {"tick_count": 0, "agents": {}, "last_tick": None})


def _write_state(state: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, state)


def _agent_config() -> Dict[str, Any]:
    cfg = ex.load_config()
    return cfg.get("agent_trading") if isinstance(cfg.get("agent_trading"), dict) else {}


def list_agents() -> Dict[str, Any]:
    cfg = _agent_config()
    state = _read_state()
    try:
        ex.ensure_agent_wallets()
    except Exception:
        pass
    agents = []
    for row in cfg.get("agents") or []:
        if not isinstance(row, dict):
            continue
        aid = str(row.get("id") or "").strip()
        wallet = ex.get_wallet(aid) if aid else {"success": False}
        assets = (wallet.get("assets") if isinstance(wallet, dict) else {}) or {}
        # Show every catalog coin so agents can compare distinct balances.
        wallets = wallet.get("wallets") if isinstance(wallet, dict) else None
        agents.append({
            **row,
            "state": (state.get("agents") or {}).get(aid, {}),
            "wallet": {
                "success": bool(wallet.get("success")),
                "mn2_balance": wallet.get("mn2_balance"),
                "coins_balance": wallet.get("coins_balance"),
                "assets": assets,
                "wallets": wallets or [],
                "total_usd": wallet.get("total_usd"),
                "wallet_count": wallet.get("wallet_count"),
            },
        })
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "daemon_interval_sec": int(cfg.get("daemon_interval_sec") or 300),
        "live_venue_trading": bool(cfg.get("live_venue_trading", True)),
        "venue_id": str(cfg.get("venue_id") or "binance"),
        "agents": agents,
        "tick_count": int(state.get("tick_count") or 0),
        "last_tick": state.get("last_tick"),
        "venue_live": _venue_live_ready(str(cfg.get("venue_id") or "binance")),
    }


def _seed_agent_mn2(agent_id: str, target_mn2: float, *, tick_count: int = 0) -> None:
    """Top up agent MN2 before each trade. Disabled when stable markets paper mode is off
    so agents cannot invent non-withdrawable inventory that becomes 'real' USDT/USDC."""
    try:
        from backend.services.exchange_stable_markets_service import paper_mode_enabled
        if not paper_mode_enabled():
            return
    except ImportError:
        pass
    from backend.services.unified_points_database import unified_points_db

    bal = ex._get_quote_balance(agent_id, "MN2")
    gap = round(float(target_mn2) - float(bal), 8)
    if gap <= 0:
        return
    unified_points_db.add_points(
        agent_id,
        "mn2_balance",
        gap,
        source="exchange_agent_seed",
        metadata={
            "reference": f"exchange-agent-seed:{agent_id}:t{int(tick_count)}",
            "non_withdrawable": True,
        },
    )


def _pick_asset(agent: Dict[str, Any], tick_count: int) -> str:
    assets = [str(a).upper() for a in (agent.get("assets") or []) if str(a).upper() != "MN2"]
    if not assets:
        assets = ["USDC"]
    return assets[tick_count % len(assets)]


def _venue_live_ready(venue_id: str = "binance") -> bool:
    try:
        from backend.services.exchange_arbitrage_service import live_enabled
        from backend.services.exchange_live_execution_service import venue_live_ready
        if not live_enabled():
            return False
        cfg = _agent_config()
        if cfg.get("live_venue_trading") is False:
            return False
        return bool(venue_live_ready(str(venue_id or "binance")))
    except Exception:
        return False


def _sales_pool_id() -> str:
    try:
        from backend.services.exchange_sales_pool_service import sales_pool_user_id
        return sales_pool_user_id()
    except Exception:
        return "exchange_sales_pool"


def _allocate_quote_from_pool(
    agent_id: str,
    quote: str,
    amount: float,
    *,
    venue_free: float,
) -> float:
    """Move venue-backed quote from sales pool → agent for a live buy."""
    pool = _sales_pool_id()
    need = round(max(0.0, float(amount)), 8)
    if need <= 0:
        return 0.0
    pool_bal = float(ex._get_quote_balance(pool, quote) or 0)
    agent_bal = float(ex._get_quote_balance(agent_id, quote) or 0)
    # Prefer pool funds that are backed by venue free (leave a reserve).
    reserve = float(_agent_config().get("min_venue_quote_reserve_usd") or 20.0)
    spendable_venue = max(0.0, float(venue_free) - reserve)
    already = min(agent_bal, spendable_venue)
    if already >= need:
        return need
    gap = round(need - already, 8)
    move = round(min(gap, pool_bal, max(0.0, spendable_venue - already)), 8)
    if move <= 0:
        return already if already > 0 else 0.0
    meta = {
        "reference": f"agent-venue-fund:{agent_id}:{uuid.uuid4().hex[:8]}",
        "agent_id": agent_id,
        "quote": quote,
    }
    with ex._LOCK:
        ex._adjust_quote_balance(pool, quote, -move, "agent_venue_fund", meta)
        ex._adjust_quote_balance(agent_id, quote, move, "agent_venue_fund", meta)
    return round(already + move, 8)


def _return_unused_quote_to_pool(agent_id: str, quote: str, amount: float) -> None:
    pool = _sales_pool_id()
    amt = round(max(0.0, float(amount)), 8)
    if amt <= 0:
        return
    have = float(ex._get_quote_balance(agent_id, quote) or 0)
    move = round(min(amt, have), 8)
    if move <= 0:
        return
    meta = {
        "reference": f"agent-venue-refund:{agent_id}:{uuid.uuid4().hex[:8]}",
        "agent_id": agent_id,
        "quote": quote,
    }
    try:
        with ex._LOCK:
            ex._adjust_quote_balance(agent_id, quote, -move, "agent_venue_refund", meta)
            ex._adjust_quote_balance(pool, quote, move, "agent_venue_refund", meta)
    except Exception:
        pass


def _trade_agent_live(
    agent: Dict[str, Any],
    tick_count: int,
    max_trade_usd: float,
    *,
    venue_id: str,
) -> Dict[str, Any]:
    from backend.services import exchange_venue_api_service as vapi
    from backend.services.exchange_user_venue_execution_service import (
        execute_venue_swap,
        quote_venue_swap,
    )

    agent_id = str(agent.get("id") or "").strip()
    if not agent_id:
        return {"success": False, "error": "missing_agent_id"}

    quote = str(vapi.venue_quote_asset(venue_id) or "USDC").upper()
    if quote not in ("USDC", "USDT"):
        quote = "USDC"

    symbols = [
        str(a).upper()
        for a in (agent.get("assets") or [])
        if str(a).upper() not in _VENUE_SKIP_ASSETS and str(a).upper() != quote
    ]
    if not symbols:
        return {
            "agent_id": agent_id,
            "agent_name": agent.get("name") or agent_id,
            "strategy": agent.get("strategy") or "rotation",
            "success": False,
            "error": "no_venue_tradeable_assets",
            "mode": "live",
            "venue_id": venue_id,
        }

    bals = vapi.parse_spot_balances(venue_id, dry_run=False, force_refresh=False)
    venue_quote_free = float(bals.get(quote) or 0)
    reserve = float(_agent_config().get("min_venue_quote_reserve_usd") or 20.0)
    spendable = max(0.0, venue_quote_free - reserve)
    base_usd = max(5.0, min(float(max_trade_usd), 25.0))

    # Rotate start symbol; skip pairs Binance rejects (unlist / API-key whitelist).
    start = tick_count % len(symbols)
    ordered = [symbols[(start + i) % len(symbols)] for i in range(len(symbols))]
    last_err = "no_tradeable_pair"
    symbol = ordered[0]
    side = "buy"
    amount = 0.0
    notional = 0.0
    result: Dict[str, Any] = {"success": False, "error": last_err}

    def _retryable(err: str) -> bool:
        e = (err or "").lower()
        return any(
            token in e
            for token in (
                "not whitelisted",
                "pair_not_supported",
                "invalid symbol",
                "does not exist",
                "not support this symbol",
                "permission",
                "min_lot_exceeds",
            )
        )

    for symbol in ordered:
        venue_base = float(bals.get(symbol) or 0)
        agent_base = float((ex.get_wallet(agent_id).get("assets") or {}).get(symbol) or 0)
        if venue_base > 0 and agent_base > 0 and tick_count % 2 == 1:
            side = "sell"
        elif spendable >= 5.0:
            side = "buy"
        elif venue_base > 0 and agent_base > 0:
            side = "sell"
        else:
            last_err = "insufficient_venue_inventory"
            continue

        target_usd = base_usd if side == "sell" else min(base_usd, spendable)
        if side == "buy" and target_usd < 5.0:
            last_err = "venue_quote_below_min_notional"
            continue

        spec = vapi.market_order_for_leg(
            venue_id, side, symbol, target_usd, quote=quote,
        )
        if not spec.get("ok"):
            last_err = str(spec.get("error") or "order_spec_failed")
            continue

        amount = float(spec["quantity"])
        notional = float(spec.get("notional_usd") or target_usd)
        if notional > target_usd * 1.35 and side == "buy":
            last_err = "min_lot_exceeds_trade_budget"
            continue

        if side == "sell":
            sell_amt = min(amount, venue_base, agent_base)
            if sell_amt <= 0:
                last_err = "insufficient_sellable_inventory"
                continue
            amount = sell_amt

        funded = 0.0
        if side == "buy":
            q_preview = quote_venue_swap(agent_id, venue_id, symbol, side, amount, quote)
            cost = float(q_preview.get("quote_cost") or notional) * 1.02
            funded = _allocate_quote_from_pool(
                agent_id, quote, cost, venue_free=venue_quote_free,
            )
            needed = float(q_preview.get("quote_cost") or notional)
            if funded + 1e-9 < needed:
                last_err = "insufficient_pool_quote"
                continue

        result = execute_venue_swap(
            agent_id,
            venue_id,
            uuid.uuid4().hex[:16],
            symbol,
            side,
            amount,
            quote,
        )
        if result.get("success"):
            break

        last_err = str(result.get("error") or "venue_order_failed")
        if side == "buy" and funded > 0:
            _return_unused_quote_to_pool(agent_id, quote, funded)
        if not _retryable(last_err):
            break
        # Refresh spendable after a failed buy attempt (funds returned).
        if side == "buy":
            bals = vapi.parse_spot_balances(venue_id, dry_run=False, force_refresh=True)
            venue_quote_free = float(bals.get(quote) or 0)
            spendable = max(0.0, venue_quote_free - reserve)
    else:
        result = {
            "success": False,
            "error": last_err,
            "mode": "live",
            "venue_id": venue_id,
        }

    try:
        from backend.services.exchange_profit_path_service import record_event

        trade = result.get("trade") or {}
        usd = float(trade.get("usd_value") or notional)
        record_event(
            phase="execute",
            agent_id=agent_id,
            strategy=str(agent.get("strategy") or "rotation"),
            symbol=symbol,
            mode="live" if result.get("success") else "live_attempt",
            decision="fill" if result.get("success") else "attempt",
            skip_reason=str(result.get("error") or last_err or ""),
            notional_usd=usd,
            execution={
                "trade_id": str(trade.get("trade_id") or ""),
                "side": side,
                "venue_id": venue_id,
                "success": bool(result.get("success")),
                "fill_usd": round(usd, 4),
                "order_id": str((result.get("order") or {}).get("order_id") or ""),
            },
        )
    except Exception:
        pass

    # Invalidate balance cache so the next agent sees updated venue free.
    try:
        vapi.invalidate_venue_balance_cache(venue_id)
    except Exception:
        pass

    return {
        "agent_id": agent_id,
        "agent_name": agent.get("name") or agent_id,
        "strategy": agent.get("strategy") or "rotation",
        "symbol": symbol,
        "side": side,
        "amount": amount,
        "success": bool(result.get("success")),
        "error": result.get("error") or (None if result.get("success") else last_err),
        "trade": result.get("trade"),
        "order": result.get("order"),
        "mode": result.get("mode") or "live",
        "venue_id": venue_id,
        "notional_usd": notional,
    }


def _trade_agent_internal(agent: Dict[str, Any], tick_count: int, max_trade_mn2: float) -> Dict[str, Any]:
    agent_id = str(agent.get("id") or "").strip()
    if not agent_id:
        return {"success": False, "error": "missing_agent_id"}
    symbol = _pick_asset(agent, tick_count)
    price_mn2 = max(float(ex._price_in_quote(symbol, "MN2") or 0), 0.00000001)
    asset = ex._asset_map().get(symbol) or {}
    min_trade = float(asset.get("min_trade") or 0)
    target_asset_amount = round(max(max_trade_mn2 / price_mn2, min_trade), 12)
    holding = float((ex.get_wallet(agent_id).get("assets") or {}).get(symbol) or 0)

    # Alternate between adding inventory and recycling part of it back to MN2.
    if tick_count % 2 == 1 and holding > target_asset_amount / 2:
        amount = max(target_asset_amount / 2, min(holding, target_asset_amount))
        side = "sell"
    else:
        amount = target_asset_amount
        side = "buy"

    result = ex.execute_swap(
        agent_id,
        uuid.uuid4().hex[:16],
        symbol,
        side,
        amount,
        "MN2",
    )
    try:
        from backend.services.exchange_profit_path_service import record_event, ledger_mode
        trade = result.get("trade") or {}
        usd = float(trade.get("usd_value") or 0) if trade else float(amount) * ex._price_usd(symbol)
        record_event(
            phase="execute",
            agent_id=agent_id,
            strategy=str(agent.get("strategy") or "rotation"),
            symbol=symbol,
            mode=ledger_mode(),
            decision="fill" if result.get("success") else "attempt",
            skip_reason=str(result.get("error") or ""),
            notional_usd=usd,
            execution={
                "trade_id": str(trade.get("trade_id") or ""),
                "side": side,
                "success": bool(result.get("success")),
                "realized_pnl_usd": round(usd * 0.001, 4) if result.get("success") else 0.0,
                "fill_usd": round(usd, 4),
            },
        )
    except Exception:
        pass
    return {
        "agent_id": agent_id,
        "agent_name": agent.get("name") or agent_id,
        "strategy": agent.get("strategy") or "rotation",
        "symbol": symbol,
        "side": side,
        "amount": amount,
        "success": bool(result.get("success")),
        "error": result.get("error"),
        "trade": result.get("trade"),
        "mode": "internal",
    }


def _trade_agent(agent: Dict[str, Any], tick_count: int, max_trade_mn2: float) -> Dict[str, Any]:
    cfg = _agent_config()
    venue_id = str(cfg.get("venue_id") or "binance").lower()
    if _venue_live_ready(venue_id):
        max_usd = float(cfg.get("max_trade_usd_per_tick") or cfg.get("max_trade_mn2_per_tick") or 8.0)
        return _trade_agent_live(agent, tick_count, max_usd, venue_id=venue_id)
    return _trade_agent_internal(agent, tick_count, max_trade_mn2)


def _enabled_agents(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for agent in cfg.get("agents") or []:
        if not isinstance(agent, dict) or not agent.get("enabled", True):
            continue
        if not str(agent.get("id") or "").strip():
            continue
        out.append(agent)
    return out


def _agents_for_tick(agents: List[Dict[str, Any]], tick_count: int, max_n: int) -> List[Dict[str, Any]]:
    if max_n <= 0 or max_n >= len(agents):
        return agents
    if not agents:
        return []
    start = (max(0, tick_count) - 1) % len(agents)
    picked: List[Dict[str, Any]] = []
    for i in range(max_n):
        picked.append(agents[(start + i) % len(agents)])
    return picked


def tick(*, force: bool = False) -> Dict[str, Any]:
    cfg = _agent_config()
    if not cfg.get("enabled", True) and not force:
        return {"success": False, "error": "agent_trading_disabled"}

    try:
        ex.ensure_agent_wallets()
    except Exception:
        pass

    state = _read_state()
    # Dedupe when master daemon + multi-wallet both invoke this in one loop.
    if not force:
        last = str(state.get("last_tick") or "")
        min_gap = int(cfg.get("min_tick_gap_sec") or 45)
        if last and min_gap > 0:
            try:
                ts = last.replace("Z", "+00:00")
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds()
                if age < min_gap:
                    return {
                        "success": True,
                        "skipped": True,
                        "reason": "min_tick_gap",
                        "age_sec": round(age, 1),
                        "tick_count": int(state.get("tick_count") or 0),
                        "mode": state.get("last_mode"),
                    }
            except Exception:
                pass

    tick_count = int(state.get("tick_count") or 0) + 1
    max_trade_mn2 = float(cfg.get("max_trade_mn2_per_tick") or 2.5)
    seed_mn2 = float(cfg.get("seed_mn2_per_agent") or 25.0)
    venue_id = str(cfg.get("venue_id") or "binance").lower()
    live = _venue_live_ready(venue_id)
    actions: List[Dict[str, Any]] = []

    all_agents = _enabled_agents(cfg)
    max_agents = int(cfg.get("max_agents_per_tick") or (2 if live else len(all_agents) or 0))
    agents = _agents_for_tick(all_agents, tick_count, max_agents if live else len(all_agents))

    if live:
        try:
            from backend.services import exchange_venue_api_service as vapi
            vapi.refresh_venue_balances([venue_id], force=True)
        except Exception:
            pass

    for agent in agents:
        agent_id = str(agent.get("id") or "").strip()
        try:
            if not live:
                _seed_agent_mn2(agent_id, seed_mn2, tick_count=tick_count)
            action = _trade_agent(agent, tick_count, max_trade_mn2)
        except Exception as exc:
            action = {
                "agent_id": agent_id,
                "agent_name": agent.get("name") or agent_id,
                "success": False,
                "error": str(exc),
            }
        actions.append(action)
        state.setdefault("agents", {})[agent_id] = {
            "last_action": action,
            "last_tick": _iso(),
        }

    pool_action: Dict[str, Any] = {"skipped": True}
    try:
        from backend.services.exchange_mn2_pool_agent_service import tick as pool_tick

        pool_action = pool_tick()
        actions.append({
            "agent_id": pool_action.get("agent_id") or "exchange_agent_mn2_pool",
            "agent_name": "MN2 Pool Controller",
            "strategy": "mn2_pool",
            "success": bool(pool_action.get("success")),
            "error": pool_action.get("error"),
            "pool_assets": (pool_action.get("status") or {}).get("pool_assets"),
        })
    except Exception as exc:
        actions.append({
            "agent_id": "exchange_agent_mn2_pool",
            "agent_name": "MN2 Pool Controller",
            "strategy": "mn2_pool",
            "success": False,
            "error": str(exc),
        })

    mode = "live" if live else "internal"
    state["tick_count"] = tick_count
    state["last_tick"] = _iso()
    state["last_mode"] = mode
    _write_state(state)
    return {
        "success": True,
        "tick_count": tick_count,
        "actions": actions,
        "pool_tick": pool_action,
        "state": state,
        "mode": mode,
        "venue_id": venue_id if live else None,
        "agents_traded": len(agents),
    }


def run_daemon(interval_sec: int | None = None) -> None:
    cfg = _agent_config()
    interval = int(interval_sec or cfg.get("daemon_interval_sec") or 300)
    while True:
        tick()
        time.sleep(max(5, interval))
