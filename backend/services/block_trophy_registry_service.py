"""Per-block trophy registry — license numbers + trading metadata (one trophy per block)."""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

LICENSE_VERSION = "block-trophy-license-v1"


def license_number(block_height: int) -> str:
    """Unique platform license for the one-of-one block collectible."""
    h = int(block_height)
    tag = hashlib.sha256(f"{LICENSE_VERSION}|{h}".encode("utf-8")).hexdigest()[:4].upper()
    return f"MN2-BLK-LIC-{h:09d}-{tag}"


def _attributes_from_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "power": stats.get("power"),
        "defense": stats.get("defense"),
        "speed": stats.get("speed"),
        "luck": stats.get("luck"),
        "smile": stats.get("smile"),
        "combat_rating": stats.get("combat_rating"),
        "rarity": stats.get("rarity"),
        "mood": stats.get("mood"),
    }


def build_trading_profile(
    block_height: int,
    *,
    stats: Dict[str, Any],
    claimed: bool = False,
    claimed_by: Optional[str] = None,
    edition_key: Optional[str] = None,
    edition_no: Optional[int] = None,
    proof_hash: Optional[str] = None,
    anchor_status: Optional[str] = None,
    floor_price_usd: Optional[float] = None,
) -> Dict[str, Any]:
    """Trading desk fields for a unique per-block trophy edition."""
    h = int(block_height)
    lic = license_number(h)
    serial = stats.get("serial_number") or f"BLK-{h:07d}-E{(edition_no or 1):04d}"
    item_id = f"block-{h}"

    return {
        "license_number": lic,
        "serial_number": serial,
        "collectible_id": item_id,
        "block_height": h,
        "uniqueness": "one_per_block",
        "supply": 1,
        "max_supply": 1,
        "edition_cap": 1,
        "transferable": True,
        "auction_listable": True,
        "peer_transfer": True,
        "exchange_tradable": True,
        "royalty_bps": 250,
        "platform_fee_bps": 100,
        "listing_status": "claimed" if claimed else "available",
        "owner_id": claimed_by if claimed else None,
        "edition_key": edition_key,
        "edition_no": edition_no,
        "proof_hash": proof_hash,
        "anchor_status": anchor_status,
        "floor_price_usd": floor_price_usd,
        "attributes": _attributes_from_stats(stats),
        "trading_urls": {
            "shop": f"/shop?tab=block-gallery&highlight={item_id}",
            "auction": "/shop?tab=auction",
            "wallet": "/wallets?tab=trophies",
            "exchange": "/exchange#cex-trophy-section",
            "explorer": f"/explorer?height={h}",
        },
        "provenance_source": "block_mint",
        "on_chain_mint": False,
        "platform_ledger": True,
    }


def manifest_fields_for_block(block_height: int) -> Dict[str, Any]:
    """Registry payload stored on each new manifest drop row."""
    from backend.services.block_trophy_battle_service import generate_battle_stats

    h = int(block_height)
    preview_key = f"TRO-block-{h}-preview"
    stats = generate_battle_stats(h, preview_key, edition_no=1)
    try:
        from backend.services.block_mint_service import get_config

        cfg = get_config()
        floor = float(cfg.get("floor_price_usd") or 0.99)
    except Exception:
        floor = 0.99

    trading = build_trading_profile(h, stats=stats, floor_price_usd=floor)
    return {
        "license_number": trading["license_number"],
        "serial_number": trading["serial_number"],
        "battle_stats": stats,
        "trading_profile": trading,
    }


def enrich_catalog_row(row: Dict[str, Any], manifest_row: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Attach license + trading profile to a shop catalog row."""
    out = dict(row)
    h = int(out.get("block_height") or 0)
    if not h and str(out.get("id", "")).startswith("block-"):
        try:
            h = int(str(out["id"])[6:])
        except (TypeError, ValueError):
            h = 0
    if not h:
        return out

    manifest_row = manifest_row or {}
    stats = manifest_row.get("battle_stats") or out.get("battle_stats") or {}
    if not stats.get("power"):
        from backend.services.block_trophy_battle_service import generate_battle_stats

        stats = generate_battle_stats(h, f"TRO-block-{h}-preview", edition_no=1)

    claimed = bool(manifest_row.get("claimed_by") or out.get("claimed"))
    trading = manifest_row.get("trading_profile") or build_trading_profile(
        h,
        stats=stats,
        claimed=claimed,
        claimed_by=manifest_row.get("claimed_by") or out.get("claimed_by"),
        edition_key=manifest_row.get("edition_key") or out.get("edition_key"),
        edition_no=manifest_row.get("edition_no") or out.get("edition_no"),
        proof_hash=manifest_row.get("proof_hash"),
        floor_price_usd=out.get("floor_price_usd") or out.get("base_price_usd"),
    )

    out["license_number"] = manifest_row.get("license_number") or trading.get("license_number")
    out["serial_number"] = out.get("serial_number") or trading.get("serial_number")
    out["battle_stats"] = stats
    out["trading_profile"] = trading
    out["one_per_block"] = True
    out["floor_price_usd"] = trading.get("floor_price_usd")
    return out
