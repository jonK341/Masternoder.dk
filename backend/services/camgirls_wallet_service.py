"""
Camgirls wallet catalog and per-user upgrade progress for /api/wallet/v2/camgirls/*.
Mirrors wallet_upgrades_service pattern with separate catalog and progress store.
"""
import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

_CATALOG_CACHE: Optional[Dict[str, Any]] = None
_UPGRADES_CACHE: Optional[Dict[str, Any]] = None
_WALLETS_PROVISIONED = False
_LOCK = threading.RLock()
_GUEST_IDS = frozenset({"", "default_user", "guest"})
_WALLET_ID_PREFIX = "camgirl_"


def _base() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _catalog_path() -> str:
    return os.path.join(_base(), "data", "camgirls_catalog.json")


def _upgrades_path() -> str:
    return os.path.join(_base(), "data", "camgirls_upgrades_catalog.json")


def _wallet_registry_path() -> str:
    return os.path.join(_base(), "data", "camgirls_wallet_registry.json")


def _progress_dir() -> str:
    return os.path.join(_base(), "data", "camgirls_upgrades_progress")


def _progress_path(user_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (user_id or "default_user"))
    return os.path.join(_progress_dir(), f"{safe}.json")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
        f.write("\n")
    os.replace(tmp, path)


def load_performers_catalog() -> Dict[str, Any]:
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE
    path = _catalog_path()
    if not os.path.isfile(path):
        _CATALOG_CACHE = {"version": 1, "total": 0, "performers": []}
        return _CATALOG_CACHE
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {"version": 1, "total": 0, "performers": []}
    except Exception:
        data = {"version": 1, "total": 0, "performers": []}
    _CATALOG_CACHE = data
    return data


def load_upgrades_catalog() -> Dict[str, Any]:
    global _UPGRADES_CACHE
    if _UPGRADES_CACHE is not None:
        return _UPGRADES_CACHE
    path = _upgrades_path()
    if not os.path.isfile(path):
        _UPGRADES_CACHE = {"version": 1, "total": 0, "categories": [], "upgrades": []}
        return _UPGRADES_CACHE
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {"version": 1, "total": 0, "categories": [], "upgrades": []}
    except Exception:
        data = {"version": 1, "total": 0, "categories": [], "upgrades": []}
    _UPGRADES_CACHE = data
    return data


def _upgrade_index() -> Dict[str, Dict[str, Any]]:
    doc = load_upgrades_catalog()
    out: Dict[str, Dict[str, Any]] = {}
    for u in doc.get("upgrades") or []:
        if isinstance(u, dict) and u.get("id"):
            out[str(u["id"])] = u
    return out


def get_upgrade_by_id(upgrade_id: str) -> Optional[Dict[str, Any]]:
    return _upgrade_index().get((upgrade_id or "").strip())


def _get_performer(camgirl_id: str) -> Optional[Dict[str, Any]]:
    cid = (camgirl_id or "").strip()
    if not cid:
        return None
    for p in load_performers_catalog().get("performers") or []:
        if isinstance(p, dict) and str(p.get("id")) == cid:
            return p
    return None


def wallet_user_id_for(camgirl_id: str) -> str:
    """Synthetic ledger user id for a wallet-catalog camgirl."""
    p = _get_performer(camgirl_id)
    if p and p.get("wallet_user_id"):
        return str(p["wallet_user_id"]).strip()
    return f"{_WALLET_ID_PREFIX}{(camgirl_id or '').strip()}"


def _load_wallet_registry() -> Dict[str, Dict[str, Any]]:
    doc = _read_json(_wallet_registry_path())
    wallets = doc.get("wallets") if isinstance(doc.get("wallets"), dict) else {}
    return wallets


def _save_wallet_registry(wallets: Dict[str, Dict[str, Any]]) -> None:
    _write_json(_wallet_registry_path(), {"version": 1, "wallets": wallets, "updated_at": _iso_now()})


def _deposit_address_optional(wallet_user_id: str) -> Optional[str]:
    """Return deposit address only if already provisioned — no RPC in phase 1."""
    try:
        from backend.services.mn2_wallet_service import _load_addresses, _entry_primary
        entry = _load_addresses().get(wallet_user_id)
        return _entry_primary(entry) if entry else None
    except Exception:
        return None


def _explorer_link_for_wallet(wallet_user_id: str) -> Optional[str]:
    addr = _deposit_address_optional(wallet_user_id)
    if not addr:
        return None
    try:
        from backend.services.mn2_explorer_urls import explorer_address_url
        return explorer_address_url(addr) or None
    except Exception:
        return None


def ensure_wallet(camgirl_id: str) -> Dict[str, Any]:
    """Ensure synthetic ledger account exists for a camgirl (0 balance start)."""
    cid = (camgirl_id or "").strip()
    if not cid:
        return {"success": False, "error": "camgirl_id required"}
    performer = _get_performer(cid)
    if not performer:
        return {"success": False, "error": "performer_not_found", "camgirl_id": cid}

    wuid = wallet_user_id_for(cid)
    with _LOCK:
        wallets = _load_wallet_registry()
        if cid not in wallets:
            wallets[cid] = {
                "wallet_user_id": wuid,
                "camgirl_id": cid,
                "name": performer.get("name"),
                "provisioned_at": _iso_now(),
            }
            _save_wallet_registry(wallets)

    from backend.services.mn2_wallet_service import get_balance
    bal = get_balance(wuid)
    return {
        "success": True,
        "camgirl_id": cid,
        "wallet_user_id": wuid,
        "mn2_balance": round(float(bal.get("mn2_balance") or 0), 8),
        "deposit_address": _deposit_address_optional(wuid),
        "explorer_url": _explorer_link_for_wallet(wuid),
    }


def provision_all_wallets() -> None:
    """Auto-provision ledger accounts for all catalog camgirls on first catalog load."""
    global _WALLETS_PROVISIONED
    if _WALLETS_PROVISIONED:
        return
    with _LOCK:
        if _WALLETS_PROVISIONED:
            return
        for p in load_performers_catalog().get("performers") or []:
            if isinstance(p, dict) and p.get("id"):
                ensure_wallet(str(p["id"]))
        _WALLETS_PROVISIONED = True


def get_camgirl_balance(camgirl_id: str) -> Dict[str, Any]:
    detail = ensure_wallet(camgirl_id)
    if not detail.get("success"):
        return detail
    return {
        "success": True,
        "camgirl_id": detail["camgirl_id"],
        "wallet_user_id": detail["wallet_user_id"],
        "mn2_balance": detail["mn2_balance"],
    }


def get_wallet_detail(camgirl_id: str) -> Dict[str, Any]:
    """Full wallet snapshot for one camgirl."""
    detail = ensure_wallet(camgirl_id)
    if not detail.get("success"):
        return detail
    performer = _get_performer(camgirl_id) or {}
    return {
        **detail,
        "name": performer.get("name"),
        "tip_min_mn2": float(performer.get("tip_min_mn2") or 5),
        "explorer_url": detail.get("explorer_url"),
    }


def list_all_wallets() -> Dict[str, Any]:
    provision_all_wallets()
    wallets = []
    for p in load_performers_catalog().get("performers") or []:
        if not isinstance(p, dict) or not p.get("id"):
            continue
        cid = str(p["id"])
        bal = get_camgirl_balance(cid)
        wallets.append({
            "camgirl_id": cid,
            "name": p.get("name"),
            "wallet_user_id": bal.get("wallet_user_id"),
            "mn2_balance": bal.get("mn2_balance", 0),
        })
    return {"success": True, "total": len(wallets), "wallets": wallets}


def _enrich_performer(performer: Dict[str, Any]) -> Dict[str, Any]:
    row = dict(performer)
    cid = str(row.get("id") or "")
    wuid = wallet_user_id_for(cid)
    row["wallet_user_id"] = wuid
    bal = get_camgirl_balance(cid)
    row["mn2_balance"] = bal.get("mn2_balance", 0) if bal.get("success") else 0.0
    row["explorer_url"] = _explorer_link_for_wallet(wuid)
    row["deposit_address"] = _deposit_address_optional(wuid)
    return row


def tip_camgirl(from_user_id: str, camgirl_id: str, amount: float) -> Dict[str, Any]:
    """Transfer MN2 from tipper to camgirl synthetic wallet."""
    from_user_id = (from_user_id or "").strip()
    if from_user_id in _GUEST_IDS:
        return {"success": False, "error": "guest_cannot_tip", "message": "Sign in to send tips."}

    performer = _get_performer(camgirl_id)
    if not performer:
        return {"success": False, "error": "performer_not_found"}

    try:
        amt = round(float(amount), 8)
    except (TypeError, ValueError):
        return {"success": False, "error": "invalid_amount"}

    tip_min = float(performer.get("tip_min_mn2") or 5)
    if amt < tip_min:
        return {"success": False, "error": "below_minimum", "tip_min_mn2": tip_min}

    wallet_detail = ensure_wallet(camgirl_id)
    if not wallet_detail.get("success"):
        return wallet_detail

    recipient = wallet_detail["wallet_user_id"]
    from backend.services.mn2_gift_service import transfer
    note = f"camgirl_tip:{camgirl_id}"
    result = transfer(from_user_id, recipient, amt, note=note)
    if not result.get("success"):
        return result

    new_bal = get_camgirl_balance(camgirl_id)
    return {
        "success": True,
        "camgirl_id": camgirl_id,
        "wallet_user_id": recipient,
        "amount_mn2": amt,
        "from_user_id": from_user_id,
        "camgirl_balance": new_bal.get("mn2_balance"),
        "transfer": result,
    }


def list_performers() -> Dict[str, Any]:
    provision_all_wallets()
    doc = load_performers_catalog()
    performers = [_enrich_performer(p) for p in (doc.get("performers") or []) if isinstance(p, dict)]
    online = sum(1 for p in performers if p.get("online"))
    return {
        "success": True,
        "version": doc.get("version", 1),
        "total": len(performers),
        "online_count": online,
        "performers": performers,
        "studio_url": "/camgirls",
        "wallet_user_id_pattern": f"{_WALLET_ID_PREFIX}{{camgirl_id}}",
    }


def list_upgrades(category: Optional[str] = None) -> Dict[str, Any]:
    doc = load_upgrades_catalog()
    upgrades = doc.get("upgrades") or []
    if category:
        cat = category.strip().lower()
        upgrades = [u for u in upgrades if isinstance(u, dict) and (u.get("category") or "").lower() == cat]
    return {
        "success": True,
        "version": doc.get("version", 1),
        "total": len(upgrades),
        "categories": doc.get("categories") or [],
        "upgrades": upgrades,
    }


def load_user_progress(user_id: str) -> Dict[str, Any]:
    user_id = (user_id or "").strip() or "default_user"
    path = _progress_path(user_id)
    with _LOCK:
        doc = _read_json(path)
    unlocked = doc.get("unlocked_ids") or []
    if not isinstance(unlocked, list):
        unlocked = []
    unlocked_at = doc.get("unlocked_at") if isinstance(doc.get("unlocked_at"), dict) else {}
    return {
        "user_id": user_id,
        "unlocked_ids": [str(x) for x in unlocked if x],
        "unlocked_at": {str(k): v for k, v in unlocked_at.items()},
        "version": int(doc.get("version") or 1),
    }


def _save_user_progress(user_id: str, unlocked_ids: List[str], unlocked_at: Dict[str, str]) -> None:
    path = _progress_path(user_id)
    doc = {
        "version": 1,
        "user_id": user_id,
        "unlocked_ids": unlocked_ids,
        "unlocked_at": unlocked_at,
        "updated_at": _iso_now(),
    }
    with _LOCK:
        _write_json(path, doc)


def _user_wallet_level(user_id: str) -> int:
    if not (user_id or "").strip() or user_id in _GUEST_IDS:
        return 1
    try:
        from backend.services.wallet_upgrades_service import _user_wallet_level as wl
        return wl(user_id)
    except Exception:
        return 1


def _user_mn2_spent(user_id: str) -> float:
    if not (user_id or "").strip() or user_id in _GUEST_IDS:
        return 0.0
    try:
        from backend.services.wallet_upgrades_service import _user_mn2_spent as ms
        return ms(user_id)
    except Exception:
        return 0.0


def _user_trophy_count(user_id: str) -> int:
    if not (user_id or "").strip() or user_id in _GUEST_IDS:
        return 0
    try:
        from backend.services.wallet_upgrades_service import _user_trophy_count as tc
        return tc(user_id)
    except Exception:
        return 0


def _build_user_context(user_id: str, unlocked_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    unlocked = unlocked_ids or []
    return {
        "level": _user_wallet_level(user_id),
        "mn2_spent": _user_mn2_spent(user_id),
        "trophy_count": _user_trophy_count(user_id),
        "upgrade_count": len(unlocked),
    }


def _normalize_unlock_type(utype: str) -> str:
    t = (utype or "default").lower()
    if t in ("default", "always"):
        return "always"
    return t


def _check_unlock_condition(unlock: Dict[str, Any], ctx: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    utype = _normalize_unlock_type(unlock.get("type") or "default")
    value = unlock.get("value")

    if utype == "always":
        return True, None

    if utype == "level":
        try:
            need = int(value or 1)
        except (TypeError, ValueError):
            need = 1
        have = int(ctx.get("level") or 1)
        if have >= need:
            return True, None
        return False, f"Level {have}/{need}"

    if utype == "mn2_spent":
        try:
            need = float(value or 0)
        except (TypeError, ValueError):
            need = 0.0
        have = float(ctx.get("mn2_spent") or 0)
        if have >= need:
            return True, None
        return False, f"Spent {have:.0f}/{need:.0f} MN2"

    if utype == "trophy_count":
        try:
            need = int(value or 0)
        except (TypeError, ValueError):
            need = 0
        have = int(ctx.get("trophy_count") or 0)
        if have >= need:
            return True, None
        return False, f"Trophies {have}/{need}"

    if utype == "upgrade_count":
        try:
            need = int(value or 0)
        except (TypeError, ValueError):
            need = 0
        have = int(ctx.get("upgrade_count") or 0)
        if have >= need:
            return True, None
        return False, f"Unlocks {have}/{need}"

    return False, "Unknown unlock condition"


def get_progress(user_id: str) -> Dict[str, Any]:
    user_id = (user_id or "").strip() or "default_user"
    guest = user_id in _GUEST_IDS
    doc = load_upgrades_catalog()
    upgrades = doc.get("upgrades") or []
    persisted = load_user_progress(user_id)
    unlocked_set = set(persisted["unlocked_ids"])
    ctx = _build_user_context(user_id, persisted["unlocked_ids"])

    unlocked: List[str] = []
    available: List[str] = []
    locked: List[str] = []
    hints: Dict[str, str] = {}
    by_category: Dict[str, Dict[str, int]] = {}

    for u in upgrades:
        if not isinstance(u, dict):
            continue
        uid = u.get("id") or ""
        cat = (u.get("category") or "other").lower()
        if cat not in by_category:
            by_category[cat] = {"unlocked": 0, "available": 0, "locked": 0, "total": 0}
        by_category[cat]["total"] += 1

        if uid in unlocked_set:
            unlocked.append(uid)
            by_category[cat]["unlocked"] += 1
            continue

        unlock = u.get("unlock") if isinstance(u.get("unlock"), dict) else {}
        met, hint = _check_unlock_condition(unlock, ctx)
        if met:
            available.append(uid)
            by_category[cat]["available"] += 1
        else:
            locked.append(uid)
            by_category[cat]["locked"] += 1
            if hint:
                hints[uid] = hint

    return {
        "success": True,
        "user_id": user_id,
        "guest": guest,
        "wallet_level": ctx["level"],
        "mn2_spent": round(float(ctx["mn2_spent"]), 8),
        "trophy_count": ctx["trophy_count"],
        "upgrade_count": len(unlocked),
        "unlocked_count": len(unlocked),
        "available_count": len(available),
        "locked_count": len(locked),
        "total": len(upgrades),
        "unlocked_ids": unlocked,
        "available_ids": available,
        "locked_ids": locked,
        "progress_hints": hints,
        "by_category": by_category,
    }


def unlock_upgrade(user_id: str, upgrade_id: str) -> Dict[str, Any]:
    user_id = (user_id or "").strip() or "default_user"
    upgrade_id = (upgrade_id or "").strip()

    if user_id in _GUEST_IDS:
        return {"success": False, "error": "guest_cannot_unlock", "message": "Sign in to unlock camgirl upgrades."}

    if not upgrade_id:
        return {"success": False, "error": "missing_upgrade_id", "message": "Upgrade id is required."}

    upgrade = get_upgrade_by_id(upgrade_id)
    if not upgrade:
        return {"success": False, "error": "unknown_upgrade", "message": f"Unknown upgrade: {upgrade_id}"}

    progress = load_user_progress(user_id)
    if upgrade_id in progress["unlocked_ids"]:
        return {
            "success": False,
            "error": "already_unlocked",
            "message": f"{upgrade_id} is already unlocked.",
            "upgrade_id": upgrade_id,
        }

    ctx = _build_user_context(user_id, progress["unlocked_ids"])
    unlock = upgrade.get("unlock") if isinstance(upgrade.get("unlock"), dict) else {}
    met, hint = _check_unlock_condition(unlock, ctx)
    if not met:
        return {
            "success": False,
            "error": "conditions_not_met",
            "message": unlock.get("label") or hint or "Unlock conditions not met.",
            "upgrade_id": upgrade_id,
            "progress_hint": hint,
        }

    unlocked_ids = list(progress["unlocked_ids"])
    unlocked_ids.append(upgrade_id)
    unlocked_at = dict(progress["unlocked_at"])
    unlocked_at[upgrade_id] = _iso_now()
    _save_user_progress(user_id, unlocked_ids, unlocked_at)

    return {
        "success": True,
        "upgrade_id": upgrade_id,
        "name": upgrade.get("name"),
        "unlocked_at": unlocked_at[upgrade_id],
        "progress": get_progress(user_id),
    }
