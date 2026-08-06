"""Trader agent market-making service (Stage 2 / Gate C)."""
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional

STRATEGIES = (
    "market_maker",
    "momentum",
    "mean_reversion",
    "arbitrage",
    "sniper",
    "liquidity",
)


def list_strategies() -> List[str]:
    return list(STRATEGIES)


def _trader_agent_ids() -> List[str]:
    from backend.services.agent_wallet_service import get_treasury
    count = int(get_treasury().get("trader_agent_count") or 6)
    return [f"trader_agent_{i + 1}" for i in range(max(1, count))]


def _market_cfg() -> Dict[str, Any]:
    try:
        from backend.services.mn2_staking_service import get_config
        ta = get_config().get("trader_agents") or {}
        m = ta.get("market") if isinstance(ta.get("market"), dict) else {}
        return m if isinstance(m, dict) else {}
    except Exception:
        return {}


def _agent_free_mn2(agent_id: str) -> float:
    from backend.services.unified_points_database import unified_points_db
    bal = unified_points_db.get_all_points(agent_id).get("points") or {}
    return float(bal.get("mn2_balance") or 0)


def _strategy_price(base: float, strategy: str) -> float:
    s = (strategy or "market_maker").strip().lower()
    if s == "momentum":
        return round(base * 1.01, 4)
    if s == "mean_reversion":
        return round(base * 0.99, 4)
    if s == "arbitrage":
        return round(base * 1.005, 4)
    if s == "sniper":
        return round(base * 0.995, 4)
    return round(base, 4)


def run_trader_sell_tick(agent_id: str, strategy: str = "market_maker") -> Dict[str, Any]:
    """Place a sell order for one trader agent if liquidity rules allow."""
    from backend.services.agent_kill_switch import check_action
    from backend.services.p2p_market_service import create_order, list_orders

    gate = check_action("run_agent", agent_id=agent_id)
    if not gate.get("allowed"):
        return {"success": False, "skipped": True, "reason": gate.get("reason", "halted")}

    mcfg = _market_cfg()
    if mcfg.get("enabled") is False:
        return {"success": False, "skipped": True, "reason": "market_disabled"}

    sell_amt = float(mcfg.get("sell_mn2_per_order") or 10)
    min_free = float(mcfg.get("min_free_mn2") or 5)
    max_open = int(mcfg.get("max_open_sells_per_agent") or 2)
    base_price = float(mcfg.get("reference_price_coins_per_mn2") or 100)
    price = _strategy_price(base_price, strategy)

    free = _agent_free_mn2(agent_id)
    if free < min_free + sell_amt:
        return {"success": False, "skipped": True, "reason": "insufficient_free_mn2", "free_mn2": free}

    open_sells = [
        o for o in (list_orders(side="sell").get("orders") or [])
        if o.get("user_id") == agent_id
    ]
    if len(open_sells) >= max_open:
        return {"success": False, "skipped": True, "reason": "max_open_sells"}

    result = create_order(agent_id, "sell", sell_amt, price)
    if result.get("success"):
        try:
            from backend.services.activity_events_service import emit
            emit(
                "trader_market_tick",
                channel="market",
                user_id=agent_id,
                payload={"action": "sell", "strategy": strategy, "order_id": (result.get("order") or {}).get("order_id")},
            )
        except Exception:
            pass
    return result


def run_all_traders() -> Dict[str, Any]:
    """Run sell ticks for all traders, then cross-fill between agents for liquidity."""
    from backend.services.p2p_market_service import fill_order, list_orders
    from backend.services.unified_points_database import unified_points_db

    agents = _trader_agent_ids()
    mcfg = _market_cfg()
    fill_amt = float(mcfg.get("fill_mn2_per_trade") or 5)
    trades = 0

    for aid in agents:
        run_trader_sell_tick(aid, strategy="market_maker")

    sells = list_orders(side="sell").get("orders") or []
    for order in sells:
        seller = order.get("user_id")
        order_id = order.get("order_id")
        if not seller or not order_id:
            continue
        price = float(order.get("price_coins_per_mn2") or 0)
        coins_needed = round(fill_amt * price, 4)
        for buyer in agents:
            if buyer == seller:
                continue
            buyer_bal = unified_points_db.get_all_points(buyer).get("points") or {}
            if float(buyer_bal.get("coins") or 0) < coins_needed:
                unified_points_db.add_points(
                    buyer, "coins", coins_needed * 2,
                    source="agent_trader_float",
                    metadata={"reference": f"trader-float:{buyer}"},
                )
            fr = fill_order(buyer, order_id, fill_amt)
            if fr.get("success"):
                trades += 1
                try:
                    from backend.services.activity_events_service import emit
                    emit(
                        "trader_market_tick",
                        channel="market",
                        user_id=buyer,
                        payload={"action": "fill", "seller": seller, "trade": fr.get("trade")},
                    )
                except Exception:
                    pass
                break

    return {"success": True, "trades": trades, "agents": agents}
