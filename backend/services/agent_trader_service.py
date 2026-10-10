"""Trader agent strategies for internal P2P market (MN2 ↔ coins) liquidity + flow."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

_STRATEGIES = ("market_maker", "momentum", "mean_reversion", "liquidity", "arbitrage", "sniper")


def list_strategies() -> List[str]:
    return list(_STRATEGIES)


def _market_cfg() -> Dict[str, Any]:
    try:
        import backend.services.mn2_staking_service as staking
        cfg = staking.get_config()
        ta = cfg.get("trader_agents") if isinstance(cfg.get("trader_agents"), dict) else {}
        m = ta.get("market") if isinstance(ta.get("market"), dict) else {}
    except Exception:
        ta, m = {}, {}
    keep = float(ta.get("keep_balance_min_mn2") or 5000)
    return {
        "enabled": bool(m.get("enabled", True)) and bool(ta.get("enabled", True)),
        "keep_balance_min_mn2": keep,
        "sell_mn2_per_order": float(m.get("sell_mn2_per_order") or 50),
        "fill_mn2_per_trade": float(m.get("fill_mn2_per_trade") or 25),
        "min_free_mn2": float(m.get("min_free_mn2") or 100),
        "coin_float_target": float(m.get("coin_float_target") or 10000),
        "max_open_sells_per_agent": int(m.get("max_open_sells_per_agent") or 2),
        "reference_price_coins_per_mn2": float(m.get("reference_price_coins_per_mn2") or 100),
        "price_spread_bps": int(m.get("price_spread_bps") or 50),
    }


def trader_agent_ids() -> List[str]:
    from backend.services.agent_trader_staking_service import trader_agent_ids as _ids
    return _ids()


def _halted(agent_id: str) -> Optional[Dict[str, Any]]:
    try:
        from backend.services.agent_kill_switch import check_action
    except ImportError:
        return None
    gate = check_action("market_trade", agent_id)
    if not gate.get("allowed"):
        return {"success": True, "skipped": True, "reason": gate.get("code"), "agent_id": agent_id}
    return None


def _free_mn2(agent_id: str) -> float:
    import backend.services.mn2_staking_service as staking
    bal, _staked = staking.get_balances(agent_id)
    keep = _market_cfg()["keep_balance_min_mn2"]
    return round(max(0.0, float(bal) - keep), 8)


def _ensure_coin_float(agent_id: str) -> Dict[str, Any]:
    """Give agents coins to buy MN2 from each other (idempotent float credit)."""
    from backend.services.unified_points_database import unified_points_db
    cfg = _market_cfg()
    target = float(cfg["coin_float_target"])
    pts = unified_points_db.get_all_points(agent_id).get("points") or {}
    coins = float(pts.get("coins") or 0)
    if coins >= target * 0.5:
        return {"success": True, "skipped": True, "coins": coins}
    need = round(target - coins, 4)
    ref = f"agent-market-coins:{agent_id}"
    r = unified_points_db.add_points(
        agent_id,
        "coins",
        need,
        source="agent_market_float",
        metadata={"reference": ref, "agent_id": agent_id},
    )
    return {"success": bool(r.get("success", True)), "credited": need, "duplicate": bool(r.get("duplicate"))}


def _strategy_price(strategy: str, sell_prices: List[float], base: float) -> float:
    spread = _market_cfg()["price_spread_bps"] / 10000.0
    if not sell_prices:
        return base
    if strategy == "momentum":
        return round(max(sell_prices) * (1.0 + spread), 4)
    if strategy == "mean_reversion":
        return round(sum(sell_prices) / len(sell_prices), 4)
    if strategy == "sniper":
        return round(min(sell_prices) * (1.0 - spread * 0.5), 4)
    return round(min(sell_prices) * (1.0 - spread), 4)


def run_trader_sell_tick(*, agent_id: str, strategy: str = "market_maker") -> Dict[str, Any]:
    """Post a sell order using free MN2 above the staking keep buffer."""
    from backend.services.p2p_market_service import list_orders, create_order, cancel_order

    halted = _halted(agent_id)
    if halted:
        return halted

    cfg = _market_cfg()
    if not cfg.get("enabled"):
        return {"success": True, "skipped": True, "reason": "market_disabled", "agent_id": agent_id}

    strategy = (strategy or "market_maker").strip().lower()
    if strategy not in _STRATEGIES:
        return {"success": False, "error": "unknown_strategy", "agent_id": agent_id}

    free = _free_mn2(agent_id)
    if free < cfg["min_free_mn2"]:
        return {
            "success": True,
            "skipped": True,
            "reason": "insufficient_free_mn2",
            "agent_id": agent_id,
            "free_mn2": free,
        }

    sells = list_orders(side="sell", limit=40).get("orders") or []
    own = [o for o in sells if o.get("user_id") == agent_id and o.get("status") == "open"]
    if len(own) >= cfg["max_open_sells_per_agent"]:
        return {
            "success": True,
            "skipped": True,
            "reason": "depth_sufficient",
            "agent_id": agent_id,
            "open_orders": len(own),
        }

    if len(own) > 0 and float(own[0].get("remaining_mn2") or 0) > cfg["sell_mn2_per_order"] * 0.25:
        return {"success": True, "skipped": True, "reason": "existing_sell_active", "agent_id": agent_id}

    for stale in own:
        cancel_order(agent_id, stale.get("order_id", ""))

    others = [float(o.get("price_coins_per_mn2") or 0) for o in sells if o.get("user_id") != agent_id]
    price = _strategy_price(strategy, others, cfg["reference_price_coins_per_mn2"])
    amount = min(cfg["sell_mn2_per_order"], free * 0.2)
    amount = round(max(0.01, amount), 8)
    created = create_order(agent_id, "sell", amount, price)
    return {
        "success": bool(created.get("success")),
        "agent_id": agent_id,
        "strategy": strategy,
        "phase": "sell",
        "result": created,
    }


def run_trader_buy_tick(*, agent_id: str) -> Dict[str, Any]:
    """Buy MN2 from another trader's sell order to generate market flow."""
    from backend.services.p2p_market_service import list_orders, fill_order

    halted = _halted(agent_id)
    if halted:
        return halted

    cfg = _market_cfg()
    if not cfg.get("enabled"):
        return {"success": True, "skipped": True, "reason": "market_disabled", "agent_id": agent_id}

    float_res = _ensure_coin_float(agent_id)
    sells = list_orders(side="sell", limit=40).get("orders") or []
    candidates = [
        o for o in sells
        if o.get("user_id") != agent_id
        and o.get("user_id", "").startswith("trader_agent_")
        and float(o.get("remaining_mn2") or 0) > 0
    ]
    if not candidates:
        return {"success": True, "skipped": True, "reason": "no_peer_sells", "agent_id": agent_id}

    candidates.sort(key=lambda o: float(o.get("price_coins_per_mn2") or 0))
    order = candidates[0]
    fill_amt = min(cfg["fill_mn2_per_trade"], float(order.get("remaining_mn2") or 0))
    fill_amt = round(fill_amt, 8)
    if fill_amt <= 0:
        return {"success": True, "skipped": True, "reason": "nothing_to_fill", "agent_id": agent_id}

    filled = fill_order(agent_id, order.get("order_id", ""), fill_amt)
    return {
        "success": bool(filled.get("success")),
        "agent_id": agent_id,
        "phase": "buy",
        "coin_float": float_res,
        "result": filled,
    }


def run_trader_tick(*, agent_id: str = "trader_agent_1", strategy: str = "market_maker") -> Dict[str, Any]:
    """One agent: try sell then buy (single-agent tick)."""
    sell = run_trader_sell_tick(agent_id=agent_id, strategy=strategy)
    buy = run_trader_buy_tick(agent_id=agent_id)
    trades = 0
    if buy.get("result", {}).get("trade"):
        trades = 1
    return {
        "success": sell.get("success") or buy.get("success"),
        "agent_id": agent_id,
        "strategy": strategy,
        "sell": sell,
        "buy": buy,
        "trades": trades,
    }


def run_all_traders() -> Dict[str, Any]:
    """Fleet tick: all agents post sells, then all agents cross-buy for volume."""
    cfg = _market_cfg()
    if not cfg.get("enabled"):
        return {"success": True, "skipped": True, "reason": "market_disabled"}

    ids = trader_agent_ids()
    sell_results: List[Dict[str, Any]] = []
    buy_results: List[Dict[str, Any]] = []
    trade_count = 0
    wallet_sync: List[Dict[str, Any]] = []

    from backend.services.agent_trader_staking_service import sync_trader_wallet_to_points
    for aid in ids:
        try:
            wallet_sync.append(sync_trader_wallet_to_points(aid))
        except Exception as exc:
            wallet_sync.append({"success": False, "agent_id": aid, "error": str(exc)})

    for i, aid in enumerate(ids):
        strat = _STRATEGIES[i % len(_STRATEGIES)]
        try:
            sell_results.append(run_trader_sell_tick(agent_id=aid, strategy=strat))
        except Exception as exc:
            sell_results.append({"success": False, "agent_id": aid, "phase": "sell", "error": str(exc)})

    for aid in ids:
        try:
            br = run_trader_buy_tick(agent_id=aid)
            buy_results.append(br)
            if br.get("result", {}).get("trade"):
                trade_count += 1
        except Exception as exc:
            buy_results.append({"success": False, "agent_id": aid, "phase": "buy", "error": str(exc)})

    result = {
        "success": True,
        "agents": len(ids),
        "trades": trade_count,
        "wallet_sync": wallet_sync,
        "sell_results": sell_results,
        "buy_results": buy_results,
    }
    if trade_count > 0:
        try:
            from backend.services.activity_events_service import emit
            emit(
                "trader_market_tick",
                channel="market",
                text=f"{trade_count} trader cross-trades",
                payload={"trades": trade_count, "agents": len(ids)},
            )
        except Exception:
            pass
    return result
