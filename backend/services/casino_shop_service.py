"""Casino shop — catalog and purchases with coins / MN2 / USD rails."""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOCK = threading.Lock()
_CATALOG_PATH = os.path.join(_ROOT, "data", "casino_shop_catalog.json")


def _log_dir() -> str:
    return os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(_ROOT, "logs")


def _owned_path() -> str:
    os.makedirs(_log_dir(), exist_ok=True)
    return os.path.join(_log_dir(), "casino_shop_owned.json")


def _load_catalog() -> Dict[str, Any]:
    if not os.path.isfile(_CATALOG_PATH):
        return {"items": []}
    try:
        with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"items": []}
    except Exception:
        return {"items": []}


def _load_owned() -> Dict[str, List[str]]:
    path = _owned_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_owned(data: Dict[str, List[str]]) -> None:
    try:
        with open(_owned_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _find_item(item_id: str) -> Optional[Dict[str, Any]]:
    for item in _load_catalog().get("items") or []:
        if isinstance(item, dict) and item.get("id") == item_id:
            return item
    return None


def list_catalog(user_id: Optional[str] = None) -> Dict[str, Any]:
    owned = set(_load_owned().get(user_id or "", []) or [])
    items = []
    for item in _load_catalog().get("items") or []:
        if not isinstance(item, dict):
            continue
        items.append({**item, "owned": item.get("id") in owned})
    return {"success": True, "items": items, "count": len(items)}


def list_owned(user_id: str) -> Dict[str, Any]:
    owned_ids = _load_owned().get(user_id) or []
    catalog = {i.get("id"): i for i in (_load_catalog().get("items") or []) if isinstance(i, dict)}
    rows = []
    for iid in owned_ids:
        item = catalog.get(iid)
        if item:
            rows.append(item)
        else:
            rows.append({"id": iid, "name": iid})
    return {"success": True, "user_id": user_id, "owned": rows, "count": len(rows)}


def owned_count(user_id: str) -> int:
    return len(_load_owned().get(user_id) or [])


def purchase(user_id: str, item_id: str, currency: str = "coins") -> Dict[str, Any]:
    item = _find_item(item_id)
    if not item:
        return {"success": False, "error": "Item not found"}
    if not item.get("cosmetic_only", True):
        return {"success": False, "error": "Item is not available"}
    currency = (currency or "coins").lower()
    if currency == "fiat":
        currency = "usd"

    with _LOCK:
        owned = _load_owned()
        user_owned = set(owned.get(user_id) or [])
        if item_id in user_owned and item.get("category") != "booster":
            return {"success": False, "error": "Already owned", "code": "ALREADY_OWNED"}

    price_key = f"price_{currency}"
    price = item.get(price_key)
    if price is None:
        if currency != "coins":
            return {"success": False, "error": f"Item not available for {currency}"}
        price = item.get("price_coins")
    if price is None or float(price) <= 0:
        return {"success": False, "error": "Invalid price"}

    try:
        from backend.services.casino_service import _apply_balance_delta, _normalize_currency, _validate_bet
        currency = _normalize_currency(currency)
        err = _validate_bet(user_id, price, currency)
        if err:
            return {"success": False, "error": err}
        _apply_balance_delta(user_id, -float(price), currency, "casino_shop", {"item_id": item_id})
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    qty = int(item.get("quantity") or 1)
    with _LOCK:
        owned = _load_owned()
        user_list = list(owned.get(user_id) or [])
        for _ in range(qty):
            user_list.append(item_id)
        owned[user_id] = user_list
        _save_owned(owned)

    try:
        from backend.services.shop_db_service import add_to_inventory
        add_to_inventory(user_id, item_id, item.get("name") or item_id, qty)
    except Exception:
        pass

    try:
        from backend.services import casino_progression
        casino_progression.on_event(user_id, "shop_purchase", {"item_id": item_id, "owned_count": len(user_list)})
    except Exception:
        pass

    return {
        "success": True,
        "item": item,
        "currency": currency,
        "price": float(price),
        "quantity": qty,
    }
