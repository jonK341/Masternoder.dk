"""4D Trophy Monitor BFF — network strip + owned trophy GIFs (plan 002 WR-G1)."""
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


def build_4d_trophy_monitor(user_id: str) -> Dict[str, Any]:
    """Holodeck payload: network KPIs + animated trophy cards + optional block teaser."""
    uid = (user_id or "").strip()
    out: Dict[str, Any] = {
        "success": True,
        "user_id": uid,
        "guest": not uid or uid in ("default_user", "guest"),
        "network": {},
        "trophies": [],
        "block_teaser": None,
        "sound_enabled_default": False,
        "on_chain_mint": False,
    }

    try:
        from backend.services.wallet_v2_service import _network_snapshot

        out["network"] = _network_snapshot()
    except Exception:
        out["network"] = {"block_height": None}

    media = _load_media()
    if not out["guest"]:
        try:
            from backend.services.wallet_trophies_service import build_wallet_trophies

            trophies = build_wallet_trophies(uid)
            cards: List[Dict[str, Any]] = []
            for ed in (trophies.get("editions") or [])[:24]:
                iid = str(ed.get("item_id") or "")
                m = media.get(iid) or {}
                cards.append(
                    {
                        "item_id": iid,
                        "item_name": ed.get("item_name") or iid,
                        "edition_no": ed.get("edition_no"),
                        "edition_key": ed.get("edition_key"),
                        "series": ed.get("series"),
                        "gif_url": ed.get("gif_url") or m.get("gif_url") or m.get("clip_url"),
                        "image_url": ed.get("image_url") or m.get("image_url") or m.get("poster_url"),
                        "sound_url": ed.get("sound_url") or m.get("sound_url"),
                        "hold_until": ed.get("hold_until"),
                    }
                )
            out["trophies"] = cards
            out["counts"] = trophies.get("counts") or {}
        except Exception:
            out["trophies"] = []

    try:
        from backend.services.block_mint_service import get_block_drops

        drops = get_block_drops(limit=1)
        latest = (drops.get("drops") or [None])[0]
        if latest:
            out["block_teaser"] = {
                "height": latest.get("block_height"),
                "item_id": latest.get("id"),
                "name": latest.get("name"),
                "gif_url": latest.get("gif_url"),
                "explorer_url": latest.get("explorer_url"),
                "effective_price_usd": latest.get("effective_price_usd"),
                "claimed": latest.get("claimed"),
            }
    except Exception:
        pass

    return out
