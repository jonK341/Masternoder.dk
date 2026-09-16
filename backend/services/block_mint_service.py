"""Block-height trophy drops — listener, manifest, claim path (plan 001 BM-U1–BM-U5)."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MANIFEST_PATH = os.path.join(_BASE, "data", "block_mint_manifest.json")
_CONFIG_PATH = os.path.join(_BASE, "data", "block_mint_config.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data: Any) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with _LOCK:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)
        return True
    except Exception:
        return False


def get_config() -> Dict[str, Any]:
    return _read_json(
        _CONFIG_PATH,
        {
            "enabled": True,
            "lookback_blocks": 5,
            "base_price_usd": 2.99,
            "floor_price_usd": 0.99,
            "claim_methods": ["mn2", "paypal"],
            "explorer_base_url": "/explorer?height=",
        },
    )


def _current_block_height() -> Optional[int]:
    try:
        from backend.services.mn2_rpc_client import getblockcount

        r = getblockcount(timeout_sec=4)
        if r.get("result") is not None:
            return int(r["result"])
    except Exception:
        pass
    try:
        from backend.services.mn2_chainz import chainz_getblockcount

        ch = chainz_getblockcount()
        if ch is not None:
            return int(ch)
    except Exception:
        pass
    return None


def block_item_id(height: int) -> str:
    return f"block-{int(height)}"


def _media_for_height(height: int) -> Dict[str, str]:
    iid = block_item_id(height)
    media = _read_json(os.path.join(_BASE, "data", "shop_item_media.json"), {})
    row = media.get(iid) or {}
    return {
        "image_url": row.get("image_url") or row.get("poster_url") or f"/static/img/trophies/block-{height}.png",
        "gif_url": row.get("gif_url") or row.get("clip_url") or f"/static/img/trophies/block-{height}.gif",
    }


def _catalog_row(height: int, manifest_row: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = get_config()
    iid = block_item_id(height)
    media = _media_for_height(height)
    claimed = bool((manifest_row or {}).get("claimed_by"))
    return {
        "id": iid,
        "name": f"Block Trophy #{height}",
        "kind": "trophy",
        "series": "block_mint",
        "tags": ["block_mint", "trophy"],
        "category": "trophies",
        "block_height": height,
        "supply": 1,
        "claimed": claimed,
        "claimed_by": (manifest_row or {}).get("claimed_by"),
        "base_price_usd": float(cfg.get("base_price_usd") or 2.99),
        "price": max(99, int(float(cfg.get("base_price_usd") or 2.99) * 100)),
        "on_chain_mint": False,
        "explorer_url": f"{cfg.get('explorer_base_url', '/explorer?height=')}{height}",
        "image_url": media.get("image_url"),
        "gif_url": media.get("gif_url"),
        "shop_url": f"/shop?tab=trophies&series=block-mint&highlight={iid}",
    }


def sync_block_height() -> Dict[str, Any]:
    """Poll chain tip and append unseen block heights to manifest (BM-U1)."""
    cfg = get_config()
    if not cfg.get("enabled", True):
        return {"success": True, "synced": False, "reason": "disabled"}

    height = _current_block_height()
    if height is None:
        return {"success": False, "error": "block_height_unavailable"}

    lookback = max(1, int(cfg.get("lookback_blocks") or 5))
    doc = _read_json(_MANIFEST_PATH, {"drops": {}, "last_height": 0})
    drops = doc.setdefault("drops", {})
    last = int(doc.get("last_height") or 0)
    start = max(last, height - lookback + 1)
    added: List[int] = []
    for h in range(start, height + 1):
        key = str(h)
        if key not in drops:
            drops[key] = {
                "height": h,
                "item_id": block_item_id(h),
                "detected_at": _iso(),
                "claimed_by": None,
                "claimed_at": None,
            }
            added.append(h)
    doc["last_height"] = height
    doc["updated_at"] = _iso()
    _write_json(_MANIFEST_PATH, doc)
    return {"success": True, "block_height": height, "added": added, "total_drops": len(drops)}


def get_block_drops(limit: int = 20) -> Dict[str, Any]:
    sync_block_height()
    doc = _read_json(_MANIFEST_PATH, {"drops": {}, "last_height": 0})
    drops_map = doc.get("drops") or {}
    rows: List[Dict[str, Any]] = []
    for key in sorted(drops_map.keys(), key=lambda x: int(x), reverse=True)[: max(1, min(limit, 100))]:
        manifest_row = drops_map[key]
        h = int(manifest_row.get("height") or key)
        row = _catalog_row(h, manifest_row)
        try:
            from backend.services.trophy_pricing_service import get_effective_price

            pricing = get_effective_price(row["id"])
            if pricing.get("success"):
                row["effective_price_usd"] = pricing.get("effective_price_usd")
                row["price_factors"] = pricing.get("price_factors") or {}
        except Exception:
            row["effective_price_usd"] = row["base_price_usd"]
        rows.append(row)
    return {
        "success": True,
        "block_height": doc.get("last_height"),
        "drops": rows,
        "series": "block_mint",
        "on_chain_mint": False,
    }


def block_mint_shop_items() -> List[Dict[str, Any]]:
    """Merge manifest drops into shop catalog."""
    doc = _read_json(_MANIFEST_PATH, {"drops": {}})
    items: List[Dict[str, Any]] = []
    for key in sorted((doc.get("drops") or {}).keys(), key=lambda x: int(x), reverse=True)[:50]:
        manifest_row = doc["drops"][key]
        h = int(manifest_row.get("height") or key)
        if manifest_row.get("claimed_by"):
            continue
        items.append(_catalog_row(h, manifest_row))
    return items


def claim_block_trophy(
    user_id: str,
    height: int,
    *,
    payment_method: str = "mn2",
) -> Dict[str, Any]:
    """Claim a block trophy edition for a user (BM-U4)."""
    uid = (user_id or "").strip()
    if not uid or uid in ("default_user", "guest"):
        return {"success": False, "error": "guest_blocked"}

    h = int(height)
    iid = block_item_id(h)
    doc = _read_json(_MANIFEST_PATH, {"drops": {}})
    drops = doc.setdefault("drops", {})
    key = str(h)
    if key not in drops:
        sync_block_height()
        doc = _read_json(_MANIFEST_PATH, {"drops": {}})
        drops = doc.get("drops") or {}
        if key not in drops:
            return {"success": False, "error": "block_not_in_manifest", "height": h}

    row = drops[key]
    if row.get("claimed_by"):
        return {
            "success": False,
            "error": "already_claimed",
            "claimed_by": row.get("claimed_by"),
            "height": h,
        }

    method = (payment_method or "mn2").strip().lower()
    catalog = _catalog_row(h, row)

    if method == "mn2":
        from backend.services.trophy_pricing_service import get_effective_price
        from backend.services.unified_points_database import unified_points_db

        pricing = get_effective_price(iid)
        if not pricing.get("success"):
            price_coins = max(1, int(float(catalog.get("base_price_usd") or 2.99) * 100))
        else:
            price_coins = int(pricing.get("effective_price_coins") or 0)
        if price_coins <= 0:
            return {"success": False, "error": "price_not_configured", "item_id": iid}

        cfg_path = os.path.join(_BASE, "data", "mn2_config.json")
        coins_per_mn2 = 100.0
        if os.path.isfile(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    coins_per_mn2 = float(json.load(f).get("coins_per_mn2") or 100)
            except Exception:
                pass
        price_mn2 = price_coins / coins_per_mn2
        points = unified_points_db.get_all_points(uid).get("points", {})
        mn2_balance = float(points.get("mn2_balance") or 0)
        if mn2_balance < price_mn2:
            return {
                "success": False,
                "error": "insufficient_mn2",
                "price_mn2": price_mn2,
                "mn2_balance": mn2_balance,
            }
        debit = unified_points_db.add_points(
            user_id=uid,
            point_type="mn2_balance",
            amount=-price_mn2,
            source="block_trophy_claim",
            metadata={"item_id": iid, "block_height": h, "price_coins": price_coins},
        )
        if not debit.get("success", True):
            return {"success": False, "error": "mn2_debit_failed"}
    elif method == "paypal":
        return {
            "success": False,
            "error": "use_paypal_checkout",
            "item_id": iid,
            "shop_url": catalog.get("shop_url"),
        }
    else:
        return {"success": False, "error": "unsupported_payment_method", "method": method}

    from backend.services.trophy_fulfillment_service import grant_platform_edition

    grant = grant_platform_edition(
        uid,
        iid,
        catalog["name"],
        acquired_via="block_mint",
        price_type=method,
        extra={"block_height": h},
    )
    if not grant.get("success"):
        return grant
    edition_no = grant.get("edition_no")
    edition_key = grant.get("edition_key")
    proof_hash = grant.get("proof_hash")
    edition = grant.get("edition") or {}

    row["claimed_by"] = uid
    row["claimed_at"] = _iso()
    row["edition_no"] = edition_no
    row["edition_key"] = edition_key
    drops[key] = row
    doc["updated_at"] = _iso()
    _write_json(_MANIFEST_PATH, doc)

    try:
        from backend.services.mn2_ledger import append_entry

        append_entry(
            uid,
            "block_trophy_proof",
            float(catalog.get("effective_price_usd") or catalog.get("base_price_usd") or 0),
            txid=f"block:{h}:{uid}",
            metadata={
                "item_id": iid,
                "block_height": h,
                "edition_no": edition_no,
                "edition_key": edition_key,
                "proof_hash": proof_hash,
                "payment_method": method,
            },
        )
    except Exception:
        pass

    return {
        "success": True,
        "height": h,
        "item_id": iid,
        "edition_no": edition_no,
        "edition_key": edition_key,
        "edition": edition,
        "explorer_url": catalog.get("explorer_url"),
    }
