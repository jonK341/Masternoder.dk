"""Per-agent MN2 wallet balances for trader agents (internal ledger)."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_WALLETS_FILE = os.path.join(_BASE, "data", "agent_wallets.json")
_TREASURY_FILE = os.path.join(_BASE, "data", "agent_treasury.json")
TREASURY_POOL_USER = "agent_treasury"


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def list_wallets() -> List[Dict[str, Any]]:
    with _LOCK:
        store = _read(_WALLETS_FILE)
    agents = store.get("agents") if isinstance(store.get("agents"), dict) else store
    out = []
    for agent_id, row in (agents or {}).items():
        if isinstance(row, dict):
            out.append({"agent_id": agent_id, **row})
        else:
            out.append({"agent_id": agent_id, "mn2_balance": float(row or 0)})
    return out


def get_balance(agent_id: str) -> float:
    with _LOCK:
        store = _read(_WALLETS_FILE)
    agents = store.get("agents") if isinstance(store.get("agents"), dict) else store
    row = (agents or {}).get(agent_id)
    if isinstance(row, dict):
        return float(row.get("mn2_balance") or 0)
    return float(row or 0)


def credit(agent_id: str, amount: float, *, reference: str, source: str = "treasury") -> Dict[str, Any]:
    amt = float(amount or 0)
    if amt <= 0:
        return {"success": False, "error": "amount_must_be_positive"}
    with _LOCK:
        store = _read(_WALLETS_FILE)
        if "agents" not in store or not isinstance(store["agents"], dict):
            store["agents"] = store if store and "agents" not in store else {}
            if "agents" not in store:
                store = {"agents": {}}
        agents = store["agents"]
        row = agents.setdefault(agent_id, {"mn2_balance": 0.0, "history": []})
        if not isinstance(row, dict):
            row = {"mn2_balance": float(row or 0), "history": []}
            agents[agent_id] = row
        row["mn2_balance"] = float(row.get("mn2_balance") or 0) + amt
        row.setdefault("history", []).append({
            "ts": _iso(), "amount": amt, "reference": reference, "source": source,
        })
        store["updated_at"] = _iso()
        _write(_WALLETS_FILE, store)
    return {"success": True, "agent_id": agent_id, "credited": amt, "balance": get_balance(agent_id)}


def get_treasury() -> Dict[str, Any]:
    with _LOCK:
        return _read(_TREASURY_FILE)


def set_treasury_address(address: str, *, per_agent_mn2: float = 100000, trader_count: int = 6) -> Dict[str, Any]:
    with _LOCK:
        data = {
            "address": address,
            "per_agent_mn2": per_agent_mn2,
            "trader_agent_count": trader_count,
            "updated_at": _iso(),
        }
        _write(_TREASURY_FILE, data)
    return {"success": True, **data}


def get_treasury_pool_balance() -> float:
    """MN2 balance in unified_points for the treasury pool account."""
    try:
        from backend.services.unified_points_database import unified_points_db
        bal = unified_points_db.get_all_points(TREASURY_POOL_USER).get("points") or {}
        return float(bal.get("mn2_balance") or 0)
    except Exception:
        return 0.0


def distribute_agent_funding() -> Dict[str, Any]:
    """
    Idempotently top up trader_agent_N wallets from the treasury pool.
    Debits agent_treasury unified_points; credits agent wallet + unified_points per agent.
    """
    from backend.services.treasury_signoff_service import assert_distribution_allowed
    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry

    treasury = get_treasury()
    per_agent = float(treasury.get("per_agent_mn2") or 100000)
    count = int(treasury.get("trader_agent_count") or 6)
    estimated_total = per_agent * count

    block = assert_distribution_allowed(estimated_total_mn2=estimated_total)
    if block:
        return {"success": False, "error": block}

    results: List[Dict[str, Any]] = []
    for i in range(count):
        aid = f"trader_agent_{i + 1}"
        current = get_balance(aid)
        gap = round(per_agent - current, 8)
        if gap <= 0:
            results.append({
                "agent_id": aid,
                "skipped": True,
                "reason": "already_funded",
                "balance": current,
            })
            continue
        pool_bal = get_treasury_pool_balance()
        if pool_bal < gap:
            results.append({
                "agent_id": aid,
                "skipped": True,
                "reason": "insufficient_pool",
                "pool_balance": pool_bal,
                "needed": gap,
            })
            continue

        ref = f"treasury-fund:{aid}"
        meta = {"reference": ref, "agent_id": aid, "source": "agent_treasury"}
        debit = unified_points_db.add_points(
            TREASURY_POOL_USER, "mn2_balance", -gap,
            source="agent_treasury_distribute", metadata=meta,
        )
        if not debit.get("success"):
            results.append({"agent_id": aid, "success": False, "error": debit.get("error", "pool_debit_failed")})
            continue

        unified_points_db.add_points(
            aid, "mn2_balance", gap,
            source="agent_treasury_funding", metadata=meta,
        )
        credit(aid, gap, reference=ref, source="agent_treasury")

        try:
            append_entry(TREASURY_POOL_USER, "treasury_distribution", gap, metadata=meta)
            append_entry(aid, "treasury_funding", gap, metadata=meta)
        except Exception:
            pass
        try:
            from backend.services.activity_events_service import emit
            emit("agent_funded", channel="agents", user_id=aid, payload={"amount": gap, "reference": ref})
        except Exception:
            pass
        results.append({"agent_id": aid, "success": True, "credited": gap, "balance": get_balance(aid)})

    return {"success": True, "results": results, "per_agent_mn2": per_agent, "pool_balance": get_treasury_pool_balance()}
