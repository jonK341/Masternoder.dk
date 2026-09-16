"""Public proof page payload for a trophy edition."""
from __future__ import annotations

from typing import Any, Dict


def build_proof_page(edition_key: str) -> Dict[str, Any]:
    from backend.services.trophy_metadata_service import build_metadata
    from backend.services.trophy_provenance_service import get_chain

    meta = build_metadata(edition_key)
    if not meta.get("success"):
        return meta

    edition = meta.get("edition") or {}
    try:
        from backend.services.block_trophy_media_service import ensure_lazy_edition_media

        edition = ensure_lazy_edition_media({**edition, "user_id": meta.get("owner_id")}, edition_key)
    except Exception:
        pass
    provenance = get_chain(edition_key, limit=30)

    return {
        "success": True,
        "edition_key": edition_key,
        "owner_id": meta.get("owner_id"),
        "metadata": meta.get("metadata"),
        "edition": {
            "item_id": edition.get("item_id"),
            "item_name": edition.get("item_name"),
            "edition_no": edition.get("edition_no"),
            "license_number": edition.get("license_number"),
            "serial_number": edition.get("serial_number"),
            "battle_stats": edition.get("battle_stats"),
            "trading_profile": edition.get("trading_profile"),
            "gif_url": edition.get("gif_url") or edition.get("edition_gif_url"),
            "image_url": edition.get("image_url"),
            "acquired_via": edition.get("acquired_via"),
            "granted_at": edition.get("granted_at") or edition.get("acquired_at"),
            "per_edition_media": edition.get("per_edition_media"),
            "revoked": edition.get("revoked"),
        },
        "provenance": provenance.get("events") or [],
        "on_chain_mint": False,
        "proof_url": f"/trophy/proof?edition_key={edition_key}",
        "metadata_url": f"/api/shop/trophies/metadata/{edition_key}",
    }
