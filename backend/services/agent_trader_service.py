"""Trader agent strategies for internal P2P market (MN2 ↔ coins) liquidity + flow."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

_STRATEGIES = ("market_maker", "momentum", "mean_reversion", "liquidity", "arbitrage", "sniper")

# Level-gated unlocks (Phase 4): strategy access + order-size multipliers.
_STRATEGY_MIN_LEVEL = {
    "market_maker": 1,
    "momentum": 2,
    "mean_reversion": 2,
    "liquidity": 3,
    "arbitrage": 3,
    "sniper": 4,
}
_LEVEL_SIZE_MULT = {1: 0.5, 2: 0.75, 3: 1.0, 4: 1.25, 5: 1.5}


def list_strategies() -> List[str]:
    return list(_STRATEGIES)


def agent_level(agent_id: str) -> int:
    """Best-effort agent level (defaults via stable bootstrap from agent id)."""
    # Prefer lightweight skillset file read — never construct AgentSkillset (side-effect heavy).
    try:
        import json
        import os

        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "logs",
            "agent_skillsets",
            "skillsets.json",
        )
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            row = ((data.get("agents") or {}).get(agent_id)) or {}
            if row.get("level"):
                return max(1, int(row.get("level") or 1))
            xp = int(row.get("experience") or row.get("xp") or 0)
            if xp > 0:
                return max(1, xp // 500 + 1)
    except Exception:
        pass
    # Stable bootstrap: later fleet indices start slightly higher for variety.
    try:
        n = int(str(agent_id).rsplit("_", 1)[-1])
        return max(1, min(5, 1 + (n - 1) // 2))
    except Exception:
        return 1


def unlocked_strategies(level: int) -> List[str]:
    lvl = max(1, int(level or 1))
    return [s for s in _STRATEGIES if int(_STRATEGY_MIN_LEVEL.get(s, 99)) <= lvl]


def resolve_strategy(agent_id: str, strategy: str) -> Dict[str, Any]:
    """Clamp requested strategy to what the agent's level unlocks."""
    level = agent_level(agent_id)
    allowed = unlocked_strategies(level)
    req = (strategy or "market_maker").strip().lower()
    if req not in _STRATEGIES:
        return {
            "strategy": "market_maker",
            "level": level,
            "allowed": allowed,
            "downgraded": True,
            "reason": "unknown_strategy",
        }
    if req not in allowed:
        fallback = allowed[-1] if allowed else "market_maker"
        return {
            "strategy": fallback,
            "level": level,
            "allowed": allowed,
            "downgraded": True,
            "reason": "level_locked",
            "requested": req,
        }
    return {"strategy": req, "level": level, "allowed": allowed, "downgraded": False}


def size_multiplier(level: int) -> float:
    lvl = max(1, int(level or 1))
    if lvl in _LEVEL_SIZE_MULT:
        return float(_LEVEL_SIZE_MULT[lvl])
    if lvl > 5:
        return 1.75
    return 1.0


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
    try:
        from backend.services.agent_wallet_service import trader_agent_ids as _wallet_ids
        ids = _wallet_ids()
        if ids:
            return ids
    except Exception:
        pass
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
    import random

    spread = _market_cfg()["price_spread_bps"] / 10000.0
    mid = (sum(sell_prices) / len(sell_prices)) if sell_prices else base
    low = min(sell_prices) if sell_prices else base
    high = max(sell_prices) if sell_prices else base
    if strategy == "momentum":
        return round(high * (1.0 + spread), 4)
    if strategy == "mean_reversion":
        return round(mid, 4)
    if strategy == "sniper":
        return round(low * (1.0 - spread * 0.5), 4)
    if strategy == "arbitrage":
        return round(mid * (1.0 + spread * 0.25), 4)
    if strategy == "liquidity":
        # Random-walk liquidity around the touch — keeps depth without a static peg.
        jitter = 1.0 + (random.random() - 0.5) * spread * 2.0
        return round(low * jitter, 4)
    return round(low * (1.0 - spread), 4)


def run_trader_sell_tick(*, agent_id: str, strategy: str = "market_maker") -> Dict[str, Any]:
    """Post a sell order using free MN2 above the staking keep buffer."""
    from backend.services.p2p_market_service import list_orders, create_order, cancel_order

    halted = _halted(agent_id)
    if halted:
        return halted

    cfg = _market_cfg()
    if not cfg.get("enabled"):
        return {"success": True, "skipped": True, "reason": "market_disabled", "agent_id": agent_id}

    resolved = resolve_strategy(agent_id, strategy)
    strategy = resolved["strategy"]
    level = int(resolved["level"])
    mult = size_multiplier(level)

    free = _free_mn2(agent_id)
    min_free = max(0.01, float(cfg["min_free_mn2"]) * (0.5 if level <= 1 else 1.0))
    if free < min_free:
        return {
            "success": True,
            "skipped": True,
            "reason": "insufficient_free_mn2",
            "agent_id": agent_id,
            "free_mn2": free,
            "level": level,
        }

    sells = list_orders(side="sell", limit=40).get("orders") or []
    own = [o for o in sells if o.get("user_id") == agent_id and o.get("status") == "open"]
    max_open = max(1, int(cfg["max_open_sells_per_agent"] + (1 if level >= 4 else 0)))
    if len(own) >= max_open:
        return {
            "success": True,
            "skipped": True,
            "reason": "depth_sufficient",
            "agent_id": agent_id,
            "open_orders": len(own),
            "level": level,
        }

    if len(own) > 0 and float(own[0].get("remaining_mn2") or 0) > cfg["sell_mn2_per_order"] * 0.25:
        return {"success": True, "skipped": True, "reason": "existing_sell_active", "agent_id": agent_id, "level": level}

    for stale in own:
        cancel_order(agent_id, stale.get("order_id", ""))

    others = [float(o.get("price_coins_per_mn2") or 0) for o in sells if o.get("user_id") != agent_id]
    price = _strategy_price(strategy, others, cfg["reference_price_coins_per_mn2"])
    amount = min(cfg["sell_mn2_per_order"] * mult, free * 0.2 * mult)
    amount = round(max(0.01, amount), 8)
    created = create_order(agent_id, "sell", amount, price)
    return {
        "success": bool(created.get("success")),
        "agent_id": agent_id,
        "strategy": strategy,
        "level": level,
        "size_mult": mult,
        "downgraded": resolved.get("downgraded"),
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
        preferred = _STRATEGIES[i % len(_STRATEGIES)]
        strat = resolve_strategy(aid, preferred)["strategy"]
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
