#!/usr/bin/env python3
"""Generate data/camgirls_ai_features_catalog.json with CAM-AI-001..100 unified bundles."""
import json
import os

CATEGORIES = [
    ("greetings", [
        "Wave hello", "Morning sparkle", "Night owl greet", "Raid welcome",
        "Returning fan hug", "New viewer bow", "VIP entrance", "Cosmic salute",
        "Soft smile loop", "Studio door chime",
    ]),
    ("reactions", [
        "Heart eyes pop", "LOL bounce", "Mind blown shimmer", "Clap burst",
        "Shy blush", "Surprise gasp", "Thumbs up glow", "Facepalm fade",
        "Cheer horn", "Slow nod approve",
    ]),
    ("dances", [
        "Shuffle step", "Spin twirl", "Hip sway loop", "Robot groove",
        "Ballet curtsey", "Disco pulse", "Wave arms sync", "Jump cut beat",
        "Freeze pose", "Victory shimmy",
    ]),
    ("games", [
        "Dice roll flair", "Wheel spin cue", "Trivia buzz", "Rock paper flash",
        "Number guess pop", "Truth dare card", "Bingo dab", "Raffle drum",
        "Leaderboard flash", "Mini quest ping",
    ]),
    ("tips", [
        "Rose shower", "Coin rain", "Diamond sparkle", "Fireworks tip",
        "Heart cascade", "Star trail", "Crown moment", "Neon thank-you",
        "Confetti burst", "Goal meter fill",
    ]),
    ("vip_moments", [
        "Velvet curtain", "Gold spotlight", "Private wink", "Champagne fizz",
        "Platinum frame", "Concierge bow", "Lounge shimmer", "Elite badge glow",
        "Red carpet roll", "Signature thank-you",
    ]),
    ("network_events", [
        "Block found cheer", "Masternode pulse", "Pool sync wave", "Peer join ping",
        "Hash rate shimmer", "Wallet link toast", "Exchange tick", "Chat bridge glow",
        "CDN edge flash", "Network health chip",
    ]),
    ("trophy_tie_ins", [
        "Trophy lift", "Edition sparkle", "Mint fanfare", "Collector bow",
        "Rare shine", "Shop gift link", "Battle trophy nod", "Staking flair",
        "Compendium page turn", "Hall of fame wave",
    ]),
    ("ai_chat_moods", [
        "Playful banter", "Calm zen tone", "Hype coach", "Mysterious whisper",
        "Supportive nod", "Sassy wink", "Scholarly pause", "Dreamy drift",
        "Bold challenge", "Grateful close",
    ]),
    ("seasonal", [
        "Spring bloom", "Summer sun", "Autumn leaves", "Winter frost",
        "Holiday lights", "New Year burst", "Valentine hearts", "Halloween spooky",
        "Anniversary cake", "Festival lanterns",
    ]),
]

ANIM_TYPES = ("gif", "webm", "css", "sprite")
SOUNDS = [
    "/static/sounds/notification.mp3",
    "/static/sounds/message.mp3",
    "/static/sounds/alert.mp3",
    "/static/sounds/mention.mp3",
]
GIF_ASSETS = [
    "/static/camgirls/preview-demo.svg",
    "/static/camgirls/avatar-demo.svg",
    "/static/camgirls/avatar-iris.svg",
    "/static/camgirls/avatar-sage.svg",
    "/static/camgirls/avatar-ember.svg",
]

PERFORMER_IDS = [
    "cg_wallet_nova", "cg_wallet_luna", "cg_wallet_sage", "cg_wallet_ember",
    "cg_wallet_iris", "cg_wallet_aurora", "cg_wallet_coral", "cg_wallet_velvet",
    "cg_wallet_pixel", "cg_wallet_storm", "cg_wallet_honey", "cg_wallet_onyx",
    "cg_wallet_jade", "cg_wallet_ruby", "cg_wallet_frost", "cg_wallet_silk",
    "cg_wallet_blaze", "cg_wallet_mist", "cg_wallet_copper", "cg_wallet_pearl",
    "cg_wallet_violet", "cg_wallet_terra", "cg_wallet_comet", "cg_wallet_dusk",
    "cg_wallet_apex",
]


def _performer_ids(idx: int) -> list:
    if idx % 5 == 0:
        return ["all"]
    base = PERFORMER_IDS[(idx - 1) % len(PERFORMER_IDS)]
    buddy = PERFORMER_IDS[(idx + 3) % len(PERFORMER_IDS)]
    return [base, buddy]


def _payment(idx: int, category: str) -> dict:
    price = round(2 + (idx % 9) * 1.5 + (idx // 10) * 0.5, 2)
    tip_min = max(2.0, round(price * 0.6, 2))
    unlock = None
    if idx % 7 == 0:
        upg_n = ((idx - 1) % 250) + 1
        unlock = f"WR-CAM-UPG-{upg_n:03d}"
    if category in ("vip_moments", "seasonal") and idx % 3 == 0:
        price = round(price * 1.5, 2)
    return {
        "price_mn2": price,
        "unlock_upgrade_id": unlock,
        "tip_min_mn2": tip_min,
    }


def main() -> None:
    features = []
    n = 0
    for category, names in CATEGORIES:
        for name in names:
            n += 1
            anim_type = ANIM_TYPES[n % len(ANIM_TYPES)]
            asset = GIF_ASSETS[n % len(GIF_ASSETS)]
            if anim_type == "webm":
                asset = f"/static/camgirls/clips/feature-{n:03d}.webm"
            elif anim_type == "css":
                asset = f"camgirl-ai-keyframes-{category}"
            elif anim_type == "sprite":
                asset = f"/static/camgirls/sprites/feature-{n:03d}.png"
            pay = _payment(n, category)
            features.append({
                "id": f"CAM-AI-{n:03d}",
                "name": name,
                "category": category,
                "performer_ids": _performer_ids(n),
                "animation": {
                    "type": anim_type,
                    "asset_url": asset,
                    "duration_ms": 1200 + (n % 8) * 200,
                },
                "payment": pay,
                "sound": {
                    "url": SOUNDS[n % len(SOUNDS)],
                    "volume_default": round(0.35 + (n % 6) * 0.1, 2),
                },
                "description": (
                    f"SFW wallet bundle: {name.lower()} — animation, MN2 payment, and sound cue "
                    f"for camgirl AI studio. Full experience on /camgirls."
                ),
            })

    out = {
        "version": 1,
        "generated_at": "2026-09-16",
        "total": len(features),
        "categories": [c[0] for c in CATEGORIES],
        "features": features,
    }
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "data", "camgirls_ai_features_catalog.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
        f.write("\n")
    print(f"Wrote {len(features)} features to {path}")


if __name__ == "__main__":
    main()
