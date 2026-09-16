"""
MN2 micro-transactions — maximize on-chain activity with dust-sized reward payouts.

Each successful micro credit with chain_reward_payouts enabled becomes one sendtoaddress tx.
Runs on agent cron alongside ecosystem settlement.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STATE_FILE = os.path.join(_BASE, "data", "mn2_micro_tx_state.json")
_CFG_FILE = os.path.join(_BASE, "data", "mn2_config.json")

_MICRO_ACTIONS = (
    "aggregator_pulse",
    "battle_ping",
    "generator_pulse",
    "activity_tick",
    "staking_ping",
    "shop_agent_nibble",
)


def _utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _utc_hour() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H")


def _read_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def micro_config() -> Dict[str, Any]:
    root = _read_json(_CFG_FILE)
    micro = root.get("micro_transactions") if isinstance(root.get("micro_transactions"), dict) else {}
    chain = root.get("chain_reward_payouts") if isinstance(root.get("chain_reward_payouts"), dict) else {}
    return {
        "enabled": bool(micro.get("enabled", False)),
        "amount_mn2": float(micro.get("amount_mn2") or 0.00001),
        "max_per_run": int(micro.get("max_per_run") or 60),
        "max_per_user_per_day": int(micro.get("max_per_user_per_day") or 48),
        "split_parts": int(micro.get("split_parts") or 1),
        "actions": list(micro.get("actions") or _MICRO_ACTIONS),
        "chain_enabled": bool(chain.get("enabled", False)),
        "min_chain_mn2": float(chain.get("min_amount_mn2") or 0.0001),
    }


def micro_transactions_enabled() -> bool:
    cfg = micro_config()
    return cfg["enabled"] and cfg["chain_enabled"]


def _load_state() -> dict:
    return _read_json(_STATE_FILE)


def _save_state(state: dict) -> None:
    _write_json(_STATE_FILE, state)


def _user_daily_count(state: dict, user_id: str) -> int:
    day = _utc_day()
    users = state.get("users") if isinstance(state.get("users"), dict) else {}
    row = users.get(user_id) if isinstance(users.get(user_id), dict) else {}
    if row.get("date") != day:
        return 0
    try:
        return int(row.get("count") or 0)
    except (TypeError, ValueError):
        return 0


def _bump_user_count(state: dict, user_id: str, n: int = 1) -> None:
    day = _utc_day()
    users = state.setdefault("users", {})
    row = users.setdefault(user_id, {})
    if row.get("date") != day:
        row["date"] = day
        row["count"] = 0
    row["count"] = int(row.get("count") or 0) + n


def _discover_users(limit: int = 80) -> List[str]:
    from backend.services.agent_mn2_settlement_service import _discover_active_user_ids
    return _discover_active_user_ids(limit=limit)


def _credit_micro(
    user_id: str,
    amount: float,
    action: str,
    *,
    slot: int,
    dry_run: bool = False,
) -> Dict[str, Any]:
    ref = f"micro:{action}:{user_id}:{_utc_hour()}:{slot}"
    if dry_run:
        return {"success": True, "dry_run": True, "reference": ref, "amount": amount}
    from backend.services.game_mn2_rewards import credit_mn2
    return credit_mn2(
        user_id,
        amount,
        source="micro_transaction",
        reference=ref,
        metadata={"micro_action": action, "cron": True},
    )


def _split_amount(total: float, parts: int) -> List[float]:
    parts = max(1, min(parts, 20))
    if parts == 1:
        return [round(total, 8)]
    per = round(total / parts, 8)
    if per <= 0:
        return [round(total, 8)]
    amounts = [per] * parts
    # fix rounding drift on last part
    drift = round(total - per * parts, 8)
    if drift:
        amounts[-1] = round(amounts[-1] + drift, 8)
    return amounts


def run_micro_transaction_burst(
    *,
    max_txs: Optional[int] = None,
    dry_run: bool = False,
    user_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Fire as many dust on-chain MN2 payouts as limits allow.
    One credit_mn2 per micro slot → one sendtoaddress when chain payouts are on.
    """
    cfg = micro_config()
    out: Dict[str, Any] = {
        "success": True,
        "enabled": cfg["enabled"],
        "chain_enabled": cfg["chain_enabled"],
        "dry_run": dry_run,
        "attempted": 0,
        "on_chain": 0,
        "in_app_only": 0,
        "skipped": 0,
        "errors": [],
        "txids": [],
    }

    if not cfg["enabled"]:
        out["skipped_reason"] = "micro_transactions_disabled"
        return out
    if not cfg["chain_enabled"] and not dry_run:
        out["skipped_reason"] = "chain_reward_payouts_disabled"
        out["success"] = False
        return out

    cap = max_txs if max_txs is not None else cfg["max_per_run"]
    cap = max(1, min(cap, 200))
    amount = max(cfg["amount_mn2"], cfg["min_chain_mn2"])
    actions = [a for a in cfg["actions"] if a in _MICRO_ACTIONS] or list(_MICRO_ACTIONS)
    split_parts = max(1, cfg["split_parts"])
    amounts = _split_amount(amount, split_parts)

    users = [str(u).strip() for u in (user_ids or _discover_users(limit=cap * 2)) if str(u).strip()]
    if not users:
        users = ["default_user"]

    state = _load_state()
    slot = 0

    for user_id in users:
        if out["attempted"] >= cap:
            break
        if _user_daily_count(state, user_id) >= cfg["max_per_user_per_day"]:
            out["skipped"] += 1
            continue
        action = actions[out["attempted"] % len(actions)]
        for part_i, part_amt in enumerate(amounts):
            if out["attempted"] >= cap:
                break
            if _user_daily_count(state, user_id) >= cfg["max_per_user_per_day"]:
                break
            out["attempted"] += 1
            try:
                res = _credit_micro(user_id, part_amt, action, slot=slot, dry_run=dry_run)
                slot += 1
                if res.get("chain_txid"):
                    out["on_chain"] += 1
                    out["txids"].append(res["chain_txid"])
                    _bump_user_count(state, user_id, 1)
                elif res.get("success") and not res.get("duplicate"):
                    out["in_app_only"] += 1
                    _bump_user_count(state, user_id, 1)
                elif res.get("duplicate"):
                    out["skipped"] += 1
                else:
                    out["errors"].append(f"{user_id}:{res.get('error') or 'failed'}")
            except Exception as e:
                out["errors"].append(f"{user_id}:{str(e)[:120]}")

    if not dry_run:
        state.setdefault("runs", []).append(
            {
                "at": datetime.now(timezone.utc).isoformat(),
                "attempted": out["attempted"],
                "on_chain": out["on_chain"],
            }
        )
        state["runs"] = state["runs"][-50:]
        _save_state(state)

    if out["errors"] and out["on_chain"] == 0 and out["in_app_only"] == 0:
        out["success"] = False
    return out
