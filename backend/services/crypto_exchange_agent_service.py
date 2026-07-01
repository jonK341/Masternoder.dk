"""Exchange cross-trading agents and daemon tick helpers."""
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
    agents = []
    for row in cfg.get("agents") or []:
        if not isinstance(row, dict):
            continue
        aid = row.get("id")
        agents.append({
            **row,
            "state": (state.get("agents") or {}).get(aid, {}),
        })
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "daemon_interval_sec": int(cfg.get("daemon_interval_sec") or 300),
        "agents": agents,
        "tick_count": int(state.get("tick_count") or 0),
        "last_tick": state.get("last_tick"),
    }


def _seed_agent_mn2(agent_id: str, target_mn2: float) -> None:
    from backend.services.unified_points_database import unified_points_db

    bal = ex._get_quote_balance(agent_id, "MN2")
    if bal >= target_mn2:
        return
    unified_points_db.add_points(
        agent_id,
        "mn2_balance",
        target_mn2 - bal,
        source="exchange_agent_seed",
        metadata={"reference": f"exchange-agent-seed:{agent_id}", "non_withdrawable": True},
    )


def _pick_asset(agent: Dict[str, Any], tick_count: int) -> str:
    assets = [str(a).upper() for a in (agent.get("assets") or []) if str(a).upper() != "MN2"]
    if not assets:
        assets = ["USDC"]
    return assets[tick_count % len(assets)]


def _trade_agent(agent: Dict[str, Any], tick_count: int, max_trade_mn2: float) -> Dict[str, Any]:
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
    }


def tick(*, force: bool = False) -> Dict[str, Any]:
    cfg = _agent_config()
    if not cfg.get("enabled", True) and not force:
        return {"success": False, "error": "agent_trading_disabled"}

    state = _read_state()
    tick_count = int(state.get("tick_count") or 0) + 1
    max_trade_mn2 = float(cfg.get("max_trade_mn2_per_tick") or 2.5)
    seed_mn2 = float(cfg.get("seed_mn2_per_agent") or 25.0)
    actions: List[Dict[str, Any]] = []

    for agent in cfg.get("agents") or []:
        if not isinstance(agent, dict) or not agent.get("enabled", True):
            continue
        agent_id = str(agent.get("id") or "").strip()
        if not agent_id:
            continue
        try:
            _seed_agent_mn2(agent_id, seed_mn2)
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

    state["tick_count"] = tick_count
    state["last_tick"] = _iso()
    _write_state(state)
    return {"success": True, "tick_count": tick_count, "actions": actions, "state": state}


def run_daemon(interval_sec: int | None = None) -> None:
    cfg = _agent_config()
    interval = int(interval_sec or cfg.get("daemon_interval_sec") or 300)
    while True:
        tick()
        time.sleep(max(5, interval))
