"""Shop digital goods — camgirls performer brand / resell packs."""
from __future__ import annotations

import os
from typing import Any, Dict, List

from backend.services.camgirls_media_service import all_performer_media_meta, get_performer_media_meta

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PACK_DIR = os.path.join(_ROOT, "content", "digital_goods", "camgirls")


def _pack_artifact(slug: str) -> str:
    return f"content/digital_goods/camgirls/{slug}-brand-pack.zip"


def list_resell_digital_goods() -> List[Dict[str, Any]]:
    """Digital-good rows merged into monetization catalog."""
    goods: List[Dict[str, Any]] = []
    for performer_id, meta in all_performer_media_meta().items():
        slug = str(meta.get("slug") or "")
        if not slug:
            continue
        name = slug.replace("-", " ").title()
        goods.append(
            {
                "id": f"dg-camgirls-brand-{slug}",
                "line": "B",
                "name": f"Camgirls brand pack — {name}",
                "description": (
                    "Affiliate/resell kit: icon, logo, 3 gallery stills, preview loop, "
                    "resell manifest JSON. Disclosure required on partner surfaces."
                ),
                "payment_rails": ["paypal", "mn2", "credits"],
                "price_usd": 7.99,
                "price_coins": 799,
                "delivery": "download",
                "artifact_path": _pack_artifact(slug),
                "download_filename": f"masternoder-camgirls-{slug}-brand-pack.zip",
                "license": "Affiliate resale on approved MasterNoder partner surfaces with disclosure.",
                "tags_extra": ["camgirls", "brand_pack", performer_id],
            }
        )
    goods.append(
        {
            "id": "dg-camgirls-brand-all-15",
            "line": "B",
            "name": "Camgirls brand mega pack (all 15 hosts)",
            "description": "All performer brand ZIPs in one download — icons, logos, galleries, manifests.",
            "payment_rails": ["paypal", "mn2", "credits"],
            "price_usd": 49.99,
            "price_coins": 4999,
            "delivery": "download",
            "artifact_path": "content/digital_goods/camgirls/all-performers-brand-pack.zip",
            "download_filename": "masternoder-camgirls-all-15-brand-pack.zip",
            "license": "Affiliate resale on approved MasterNoder partner surfaces with disclosure.",
            "tags_extra": ["camgirls", "brand_pack", "bundle"],
        }
    )
    return goods


def shop_item_id_for_performer(performer_id: str) -> str | None:
    meta = get_performer_media_meta(performer_id)
    slug = meta.get("slug")
    if not slug:
        return None
    return f"dg-camgirls-brand-{slug}"


def pack_zip_exists(slug: str) -> bool:
    path = os.path.join(_PACK_DIR, f"{slug}-brand-pack.zip")
    return os.path.isfile(path) and os.path.getsize(path) > 50
