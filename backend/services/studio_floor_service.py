"""One floor for portraits, the MN2 wallet, NFTs, hosting spots, and Discord audio."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Flagship pairings. Other performers share the comet chip and still show their own picture.
_PERFORMER_NFT = {
    "performer_nova": "nft-discord-wave",
    "performer_luna": "nft-spider-sigil",
    "performer_ember": "nft-casino-die",
    "performer_aurora": "nft-comet-chip",
    "performer_sage": "nft-explorer-compass",
    "performer_venus": "nft-hosting-beacon",
}
_DEFAULT_NFT = "nft-comet-chip"


def _read_json(name: str) -> Dict[str, Any]:
    path = os.path.join(_BASE, "data", name)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _sku_row(sku: str) -> Dict[str, Any]:
    for row in _read_json("nft_catalog.json").get("skus") or []:
        if isinstance(row, dict) and row.get("sku") == sku:
            return row
    return {}


def nft_for_performer(performer_id: str) -> str:
    return _PERFORMER_NFT.get(performer_id or "", _DEFAULT_NFT)


def performer_for_nft(sku: str) -> Optional[str]:
    for performer_id, paired in _PERFORMER_NFT.items():
        if paired == sku:
            return performer_id
    return None


def performer_link(performer_id: str, *, picture_url: str = "") -> Dict[str, Any]:
    """Portrait, paired NFT, and the shared hosting cap for one camgirl card."""
    pid = (performer_id or "").strip()
    sku = nft_for_performer(pid)
    nft = _sku_row(sku)
    picture = picture_url
    if not picture and pid:
        try:
            from backend.services.camgirls_media_service import media_paths_for_performer

            paths = media_paths_for_performer(pid)
            picture = paths.get("picture_url") or paths.get("icon_url") or ""
        except Exception:
            picture = ""
    return {
        "performer_id": pid,
        "picture_url": picture,
        "nft_sku": sku,
        "nft_name": nft.get("name") or sku,
        "nft_avatar_url": nft.get("avatar_url") or "",
        "hosting_spots": _hosting_spots(),
        "wallet": "one_mn2_wallet",
    }


def nft_link(sku: str) -> Dict[str, Any]:
    """Point an NFT edition back at a portrait and the hosting floor."""
    performer_id = performer_for_nft(sku) or ""
    picture = ""
    if performer_id:
        picture = str(performer_link(performer_id).get("picture_url") or "")
    row = _sku_row(sku)
    return {
        "sku": sku,
        "performer_id": performer_id or None,
        "picture_url": picture or row.get("avatar_url") or "",
        "hosting_spots": _hosting_spots(),
        "wallet": "one_mn2_wallet",
    }


def _hosting_spots() -> int:
    from backend.services.mn2_masternode_hosting_service import get_paypal_config

    return int(get_paypal_config().get("max_hosted_nodes") or 500)


def _audio() -> List[Dict[str, Any]]:
    from backend.services.discord_customer_ingest_service import list_discord_audio

    clips = list_discord_audio(limit=3).get("clips") or []
    return [row for row in clips if isinstance(row, dict)]


def _wallet(user_id: str, *, frame: bool) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid:
        return {"framed": True, "wallet_count": 1, "user_id": None, "deposit_address": None}
    if frame:
        from backend.services.mn2_wallet_service import frame_user_mn2_wallet

        framed = frame_user_mn2_wallet(uid)
        if framed.get("success"):
            return framed
    from backend.services.mn2_wallet_service import _coins_per_mn2, _entry_primary, _load_addresses, get_balance

    entry = _load_addresses().get(uid)
    address = _entry_primary(entry)
    balance = get_balance(uid)
    mn2 = float(balance.get("mn2_balance") or 0)
    rate = _coins_per_mn2()
    return {
        "success": True,
        "framed": bool(address),
        "created": False,
        "user_id": uid,
        "deposit_address": address,
        "wallet_count": 1 if address else 0,
        "mn2_balance": mn2,
        "coins_per_mn2": rate,
        "mn2_coins": int(round(mn2 * rate)),
    }


def snapshot(*, user_id: str = "", frame_wallet: bool = False) -> Dict[str, Any]:
    """Live floor: pictures, one wallet, NFT pairings, 500 hosting spots, Discord audio."""
    performers = []
    for row in _read_json("camgirls_performers.json").get("performers") or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        link = performer_link(
            str(row["id"]),
            picture_url=str(row.get("picture_url") or row.get("avatar_url") or ""),
        )
        performers.append({
            "id": row["id"],
            "display_name": row.get("display_name"),
            **link,
        })
    clips = _audio()
    audio_url = str(clips[0].get("url") or "") if clips else ""
    nfts = []
    for row in _read_json("nft_catalog.json").get("skus") or []:
        if not isinstance(row, dict) or not row.get("sku"):
            continue
        link = nft_link(str(row["sku"]))
        nfts.append({
            "sku": row["sku"],
            "name": row.get("name"),
            "avatar_url": row.get("avatar_url"),
            "picture_url": link.get("picture_url"),
            "performer_id": link.get("performer_id"),
        })
    return {
        "success": True,
        "hosting_spots": _hosting_spots(),
        "wallet": _wallet(user_id, frame=frame_wallet),
        "performers": performers,
        "nft_editions": len(nfts),
        "nfts": nfts,
        "audio_clips": clips,
        "audio_url": audio_url,
        "together": (
            "Portraits, one MN2 wallet per user, NFT editions, "
            f"{_hosting_spots()} hosting spots, and Discord audio share this floor."
        ),
    }
