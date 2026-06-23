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
