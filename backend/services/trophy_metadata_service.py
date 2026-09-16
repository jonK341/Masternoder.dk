"""Open-style metadata JSON per trophy edition."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def find_edition_globally(edition_key: str) -> Dict[str, Any]:
    """Locate edition row and current owner by edition_key."""
    ekey = (edition_key or "").strip()
    if not ekey:
        return {"success": False, "error": "missing_edition_key"}

    try:
        from backend.services.trophy_fulfillment_service import find_edition_by_key

        found = find_edition_by_key(ekey)
        if found.get("success"):
            return found
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    return {"success": False, "error": "edition_not_found"}


def build_metadata(edition_key: str) -> Dict[str, Any]:
    found = find_edition_globally(edition_key)
    if not found.get("success"):
        return found

    edition = found.get("edition") or {}
    owner = found.get("user_id") or ""
    try:
        from backend.services.block_trophy_media_service import ensure_lazy_edition_media

        edition = ensure_lazy_edition_media({**edition, "user_id": owner}, edition_key)
    except Exception:
        pass
    iid = edition.get("item_id") or ""
    stats = edition.get("battle_stats") or {}
    trading = edition.get("trading_profile") or {}

    attributes: List[Dict[str, Any]] = []
    if edition.get("block_height"):
        attributes.append({"trait_type": "Block", "value": int(edition["block_height"])})
    for key in ("rarity", "mood", "serial_number"):
        if stats.get(key):
            attributes.append({"trait_type": key.replace("_", " ").title(), "value": stats[key]})
    if edition.get("license_number"):
        attributes.append({"trait_type": "License", "value": edition["license_number"]})
    if edition.get("acquired_via"):
        attributes.append({"trait_type": "Acquired via", "value": edition["acquired_via"]})

    try:
        from backend.services.trophy_sets_service import edition_set_badges

        for badge in edition_set_badges(edition):
            attributes.append({"trait_type": "Set", "value": badge})
    except Exception:
        pass

    image = edition.get("gif_url") or edition.get("edition_gif_url") or edition.get("image_url")
    name = edition.get("item_name") or iid or edition_key

    meta = {
        "name": name,
        "description": edition.get("description") or f"MasterNoder Block Trophy edition {edition.get('edition_no')}",
        "image": image,
        "animation_url": edition.get("gif_url") or edition.get("edition_gif_url"),
        "external_url": f"/trophy/proof?edition_key={edition_key}",
        "edition_key": edition_key,
        "edition_no": edition.get("edition_no"),
        "item_id": iid,
        "owner_id": owner,
        "on_chain_mint": False,
        "platform_trophy": True,
        "attributes": attributes,
        "royalty_bps": trading.get("royalty_bps"),
        "proof_hash": edition.get("proof_hash"),
    }

    try:
        from backend.services.trophy_anchor_service import get_anchor_status

        anchor = get_anchor_status(edition_key)
        if anchor.get("success") and anchor.get("anchor_status") != "none":
            meta["anchor"] = {
                "status": anchor.get("anchor_status"),
                "commitment": anchor.get("anchor_commitment"),
                "txid": anchor.get("anchor_txid"),
                "explorer_url": anchor.get("anchor_explorer_url"),
            }
    except Exception:
        pass

    return {"success": True, "metadata": meta, "edition": edition, "owner_id": owner}
