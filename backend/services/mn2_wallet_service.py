"""
MN2 wallet service (Phase 2): per-user deposit addresses and in-app balance.
Uses mn2_rpc_client for getnewaddress; unified_points_db for mn2_balance.
See docs/MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md Phase 2.
"""
import os
import json
import threading
from typing import Dict, Any, Optional, List

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


def _address_validity(addr: str) -> Optional[bool]:
    """Ask the daemon whether `addr` is usable as one of OUR deposit addresses.

    Returns:
      - False when the daemon definitively says it's malformed (`isvalid: false`)
        OR well-formed but not owned by the current wallet (`ismine: false`) —
        deposits to a not-owned address are invisible/unrecoverable, so it must
        be regenerated.
      - True when the daemon confirms it's valid (and owned, when reported).
      - None when validation is unavailable (RPC error / daemon down / method
        unimplemented). Per the daemon-is-source-of-truth policy we must NOT
        treat an RPC outage as "invalid" — that would wrongly discard good
        addresses when the node is offline.
    """
    if not addr or not isinstance(addr, str):
        return False
    try:
        from backend.services.mn2_rpc_client import validateaddress
        r = validateaddress(addr.strip())
    except Exception:
        return None
    if r.get("error"):
        return None
    res = r.get("result")
    if not isinstance(res, dict) or "isvalid" not in res:
        return None
    if not res.get("isvalid"):
        return False
    # Well-formed. If the daemon reports ownership, require it to be ours.
    if "ismine" in res and res.get("ismine") is False:
        if not _wallet_info_ready():
            return None
        return False
    return True


def _wallet_info_ready() -> bool:
    """False when getwalletinfo is missing or the daemon cannot answer."""
    try:
        from backend.services.mn2_rpc_client import getwalletinfo
        info = getwalletinfo()
    except Exception:
        return False
    if not isinstance(info, dict) or info.get("error"):
        return False
    return isinstance(info.get("result"), dict)


_UNLOCK_MARKERS = (
    "wallet is locked",
    "wallet locked",
    "please enter the wallet passphrase",
    "walletpassphrase",
    "unlock needed",
    "wallet unlock",
)


def _rpc_needs_unlock(err: str) -> bool:
    text = (err or "").lower()
    return any(marker in text for marker in _UNLOCK_MARKERS)


def _extract_rpc_address(result: Any) -> Optional[str]:
    if isinstance(result, str):
        return result.strip() or None
    if isinstance(result, dict):
        for key in ("address", "addr"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _unlock_daemon_wallet_for_keys() -> Dict[str, Any]:
    """Full unlock (not staking-only) so getnewaddress can refill the keypool."""
    passphrase = (os.environ.get("MN2_WALLET_PASSPHRASE") or "").strip()
    if not passphrase:
        return {
            "success": False,
            "code": "wallet_unlock_needed",
            "error": "Wallet is locked. Set MN2_WALLET_PASSPHRASE so a new address can be created.",
        }
    from backend.services.mn2_rpc_client import walletpassphrase

    unlocked = walletpassphrase(passphrase, 120, False)
    if unlocked.get("error"):
        return {"success": False, "code": "wallet_unlock_failed", "error": unlocked["error"]}
    return {"success": True}


def generate_daemon_address() -> Dict[str, Any]:
    """Create one receive address on the site daemon wallet.

    This is the only application path that calls RPC ``getnewaddress``.
    Deposit addresses, shop revenue labels, order payments, encoder orders,
    masternode collateral, hosting quotes, and the agent treasury all use it.
    """
    from backend.services.mn2_rpc_client import getnewaddress

    last_err = None
    code = "address_failed"
    tried_unlock = False
    for _ in range(3):
        try:
            rpc_result = getnewaddress()
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "code": "rpc_error",
                "deposit_address": None,
                "address": None,
            }
        if not isinstance(rpc_result, dict):
            last_err = "RPC getnewaddress returned an unexpected payload"
            code = "rpc_error"
            continue
        err = rpc_result.get("error")
        if err:
            last_err = str(err)
            code = "rpc_error"
            if not tried_unlock and _rpc_needs_unlock(last_err):
                tried_unlock = True
                unlock = _unlock_daemon_wallet_for_keys()
                if not unlock.get("success"):
                    return {
                        "success": False,
                        "error": unlock.get("error"),
                        "code": unlock.get("code") or "wallet_unlock_needed",
                        "deposit_address": None,
                        "address": None,
                    }
                continue
            break
        addr = _extract_rpc_address(rpc_result.get("result"))
        if not addr:
            last_err = "RPC getnewaddress returned no address"
            code = "no_address"
            continue
        if _address_validity(addr) is False:
            last_err = "getnewaddress returned an address the daemon rejected"
            code = "address_rejected"
            continue
        return {"success": True, "deposit_address": addr, "address": addr, "code": None}
    return {
        "success": False,
        "error": last_err or "could not generate a valid address",
        "code": code,
        "deposit_address": None,
        "address": None,
    }


def _generate_valid_address(max_attempts: int = 3) -> Dict[str, Any]:
    """Generate a fresh address via getnewaddress, skipping any the daemon rejects."""
    del max_attempts  # retries and unlock live in generate_daemon_address
    return generate_daemon_address()


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

    # Return the user's existing address, but self-heal if the daemon says it's
    # invalid (e.g. generated by a previous/different wallet). Only regenerate on
    # a *definitive* invalid; an RPC outage (None) must keep the existing address.
    if user_id in addresses:
        existing = _entry_primary(addresses[user_id])
        validity = _address_validity(existing) if existing else False
        if existing and validity is not False:
            payload = {"success": True, "deposit_address": existing, "user_id": user_id}
            if validity is None and not _wallet_info_ready():
                payload["address_warning"] = (
                    "Wallet is not ready to confirm ownership; kept the existing deposit address."
                )
            return payload
        addresses.pop(user_id, None)

    # Use a pre-created pool address if available (reassign to this user),
    # skipping any pool entries the daemon rejects as invalid.
    while True:
        pool_key = _first_pool_key(addresses)
        if not pool_key:
            break
        addr = addresses.pop(pool_key)
        if _address_validity(addr) is False:
            continue  # discard invalid pool address, try the next one
        addresses[user_id] = addr
        _save_addresses(addresses)
        return {"success": True, "deposit_address": addr, "user_id": user_id}

    gen = _generate_valid_address()
    if not gen.get("success"):
        _save_addresses(addresses)
        return {"success": False, "error": gen.get("error"), "deposit_address": None}

    new_addr = gen["deposit_address"]
    addresses[user_id] = {
        "primary": new_addr,
        "wallet_type": "core",
        "addresses": [{"label": "primary", "address": new_addr, "type": "core", "active": True}],
    }
    _save_addresses(addresses)
    return {"success": True, "deposit_address": new_addr, "user_id": user_id}


def create_deposit_addresses(count: int) -> Dict[str, Any]:
    """
    Ask the daemon to create count new deposit addresses and store them as pool_1, pool_2, ...
    Returns created addresses. Thread-safe. Use for pre-creating addresses (e.g. ops endpoint).
    """
    count = max(1, min(int(count), 100))
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
        generated = generate_daemon_address()
        if not generated.get("success"):
            errors.append(generated.get("error") or "RPC returned no address")
            break
        key = f"pool_{next_n + i}"
        addresses[key] = generated["deposit_address"]
        created.append({"user_id": key, "deposit_address": addresses[key]})
    if created:
        _save_addresses(addresses)
    return {
        "success": len(errors) == 0 and len(created) == count,
        "created": created,
        "count": len(created),
        "error": errors[0] if errors else None,
    }


def _entry_primary(entry: Any) -> Optional[str]:
    """Resolve primary address from legacy string or multi-address dict."""
    if isinstance(entry, str):
        return entry.strip() or None
    if isinstance(entry, dict):
        primary = (entry.get("primary") or "").strip()
        if primary:
            return primary
        addrs = entry.get("addresses")
        if isinstance(addrs, list) and addrs:
            first = addrs[0]
            if isinstance(first, dict):
                return (first.get("address") or "").strip() or None
            if isinstance(first, str):
                return first.strip() or None
    return None


def _all_addresses_for_entry(entry: Any) -> list:
    out = []
    if isinstance(entry, str) and entry.strip():
        out.append(entry.strip())
    elif isinstance(entry, dict):
        addrs = entry.get("addresses")
        if isinstance(addrs, list):
            for row in addrs:
                if isinstance(row, dict) and row.get("address"):
                    out.append(str(row["address"]).strip())
                elif isinstance(row, str) and row.strip():
                    out.append(row.strip())
        primary = (entry.get("primary") or "").strip()
        if primary and primary not in out:
            out.insert(0, primary)
    return [a for a in out if a]


def list_user_addresses(user_id: str) -> Dict[str, Any]:
    """Return all labeled deposit addresses for a user."""
    if not (user_id or "").strip():
        return {"success": False, "error": "user_id required"}
    uid = str(user_id).strip()
    addresses = _load_addresses()
    entry = addresses.get(uid)
    if not entry:
        created = get_or_create_deposit_address(uid)
        if not created.get("success"):
            return created
        entry = addresses.get(uid) or created.get("deposit_address")
    rows = []
    if isinstance(entry, dict) and isinstance(entry.get("addresses"), list):
        rows = [r for r in entry["addresses"] if isinstance(r, dict)]
    else:
        addr = _entry_primary(entry)
        if addr:
            rows = [{"label": "primary", "address": addr, "type": "core", "active": True}]
    return {"success": True, "user_id": uid, "addresses": rows, "wallet_type": (entry or {}).get("wallet_type") if isinstance(entry, dict) else "core"}


def refresh_deposit_address(user_id: str) -> Dict[str, Any]:
    """Rotate primary deposit address (Phase 2 multi-address)."""
    if not (user_id or "").strip():
        return {"success": False, "error": "user_id required"}
    uid = str(user_id).strip()
    gen = _generate_valid_address()
    if not gen.get("success"):
        return gen
    new_addr = gen["deposit_address"]
    addresses = _load_addresses()
    entry = addresses.get(uid)
    if isinstance(entry, dict):
        rows = entry.setdefault("addresses", [])
        if not isinstance(rows, list):
            rows = []
            entry["addresses"] = rows
        for row in rows:
            if isinstance(row, dict):
                row["active"] = False
        rows.append({"label": f"rotated_{len(rows)+1}", "address": new_addr, "type": "core", "active": True, "created_at": __import__("datetime").datetime.utcnow().isoformat() + "Z"})
        entry["primary"] = new_addr
    else:
        old = _entry_primary(entry)
        addresses[uid] = {
            "primary": new_addr,
            "wallet_type": "core",
            "addresses": [
                {"label": "legacy", "address": old, "type": "core", "active": False} if old else None,
                {"label": "primary", "address": new_addr, "type": "core", "active": True},
            ],
        }
        addresses[uid]["addresses"] = [r for r in addresses[uid]["addresses"] if r]
    addresses[uid] = addresses[uid] if isinstance(addresses[uid], dict) else {"primary": new_addr, "addresses": [{"label": "primary", "address": new_addr, "type": "core", "active": True}]}
    _save_addresses(addresses)
    return {"success": True, "user_id": uid, "deposit_address": new_addr}


def connect_external_wallet(user_id: str, address: str, wallet_type: str = "watch") -> Dict[str, Any]:
    """Register an external/watch address (extension/hardware stubs). Does not custody keys."""
    if not (user_id or "").strip():
        return {"success": False, "error": "user_id required"}
    addr = (address or "").strip()
    if not addr:
        return {"success": False, "error": "address required"}
    wtype = (wallet_type or "watch").strip().lower()
    if wtype not in ("watch", "extension", "hardware", "web"):
        return {"success": False, "error": "unsupported wallet_type"}
    validity = _address_validity(addr)
    if validity is False:
        return {"success": False, "error": "invalid_address"}
    uid = str(user_id).strip()
    addresses = _load_addresses()
    entry = addresses.get(uid)
    if not isinstance(entry, dict):
        primary = _entry_primary(entry)
        entry = {"primary": primary, "wallet_type": wtype, "addresses": []}
        if primary:
            entry["addresses"].append({"label": "primary", "address": primary, "type": "core", "active": True})
    entry["wallet_type"] = wtype
    entry.setdefault("addresses", []).append({"label": wtype, "address": addr, "type": wtype, "active": True, "external": True})
    addresses[uid] = entry
    _save_addresses(addresses)
    return {"success": True, "user_id": uid, "address": addr, "wallet_type": wtype}


def get_address_to_user_map() -> Dict[str, str]:
    """Return dict address -> user_id for all assigned deposit addresses (for scanner)."""
    addresses = _load_addresses()
    out: Dict[str, str] = {}
    for uid, entry in addresses.items():
        if not uid or uid.startswith("pool_"):
            continue
        for addr in _all_addresses_for_entry(entry):
            out[addr] = uid
    try:
        from backend.services.agent_wallet_service import get_treasury
        treasury = get_treasury()
        taddr = (treasury.get("address") or "").strip()
        if taddr:
            out[taddr] = "@agent_treasury"
    except Exception:
        pass
    return out


def _coins_per_mn2() -> float:
    try:
        with open(os.path.join(_data_dir(), "mn2_config.json"), "r", encoding="utf-8") as handle:
            return float(json.load(handle).get("coins_per_mn2") or 100)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return 100.0


def frame_user_mn2_wallet(user_id: str) -> Dict[str, Any]:
    """One deposit address per user, with that user's MN2 balance shown as coins.

    Creates the address through getnewaddress when the user has none. Extra
    labeled addresses stay on file but only the primary stays active.
    """
    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required", "deposit_address": None}

    addresses = _load_addresses()
    had_address = bool(_entry_primary(addresses.get(uid)))
    created = get_or_create_deposit_address(uid)
    if not created.get("success"):
        return {
            "success": False,
            "error": created.get("error") or "could not create address",
            "code": created.get("code"),
            "user_id": uid,
            "deposit_address": None,
        }

    addresses = _load_addresses()
    entry = addresses.get(uid)
    primary = _entry_primary(entry) or created.get("deposit_address")
    if isinstance(entry, dict):
        rows = entry.get("addresses")
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    row["active"] = str(row.get("address") or "").strip() == primary
        entry["primary"] = primary
        entry["wallet_type"] = entry.get("wallet_type") or "core"
        entry["framed"] = True
        addresses[uid] = entry
        _save_addresses(addresses)
    elif isinstance(entry, str) and primary:
        addresses[uid] = {
            "primary": primary,
            "wallet_type": "core",
            "framed": True,
            "addresses": [{"label": "primary", "address": primary, "type": "core", "active": True}],
        }
        _save_addresses(addresses)

    bal = get_balance(uid)
    mn2 = float(bal.get("mn2_balance") or 0)
    rate = _coins_per_mn2()
    return {
        "success": True,
        "user_id": uid,
        "deposit_address": primary,
        "created": not had_address,
        "framed": True,
        "wallet_count": 1,
        "mn2_balance": mn2,
        "coins_per_mn2": rate,
        "mn2_coins": int(round(mn2 * rate)),
    }


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
