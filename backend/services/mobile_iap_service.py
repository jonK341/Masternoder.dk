"""D3 — Mobile in-app purchase receipt validation and shop fulfillment (stub + hooks)."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_RECEIPTS_PATH = os.path.join(_BASE, "logs", "monetization", "mobile_iap_receipts.jsonl")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _config() -> Dict[str, Any]:
    try:
        from backend.services.monetization_config_service import _load_raw
        raw = _load_raw()
        block = raw.get("mobile_iap")
        return dict(block) if isinstance(block, dict) else {}
    except Exception:
        return {}


def _products() -> List[Dict[str, Any]]:
    prods = _config().get("products")
    return [dict(p) for p in prods if isinstance(p, dict)] if isinstance(prods, list) else []


def product_for_store_id(store_product_id: str, platform: str) -> Optional[Dict[str, Any]]:
    sid = (store_product_id or "").strip()
    plat = (platform or "").strip().lower()
    for p in _products():
        if (p.get("id") or "") == sid:
            platforms = [str(x).lower() for x in (p.get("platforms") or [])]
            if not platforms or plat in platforms:
                return p
    return None


def public_catalog() -> Dict[str, Any]:
    cfg = _config()
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "validation_mode": (cfg.get("validation_mode") or "stub").strip(),
        "platforms": cfg.get("platforms") or ["apple", "google"],
        "products": [
            {
                "id": p.get("id"),
                "shop_sku": p.get("shop_sku"),
                "price_usd": p.get("price_usd"),
                "coins_granted": p.get("coins_granted"),
                "platforms": p.get("platforms"),
            }
            for p in _products()
        ],
        "note": "POST /api/mobile/iap/fulfill with receipt payload; production needs store API keys.",
    }


def _append_receipt(row: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(_RECEIPTS_PATH), exist_ok=True)
        with _LOCK:
            with open(_RECEIPTS_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _validate_stub(platform: str, receipt_data: str, product: Dict[str, Any]) -> Dict[str, Any]:
    """Dev/stub: accept non-empty receipt containing product id."""
    plat = (platform or "").strip().lower()
    if plat not in ("apple", "google", "ios", "android"):
        return {"success": False, "error": "unsupported_platform"}
    raw = (receipt_data or "").strip()
    pid = (product.get("id") or "").strip()
    if not raw or pid not in raw and raw != "stub_ok":
        return {"success": False, "error": "invalid_receipt_stub"}
    return {"success": True, "transaction_id": f"stub-{plat}-{pid}-{int(datetime.now(timezone.utc).timestamp())}"}


def fulfill_purchase(
    user_id: str,
    *,
    platform: str,
    store_product_id: str,
    receipt_data: str,
    transaction_id: Optional[str] = None,
) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return {"success": False, "error": "auth_required"}

    cfg = _config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "mobile_iap_disabled"}

    product = product_for_store_id(store_product_id, platform)
    if not product:
        return {"success": False, "error": "unknown_product", "store_product_id": store_product_id}

    mode = (cfg.get("validation_mode") or "stub").strip().lower()
    if mode == "stub":
        v = _validate_stub(platform, receipt_data, product)
    else:
        return {"success": False, "error": "store_validation_not_implemented", "validation_mode": mode}

    if not v.get("success"):
        return v

    txn = (transaction_id or v.get("transaction_id") or "").strip()
    sku = (product.get("shop_sku") or "").strip()
    coins = int(product.get("coins_granted") or 0)

    if coins > 0:
        try:
            from backend.services.unified_points_database import unified_points_db
            unified_points_db.add_points(
                user_id=uid,
                point_type="coins",
                amount=coins,
                source="mobile_iap",
                metadata={"platform": platform, "product_id": store_product_id, "transaction_id": txn},
            )
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    if sku:
        try:
            from backend.routes.shop_routes import _apply_shop_item_effects, _digital_good_by_id, _seed_shop_items

            dg = _digital_good_by_id(sku)
            item = dg or {"id": sku, "name": sku, "category": "digital_goods"}
            _apply_shop_item_effects(uid, sku, item, 1)
        except Exception:
            pass

    row = {
        "ts": _iso_now(),
        "user_id": uid,
        "platform": platform,
        "store_product_id": store_product_id,
        "shop_sku": sku,
        "transaction_id": txn,
        "coins_granted": coins,
        "validation_mode": mode,
    }
    _append_receipt(row)

    return {
        "success": True,
        "user_id": uid,
        "platform": platform,
        "store_product_id": store_product_id,
        "shop_sku": sku,
        "coins_granted": coins,
        "transaction_id": txn,
    }
