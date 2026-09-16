#!/usr/bin/env python3
"""Generate data/camgirls_catalog.json with 25 wallet camgirl profiles (SFW placeholders)."""
import json
import os

AVATARS = [
    "/static/camgirls/avatar-demo.svg",
    "/static/camgirls/avatar-iris.svg",
    "/static/camgirls/avatar-sage.svg",
    "/static/camgirls/avatar-ember.svg",
    "/static/camgirls/preview-demo.svg",
]

PROFILES = [
    ("cg_wallet_nova", "Nova Star", "Cosmic energy and playful banter", "star", 15),
    ("cg_wallet_luna", "Luna Eclipse", "Midnight vibes and moonlit chats", "moon", 12),
    ("cg_wallet_sage", "Sage Willow", "Calm wisdom and mindful studio gifts", "zen", 10),
    ("cg_wallet_ember", "Ember Blaze", "High energy dances and hype chat", "fire", 18),
    ("cg_wallet_iris", "Iris Prism", "Colorful stage and music cues", "prism", 14),
    ("cg_wallet_aurora", "Aurora Borealis", "Northern lights ambiance streams", "aurora", 16),
    ("cg_wallet_coral", "Coral Reef", "Tropical chill and island beats", "tropical", 11),
    ("cg_wallet_velvet", "Velvet Rose", "Elegant conversation and soft jazz", "elegant", 13),
    ("cg_wallet_pixel", "Pixel Pixie", "Retro gaming vibes and pixel art", "retro", 9),
    ("cg_wallet_storm", "Storm Chase", "Weather watch and dramatic reads", "storm", 17),
    ("cg_wallet_honey", "Honey Glaze", "Sweet tips and baking streams", "sweet", 10),
    ("cg_wallet_onyx", "Onyx Night", "Late-night lo-fi and deep talks", "night", 15),
    ("cg_wallet_jade", "Jade Lotus", "Wellness tips and stretch breaks", "wellness", 12),
    ("cg_wallet_ruby", "Ruby Spark", "Dance challenges and party mode", "party", 19),
    ("cg_wallet_frost", "Frost Byte", "Cool tech reviews and coding chat", "tech", 14),
    ("cg_wallet_silk", "Silk Whisper", "ASMR-friendly soft voice sessions", "soft", 11),
    ("cg_wallet_blaze", "Blaze Runner", "Fitness goals and energy boosts", "fitness", 16),
    ("cg_wallet_mist", "Mist Serene", "Meditation timers and calm goals", "calm", 10),
    ("cg_wallet_copper", "Copper Coin", "Crypto tips and MN2 explainers", "crypto", 13),
    ("cg_wallet_pearl", "Pearl Harbor", "Ocean facts and sailor stories", "ocean", 12),
    ("cg_wallet_violet", "Violet Haze", "Indie music picks and vinyl spins", "music", 15),
    ("cg_wallet_terra", "Terra Green", "Eco chats and garden updates", "eco", 11),
    ("cg_wallet_comet", "Comet Tail", "Speed runs and quick challenges", "speed", 17),
    ("cg_wallet_dusk", "Dusk Fall", "Sunset sessions and poetry corner", "poetry", 14),
    ("cg_wallet_apex", "Apex Summit", "Peak performance coaching streams", "coach", 20),
]

TIERS = ("starter", "rising", "star", "elite")


def main() -> None:
    performers = []
    for i, (pid, name, tagline, vibe, price) in enumerate(PROFILES):
        performers.append({
            "id": pid,
            "name": name,
            "tagline": tagline,
            "bio": f"{tagline}. SFW wallet card — full studio experience on the camgirls module.",
            "tier": TIERS[i % len(TIERS)],
            "price_mn2": price,
            "tip_min_mn2": max(5, price // 2),
            "wallet_user_id": f"camgirl_{pid}",
            "avatar_url": AVATARS[i % len(AVATARS)],
            "online": i % 3 != 2,
            "vibe": vibe,
            "wallet_sfw": True,
            "studio_path": f"/camgirls?performer={pid}",
        })

    doc = {
        "version": 1,
        "generated_at": "2026-09-16",
        "total": len(performers),
        "performers": performers,
    }
    out = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "camgirls_catalog.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    print(f"Wrote {len(performers)} performers to {out}")


if __name__ == "__main__":
    main()
