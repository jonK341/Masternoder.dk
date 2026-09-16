#!/usr/bin/env python3
"""Generate data/camgirls_upgrades_catalog.json with WR-CAM-UPG-001..250."""
import json
import os

CATEGORIES = [
    ("studio", 30, [
        "Ring light boost", "Backdrop swap", "Green screen edge", "4K stream tier",
        "Dual camera angle", "Audio noise gate", "Mic warmth filter", "Chat overlay skin",
        "Tip goal banner", "Viewer counter chip", "Schedule slot +1", "Private room key",
        "Lobby spotlight", "Thumbnail frame", "Bio card glow", "Tagline editor",
        "Avatar frame rare", "Status ping online", "Away message slot", "Welcome auto-reply",
        "Moderator slot", "Slow mode toggle", "Emote pack unlock", "Sticker wall tier",
        "Poll widget", "Q&A queue", "Highlight reel slot", "Clip bookmark",
        "Session timer extend", "Studio nameplate",
    ]),
    ("chat", 30, [
        "Whisper priority", "Mention highlight", "Chat color tier", "Badge flair",
        "Pinned note slot", "Reaction pack", "GIF reply unlock", "Voice note stub",
        "Translate assist", "Spam shield +1", "Keyword alert", "Fan nickname list",
        "VIP chat lane", "Mod highlight", "Slow chat bypass", "Emoji burst",
        "Thread reply", "Quote reply", "Chat history export", "Mute list expand",
        "Block list expand", "Auto-thank tip", "Greeting macro", "Farewell macro",
        "Raid shout template", "Collab invite slot", "Co-host badge", "Chat raffle stub",
        "Loyalty streak chip", "Chat XP multiplier",
    ]),
    ("gifts", 30, [
        "Rose animation", "Heart shower", "Star burst", "Diamond tier gift",
        "Crown moment", "Fireworks overlay", "Confetti burst", "Neon sign gift",
        "Moonbeam gift", "Sunrise gift", "Galaxy gift", "Crystal gift",
        "Tip sound sting", "Gift combo x2", "Gift combo x3", "Milestone fanfare",
        "Leaderboard gift", "Anonymous gift mask", "Gift message expand", "Gift schedule",
        "Wishlist slot", "Goal stretch bonus", "Tip train starter", "Tip train x5",
        "Rain gift mode", "Community pot", "Sponsor slot", "Merch shoutout",
        "Charity tie-in badge", "Gift history pin",
    ]),
    ("lighting", 25, [
        "Warm key light", "Cool fill light", "Rim light accent", "Color gel pack",
        "Sunset preset", "Midnight preset", "Neon preset", "Softbox diffuse",
        "Spotlight narrow", "Bokeh background", "Shadow soften", "Brightness auto",
        "Contrast curve", "Skin tone balance", "HDR stream hint", "Flicker reduce",
        "Stage sweep", "Pulse beat sync", "Disco ball stub", "Candle preset",
        "Aurora preset", "Studio dimmer", "Light map save", "Scene recall A",
        "Scene recall B",
    ]),
    ("wardrobe", 25, [
        "Casual outfit slot", "Formal outfit slot", "Cosplay frame", "Seasonal border",
        "Accessory pack", "Hair variant", "Color palette swap", "Logo watermark",
        "Brand overlay", "Outfit preview", "Wardrobe favorites", "Quick change macro",
        "Theme night tag", "Holiday frame", "Retro filter frame", "Minimalist card",
        "Glamour card style", "Sporty badge", "Art deco frame", "Pixel frame",
        "Hologram frame stub", "Collectible border", "Fan club frame", "Milestone outfit",
        "Signature look save",
    ]),
    ("rewards", 25, [
        "Daily login bonus", "Chat streak +1", "Tip back micro", "Viewer loyalty chip",
        "Rating star bonus", "Active hour badge", "Weekend multiplier", "Referral slot",
        "Collab bonus", "Raid bonus", "Goal smash bonus", "New fan welcome",
        "Returning fan ping", "Top fan spotlight", "Leaderboard peek", "MN2 micro drip",
        "Points sync wallet", "Achievement toast", "Level-up studio", "Quest hook chat",
        "Discord cross-post", "News mention slot", "Podcast shout slot", "Wallet tab pin",
        "Upgrade bundle hint",
    ]),
    ("network", 25, [
        "CDN edge boost", "Latency badge", "Reconnect grace", "Mobile layout opt",
        "Low-bandwidth mode", "Preview quality step", "Thumbnail CDN", "Avatar CDN",
        "Presence heartbeat", "Online roster slot", "Network chat bridge", "Wallet deep link",
        "Exchange tip rail", "Shop gift rail", "Casino cross-promo", "Podcast embed",
        "News ticker sync", "Encoder clip share", "Peer discovery stub", "Geo hint off",
        "Privacy blur toggle", "Session token extend", "Rate limit cushion", "Failover banner",
        "Health check chip",
    ]),
    ("premium", 60, [
        "VIP lounge pass", "Private show token", "Extended session", "HD priority lane",
        "4K priority lane", "No-ad interstitial", "Custom room theme", "Branded overlay",
        "Analytics peek", "Revenue snapshot", "Fan CRM export", "Schedule assistant",
        "Auto-clip highlight", "AI caption assist", "Multi-language room", "Co-stream slot",
        "Recording stub", "Archive slot", "Merch shelf", "PayPal tip rail",
        "MN2 hold explain", "Wallet upgrade sync", "Trophy gift link", "Battle promo tile",
        "Staking shout", "Masternode flair", "Explorer link card", "Generator teaser",
        "Lab collab invite", "Compendium lore pin", "Profit daemon nod", "Aggregator badge",
        "Agent co-host stub", "Social hub cross", "Gallery pin", "Debugger opt-out",
        "Owner spotlight", "Season pass tier 1", "Season pass tier 2", "Founders frame",
        "Platinum border", "Diamond lounge", "Elite tip rail", "Concierge chat",
        "Priority support", "Custom emote upload", "Brand partnership slot", "Sponsor overlay",
        "Revenue share peek", "Tax export hook", "Wallet tab badge", "Cross-promo carousel",
        "Holiday mega pack", "Anniversary frame", "Collab studio key", "Network spotlight",
        "Peer invite bonus", "Raid defense shield", "Goal insurance stub", "Fan club tier +1",
        "Merch drop alert", "Live queue jump", "Encoder shoutout", "News feature slot",
    ]),
]

TIERS = ("common", "rare", "epic")
UNLOCK_TYPES = ("default", "level", "mn2_spent", "trophy_count", "upgrade_count")


def _unlock(idx: int, category: str) -> dict:
    if idx <= 8:
        return {"type": "default", "value": 0, "label": "Available at wallet launch"}
    if idx <= 20:
        need = 2 + (idx % 5)
        return {"type": "level", "value": need, "label": f"Wallet level {need}"}
    if idx <= 35:
        need = 50 + (idx * 3) % 200
        return {"type": "mn2_spent", "value": need, "label": f"Spend {need} MN2 in shop"}
    if category in ("premium", "rewards") and idx % 7 == 0:
        need = 1 + (idx % 3)
        return {"type": "trophy_count", "value": need, "label": f"Own {need} trophy edition(s)"}
    need = 5 + (idx % 15)
    return {"type": "upgrade_count", "value": need, "label": f"Unlock {need} camgirl upgrades"}


def main() -> None:
    upgrades = []
    n = 0
    for category, count, names in CATEGORIES:
        for i, name in enumerate(names[:count]):
            n += 1
            tier = TIERS[i % len(TIERS)]
            upgrades.append({
                "id": f"WR-CAM-UPG-{n:03d}",
                "name": name,
                "effect": f"Studio upgrade: {name} — enhances camgirl wallet experience.",
                "category": category,
                "tier": tier,
                "unlock": _unlock(n, category),
            })

    doc = {
        "version": 1,
        "generated_at": "2026-09-16",
        "total": len(upgrades),
        "categories": [c[0] for c in CATEGORIES],
        "upgrades": upgrades,
    }
    out = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "camgirls_upgrades_catalog.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    print(f"Wrote {len(upgrades)} upgrades to {out}")


if __name__ == "__main__":
    main()
