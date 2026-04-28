"""
MN2 wallet service (Phase 2): per-user deposit addresses and in-app balance.
Uses mn2_rpc_client for getnewaddress; unified_points_db for mn2_balance.
See docs/MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md Phase 2.
"""
import os
import json
import threading
from typing import Dict, Any, Optional

_ADDRESSES_LOCK = threading.Lock()
_ADDRESSES_FILENAME = "mn2_user_addresses.json"


def _data_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "data")


def _addresses_path() -> str:
    return os.path.join(_data_dir(), _ADDRESSES_FILENAME)


def _load_addresses() -> Dict[str, str]:
    path = _addresses_path()
    with _ADDRESSES_LOCK:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception:
                pass
        return {}


def _save_addresses(addresses: Dict[str, str]) -> None:
    path = _addresses_path()
    os.makedirs(_data_dir(), exist_ok=True)
    with _ADDRESSES_LOCK:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(addresses, f, indent=2)


def _first_pool_key(addresses: Dict[str, str]) -> Optional[str]:
    """Return the first pool_N key (smallest N) if any."""
    pool_keys = [k for k in addresses if isinstance(k, str) and k.startswith("pool_")]
    if not pool_keys:
        return None
    def num(s):
        try:
            return int(s.replace("pool_", ""))
        except ValueError:
            return 999999
    pool_keys.sort(key=num)
    return pool_keys[0]


def get_or_create_deposit_address(user_id: str) -> Dict[str, Any]:
    """
    Return the deposit address for the user. If none exists, use an existing pool address
    if available, else call RPC getnewaddress, store user_id -> address, and return it. Thread-safe.
    """
    if not (user_id or "").strip():
        return {"success": False, "error": "user_id required", "deposit_address": None}

    user_id = str(user_id).strip()
    addresses = _load_addresses()
    if user_id in addresses:
        return {
            "success": True,
            "deposit_address": addresses[user_id],
            "user_id": user_id,
        }

    # Use a pre-created pool address if available (reassign to this user)
    pool_key = _first_pool_key(addresses)
    if pool_key:
        addr = addresses.pop(pool_key)
        addresses[user_id] = addr
        _save_addresses(addresses)
        return {"success": True, "deposit_address": addr, "user_id": user_id}

    from backend.services.mn2_rpc_client import getnewaddress
    r = getnewaddress()
    if r.get("error"):
        return {"success": False, "error": r["error"], "deposit_address": None}
    addr = r.get("result")
    if not addr or not isinstance(addr, str):
        return {"success": False, "error": "RPC getnewaddress returned no address", "deposit_address": None}

    addresses[user_id] = addr.strip()
    _save_addresses(addresses)
    return {"success": True, "deposit_address": addresses[user_id], "user_id": user_id}


def create_deposit_addresses(count: int) -> Dict[str, Any]:
    """
    Ask the daemon to create count new deposit addresses and store them as pool_1, pool_2, ...
    Returns created addresses. Thread-safe. Use for pre-creating addresses (e.g. ops endpoint).
    """
    count = max(1, min(int(count), 100))
    from backend.services.mn2_rpc_client import getnewaddress
    addresses = _load_addresses()
    existing_pool = [k for k in addresses if isinstance(k, str) and k.startswith("pool_")]
    next_n = 1
    if existing_pool:
        def num(s):
            try:
                return int(s.replace("pool_", ""))
            except ValueError:
                return 0
        next_n = max(num(k) for k in existing_pool) + 1
    created = []
    errors = []
    for i in range(count):
        r = getnewaddress()
        if r.get("error"):
            errors.append(r["error"])
            break
        addr = r.get("result")
        if not addr or not isinstance(addr, str):
            errors.append("RPC returned no address")
            break
        key = f"pool_{next_n + i}"
        addresses[key] = addr.strip()
        created.append({"user_id": key, "deposit_address": addresses[key]})
    if created:
        _save_addresses(addresses)
    return {
        "success": len(errors) == 0 and len(created) == count,
        "created": created,
        "count": len(created),
        "error": errors[0] if errors else None,
    }


def get_address_to_user_map() -> Dict[str, str]:
    """Return dict address -> user_id for all assigned deposit addresses (for scanner)."""
    addresses = _load_addresses()
    return {addr: uid for uid, addr in addresses.items() if addr and uid}


def get_balance(user_id: str) -> Dict[str, Any]:
    """Return the user's in-app MN2 balance from unified points (not chain balance)."""
    if not (user_id or "").strip():
        return {"success": False, "error": "user_id required", "mn2_balance": 0}

    try:
        from backend.services.unified_points_database import unified_points_db
        result = unified_points_db.get_all_points(str(user_id).strip())
        if not result.get("success"):
            return {"success": True, "mn2_balance": 0.0, "user_id": user_id}
        points = result.get("points") or {}
        balance = float(points.get("mn2_balance", 0) or 0)
        if balance == 0 and isinstance(points.get("systems"), dict):
            balance = float(points["systems"].get("mn2_balance", 0) or 0)
        return {"success": True, "mn2_balance": balance, "user_id": user_id}
    except Exception as e:
        return {"success": False, "error": str(e), "mn2_balance": 0}
