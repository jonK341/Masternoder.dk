"""Discord fanout for trophy grant events (staking wins, block claims)."""
from __future__ import annotations

from typing import Any, Dict, Optional


def _embed_for_trophy_grant(grant: Dict[str, Any]) -> Dict[str, Any]:
    height = grant.get("block_height")
    lic = grant.get("license_number") or ""
    ekey = grant.get("edition_key") or ""
    gif = grant.get("gif_url") or grant.get("edition_gif_url")
    combat = (grant.get("battle_stats") or {}).get("combat_rating")
    acquired = grant.get("acquired_via") or "grant"
    title = "Staking trophy won" if acquired == "staking_winner" else "Block trophy claimed"
    desc = f"Block **#{height}**"
    if lic:
        desc += f" · `{lic}`"
    if combat is not None:
        desc += f" · CR **{combat}**"
    if ekey:
        desc += f"\n`{ekey}`"

    embed: Dict[str, Any] = {
        "title": title,
        "description": desc,
        "color": 0xFBBF24,
        "fields": [
            {"name": "Acquired via", "value": acquired, "inline": True},
        ],
    }
    if gif:
        embed["image"] = {"url": gif if str(gif).startswith("http") else str(gif)}
    return embed


def post_trophy_sale(sale: Dict[str, Any], *, channel: str = "market") -> Dict[str, Any]:
    try:
        from backend.services.discord_service import post_message

        ekey = sale.get("edition_key") or ""
        payload = {
            "embeds": [{
                "title": "Trophy sold on auction",
                "description": (
                    f"`{ekey}`\n"
                    f"Seller `{sale.get('seller_id')}` → Buyer `{sale.get('buyer_id')}`\n"
                    f"Price: **{sale.get('price_coins', '—')}** coins"
                ),
                "color": 0x6EB5FF,
            }],
        }
        if sale.get("gif_url"):
            payload["embeds"][0]["image"] = {"url": str(sale["gif_url"])}
        return post_message(channel, payload, message_id=f"trophy-sale:{ekey}:{sale.get('buyer_id')}")
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def post_trophy_share(edition_key: str, user_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from backend.services.discord_service import post_message

        payload = {
            "content": f"`{user_id}` shared a trophy edition",
            "embeds": [{
                "title": metadata.get("name") or edition_key,
                "description": metadata.get("description") or edition_key,
                "color": 0xFBBF24,
            }],
        }
        if metadata.get("image"):
            payload["embeds"][0]["image"] = {"url": str(metadata["image"])}
        return post_message("market", payload, message_id=f"trophy-share:{edition_key}:{user_id}")
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def post_trophy_grant(grant: Dict[str, Any], *, channel: str = "market") -> Dict[str, Any]:
    """Post trophy grant embed to Discord (best-effort)."""
    try:
        from backend.services.discord_service import post_message

        embed = _embed_for_trophy_grant(grant)
        user_id = (grant.get("user_id") or "").strip()
        payload = {"embeds": [embed]}
        if user_id:
            payload["content"] = f"Trophy drop for `{user_id}`"
        return post_message(channel, payload, message_id=f"trophy-grant:{grant.get('edition_key')}")
    except Exception as exc:
        return {"success": False, "error": str(exc)}
