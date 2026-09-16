"""Discord announcement for block 1,000,000 genesis trophy collection launch."""
from __future__ import annotations

from typing import Any, Dict

MILESTONE_BLOCK = 1_000_000
GENESIS_BLOCK = 1
MESSAGE_ID = "block-million-trophy-genesis-v1"


def build_block_million_announcement_payload() -> Dict[str, Any]:
    """Rich embed for #announcements — block 1M trophy genesis program."""
    return {
        "content": (
            "🏆 **Block 1,000,000 milestone** — the Block Trophy collection (platform NFTs) "
            "is now rolling out **from block #1** through the chain."
        ),
        "embeds": [
            {
                "title": "Genesis → tip: one AI trophy per MN2 block",
                "description": (
                    "From block **1,000,000** onward, MasterNoder creates a **unique Block Trophy** "
                    "for every MN2 block — **starting at block #1** (genesis) and continuing to chain tip.\n\n"
                    "Each edition ships with:\n"
                    "• **Unique AI smiley GIF** (per edition, mood + rarity baked in)\n"
                    "• **License number** + battle stats + trading profile\n"
                    "• **Wallet v2** gallery, 4D monitor, auction & peer transfer\n"
                    "• **Staking interval winners** can earn unclaimed block trophies\n\n"
                    "Platform-ledger collectibles today — optional L2 anchor; on-chain mint deferred."
                ),
                "color": 0xFBBF24,
                "fields": [
                    {
                        "name": "Milestone",
                        "value": f"Block **{MILESTONE_BLOCK:,}** triggers genesis backfill",
                        "inline": True,
                    },
                    {
                        "name": "Genesis",
                        "value": f"Block **#{GENESIS_BLOCK}** — first trophy in the series",
                        "inline": True,
                    },
                    {
                        "name": "Supply rule",
                        "value": "Exactly **1 trophy per block height**",
                        "inline": True,
                    },
                    {
                        "name": "Where to go",
                        "value": "Block Gallery: `/shop?tab=block-gallery`\nWallet: `/wallets?tab=trophies` · Staking: `/wallets?tab=staking`",
                        "inline": False,
                    },
                ],
                "footer": {
                    "text": "Not financial advice · Platform trophies are not on-chain mint unless anchored · 18+",
                },
            }
        ],
    }


def post_block_million_announcement(*, channel: str = "announcements", force: bool = False) -> Dict[str, Any]:
    """Post genesis trophy announcement to Discord (idempotent unless force=True)."""
    from backend.services.discord_service import post_message

    mid = MESSAGE_ID if not force else f"{MESSAGE_ID}:{__import__('time').time():.0f}"
    payload = build_block_million_announcement_payload()
    result = post_message(channel, payload, message_id=mid)
    if result.get("success"):
        try:
            from backend.services.platform_news_publish import publish

            publish(
                item_id="news-block-million-trophy-genesis-20260916",
                title="Block 1,000,000 — trophies from genesis block #1",
                summary=(
                    "From block 1,000,000 the platform issues one unique AI Block Trophy per MN2 block, "
                    "backfilled from block #1 through chain tip. Licensed, battle-ready, wallet v2 + Block Gallery."
                ),
                channel="platform",
                href="/shop?tab=block-gallery",
                featured=True,
            )
        except Exception:
            pass
    return {"success": result.get("success"), "discord": result, "message_id": mid}
