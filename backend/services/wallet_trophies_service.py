"""Wallet hub trophy collection — merge inventory + catalog + media (plan 001 W-U3)."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MEDIA_PATH = os.path.join(_BASE, "data", "shop_item_media.json")


def _load_media() -> Dict[str, Any]:
    if not os.path.isfile(_MEDIA_PATH):
        return {}
    try:
        with open(_MEDIA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _media_for_item(item_id: str) -> Dict[str, Optional[str]]:
    row = _load_media().get(item_id) or {}
    return {
        "image_url": row.get("image_url") or row.get("poster_url"),
        "gif_url": row.get("gif_url") or row.get("clip_url"),
        "sound_url": row.get("sound_url"),
    }


def _registry_anchor_fields(edition_key: str) -> Dict[str, Any]:
    """Merge anchor registry row when edition file lacks txid (plan 003 A-U4)."""
    ekey = (edition_key or "").strip()
    if not ekey:
        return {}
    try:
        from backend.services.trophy_anchor_service import get_anchor_status

        status = get_anchor_status(ekey)
        if not status.get("success") or status.get("anchor_status") == "none":
            return {}
        return {
            "anchor_status": status.get("anchor_status"),
            "anchor_commitment": status.get("anchor_commitment"),
            "anchor_txid": status.get("anchor_txid"),
            "anchor_explorer_url": status.get("anchor_explorer_url"),
        }
    except Exception:
        return {}


def _expand_editions(
    inv_row: Dict[str, Any],
    catalog: Optional[Dict[str, Any]],
    *,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Edition rows from U2 trophy_editions store, else legacy quantity stack."""
    item_id = (inv_row.get("item_id") or "").strip()
    qty = max(0, int(inv_row.get("quantity") or 0))
    if not item_id or qty <= 0:
        return []

    stored: List[Dict[str, Any]] = []
    if user_id:
        try:
            from backend.services.trophy_fulfillment_service import get_trophy_editions

            stored = get_trophy_editions(user_id, item_id)
        except Exception:
            stored = []

    if stored:
        media = _media_for_item(item_id)
        out: List[Dict[str, Any]] = []
        for ed in stored:
            ekey = ed.get("edition_key") or ""
            anchor_extra = _registry_anchor_fields(ekey) if not ed.get("anchor_txid") else {}
            anchor_status = ed.get("anchor_status") or anchor_extra.get("anchor_status")
            out.append(
                {
                    "edition_no": ed.get("edition_no"),
                    "edition_key": ekey,
                    "legacy_stack": False,
                    "item_id": item_id,
                    "item_name": ed.get("item_name") or inv_row.get("item_name") or (catalog or {}).get("name") or item_id,
                    "serial_key": (catalog or {}).get("serial_key"),
                    "series": (catalog or {}).get("series"),
                    "tags": (catalog or {}).get("tags") or [],
                    "on_chain_mint": False,
                    "acquired_at": ed.get("granted_at") or inv_row.get("created_at"),
                    "hold_until": ed.get("hold_until"),
                    "proof_hash": ed.get("proof_hash"),
                    "anchor_status": anchor_status,
                    "anchor_commitment": ed.get("anchor_commitment") or anchor_extra.get("anchor_commitment"),
                    "anchor_txid": ed.get("anchor_txid") or anchor_extra.get("anchor_txid"),
                    "anchor_explorer_url": ed.get("anchor_explorer_url") or anchor_extra.get("anchor_explorer_url"),
                    "serial_number": ed.get("serial_number"),
                    "battle_stats": ed.get("battle_stats"),
                    "block_height": ed.get("block_height"),
                    "platform_trophy": ed.get("platform_trophy") or ed.get("platform_nft"),
                    "acquired_via": ed.get("acquired_via"),
                    "image_url": media.get("image_url"),
                    "gif_url": media.get("gif_url"),
                    "sound_url": media.get("sound_url"),
                    "trade_actions": {
                        "auction_list": "/shop?tab=auction",
                        "peer_transfer": "/api/shop/trophies/transfer",
                        "shop_detail": f"/shop?tab=trophies&highlight={item_id}",
                    },
                }
            )
        return out

    name = inv_row.get("item_name") or (catalog or {}).get("name") or item_id
    media = _media_for_item(item_id)
    editions: List[Dict[str, Any]] = []
    for n in range(1, qty + 1):
        editions.append(
            {
                "edition_no": n,
                "edition_key": f"{item_id}#{n}",
                "legacy_stack": True,
                "item_id": item_id,
                "item_name": name,
                "serial_key": (catalog or {}).get("serial_key"),
                "series": (catalog or {}).get("series"),
                "tags": (catalog or {}).get("tags") or [],
                "on_chain_mint": False,
                "acquired_at": inv_row.get("created_at"),
                "image_url": media.get("image_url"),
                "gif_url": media.get("gif_url"),
                "sound_url": media.get("sound_url"),
                "trade_actions": {
                    "auction_list": "/shop?tab=auction",
                    "peer_transfer": "/api/shop/trophies/transfer",
                    "shop_detail": f"/shop?tab=trophies&highlight={item_id}",
                },
            }
        )
    return editions


def build_wallet_trophies(user_id: str, *, series: Optional[str] = None) -> Dict[str, Any]:
    """Lazy-loaded trophy gallery for wallet Trophies tab."""
    uid = (user_id or "").strip()
    if not uid or uid in ("default_user", "guest"):
        return {
            "success": True,
            "guest": True,
            "user_id": uid,
            "editions": [],
            "owned_items": [],
            "catalog_preview": [],
            "counts": {"total_editions": 0, "top25_owned": 0, "top25_total": 0, "unique_skus": 0},
            "on_chain_mint": False,
            "message": "Create an account to collect platform trophies.",
        }

    from backend.routes.shop_routes import _is_trophy_catalog_item, _list_trophy_items

    catalog_items = _list_trophy_items(series=series)
    catalog_by_id = {str(i.get("id")): i for i in catalog_items if i.get("id")}

    inventory: List[Dict[str, Any]] = []
    try:
        from backend.services.shop_db_service import get_inventory

        inventory = get_inventory(uid) or []
    except Exception:
        inventory = []

    trophy_inv = [row for row in inventory if _is_trophy_catalog_item({"id": row.get("item_id"), **row})]

    editions: List[Dict[str, Any]] = []
    owned_items: List[Dict[str, Any]] = []
    for row in trophy_inv:
        iid = str(row.get("item_id") or "")
        cat = catalog_by_id.get(iid)
        expanded = _expand_editions(row, cat, user_id=uid)
        editions.extend(expanded)
        owned_items.append(
            {
                "item_id": iid,
                "item_name": row.get("item_name") or (cat or {}).get("name") or iid,
                "quantity": int(row.get("quantity") or 0),
                "editions": expanded,
                "catalog": cat,
            }
        )

    top25_total = sum(1 for i in catalog_items if str(i.get("id", "")).startswith("top25-"))
    top25_owned = sum(
        int(r.get("quantity") or 0)
        for r in trophy_inv
        if str(r.get("item_id", "")).startswith("top25-")
    )

    owned_ids = {str(r.get("item_id")) for r in trophy_inv}
    catalog_preview = [
        {
            "id": i.get("id"),
            "name": i.get("name"),
            "effective_price_usd": i.get("effective_price_usd"),
            "owned": i.get("id") in owned_ids,
            "image_url": _media_for_item(str(i.get("id") or "")).get("image_url"),
            "shop_url": f"/shop?tab=trophies&highlight={i.get('id')}",
        }
        for i in catalog_items
        if not i.get("owned") and i.get("id") not in owned_ids
    ][:12]

    editions.sort(key=lambda e: (e.get("item_id") or "", e.get("edition_no") or 0))

    return {
        "success": True,
        "user_id": uid,
        "series": series,
        "on_chain_mint": False,
        "platform_ledger": True,
        "editions": editions,
        "owned_items": owned_items,
        "catalog_preview": catalog_preview,
        "counts": {
            "total_editions": len(editions),
            "top25_owned": top25_owned,
            "top25_total": top25_total,
            "unique_skus": len(owned_items),
            "catalog_skus": len(catalog_items),
        },
        "shop_trophies_url": "/shop?tab=trophies",
        "auction_url": "/shop?tab=auction",
    }
