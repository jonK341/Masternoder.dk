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


TREASURY_POOL_USER = "agent_treasury"


def get_treasury_pool_balance() -> float:
    from backend.services.unified_points_database import unified_points_db
    pts = unified_points_db.get_all_points(TREASURY_POOL_USER).get("points") or {}
    bal = float(pts.get("mn2_balance") or 0)
    if bal == 0 and isinstance(pts.get("systems"), dict):
        bal = float(pts["systems"].get("mn2_balance") or 0)
    return bal


def sync_treasury_pool_from_ledger() -> Dict[str, Any]:
    """Credit pool for ledger treasury_deposit rows missing from unified_points (idempotent by txid)."""
    from backend.services.mn2_ledger import _load_entries
    from backend.services.unified_points_database import unified_points_db

    synced = 0
    total = 0.0
    for entry in _load_entries():
        if entry.get("type") != "treasury_deposit":
            continue
        txid = (entry.get("txid") or "").strip()
        amount = float(entry.get("amount") or 0)
        if amount <= 0:
            continue
        ref = f"treasury-pool-sync:{txid or entry.get('created_at')}"
        r = unified_points_db.add_points(
            TREASURY_POOL_USER,
            "mn2_balance",
            amount,
            source="mn2_treasury_deposit",
            metadata={"reference": ref, "txid": txid, "backfill": True},
        )
        if r.get("success") and not r.get("duplicate"):
            synced += 1
            total += amount
    return {"success": True, "synced_count": synced, "synced_total_mn2": round(total, 8)}


def distribute_agent_funding() -> Dict[str, Any]:
    """Idempotent top-up: debit treasury pool, credit each trader agent wallet."""
    sync_treasury_pool_from_ledger()
    treasury = get_treasury()
    per_agent = float(treasury.get("per_agent_mn2") or 100000)
    count = int(treasury.get("trader_agent_count") or 6)
    agent_ids = [f"trader_agent_{i+1}" for i in range(count)]

    estimated_total = 0.0
    for aid in agent_ids:
        gap = round(max(0.0, per_agent - get_balance(aid)), 8)
        estimated_total += gap
    try:
        from backend.services.treasury_signoff_service import assert_distribution_allowed
        gate_err = assert_distribution_allowed(estimated_total_mn2=estimated_total)
        if gate_err:
            return {"success": False, "error": gate_err, "estimated_total_mn2": estimated_total}
    except Exception:
        pass

    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry

    pool = get_treasury_pool_balance()
    results: List[Dict[str, Any]] = []
    distributed_total = 0.0

    for aid in agent_ids:
        current = get_balance(aid)
        gap = round(max(0.0, per_agent - current), 8)
        if gap <= 0:
            results.append({"agent_id": aid, "skipped": True, "reason": "already_funded", "balance": current})
            continue
        if pool < gap:
            results.append({"agent_id": aid, "error": "insufficient_treasury_pool", "needed": gap, "pool": pool})
            continue
        ref = f"treasury-fund:{aid}"
        debit = unified_points_db.add_points(
            TREASURY_POOL_USER, "mn2_balance", -gap,
            source="agent_treasury_distribution",
            metadata={"reference": ref, "agent_id": aid},
        )
        if debit.get("duplicate"):
            results.append({
                "agent_id": aid,
                "skipped": True,
                "reason": "duplicate_debit",
                "balance": current,
            })
            continue
        if not debit.get("success", True):
            results.append({"agent_id": aid, "error": "treasury_debit_failed"})
            continue
        credit(aid, gap, reference=ref, source="agent_treasury")
        try:
            append_entry(user_id=aid, entry_type="agent_treasury_fund", amount=gap, metadata={"reference": ref})
            append_entry(user_id=TREASURY_POOL_USER, entry_type="agent_treasury_debit", amount=-gap, metadata={"reference": ref, "agent_id": aid})
        except Exception:
            pass
        try:
            from backend.services.activity_events_service import emit
            emit("agent_funded", channel="agents", user_id=aid, payload={"amount": gap, "reference": ref})
        except Exception:
            pass
        pool = round(pool - gap, 8)
        distributed_total += gap
        results.append({"agent_id": aid, "credited": gap, "balance": get_balance(aid)})

    return {
        "success": True,
        "distributed_total": distributed_total,
        "pool_remaining": pool,
        "per_agent_mn2": per_agent,
        "results": results,
    }
