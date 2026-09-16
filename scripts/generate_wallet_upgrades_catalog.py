#!/usr/bin/env python3
"""Generate data/wallet_upgrades_catalog.json with WR-UPG-001..250."""
import json
import os

CATEGORIES = [
    ("speed", 30, [
        "Deposit address cache", "Summary prefetch", "Tab chunk preload", "Stale-while-revalidate",
        "Single-flight RPC", "Balance debounce", "Network KPI memo", "Lazy trophy media",
        "Receive tab warm", "Send preview cache", "Activity bucket cache", "Peer list throttle",
        "Explorer block cache", "Staking snapshot TTL", "4D monitor defer", "GIF lazy load",
        "Sound preload gate", "SSE backoff", "History poll pause", "Overview skeleton skip",
        "Bundle split", "Font subset", "CSS critical path", "API parallel cap",
        "LocalStorage mirror", "Retry jitter", "Timeout tiering", "Cold start hint",
        "Service worker hint", "Desktop tray poll",
    ]),
    ("network_visibility", 30, [
        "Block height chip", "Peer count badge", "Mempool gauge", "MN2/USD ticker",
        "Staking APY strip", "Masternode counter", "Sync status lamp", "Difficulty readout",
        "Hash rate display", "Supply snapshot", "Daemon version tag", "Chain name chip",
        "Headers vs blocks", "Verification progress", "Median block time", "RPC failover flag",
        "Peer health score", "On-ramp stats chip", "P2P market snippet", "Pool staked total",
        "Expected stake time", "Network alert dot", "SSE live indicator", "Sparkline mini",
        "Explorer deep link", "Addnode helper", "Hosting capacity", "Fleet online count",
        "Collateral tracker", "Multi-ping status",
    ]),
    ("trophies", 30, [
        "Trophy carousel slot", "Edition badge glow", "Top 25 progress", "GIF hover preview",
        "Sound on focus", "Block drop teaser", "Auction quick-list", "Transfer shortcut",
        "Hunter score chip", "Series completion", "Price factor tooltip", "PayPal hold banner",
        "Share to Discord", "Trophy count hero", "Gallery grid density", "Rarity frame",
        "Acquisition rail", "Effective USD trend", "Shop deep link", "Empty state CTA",
        "4D holodeck sync", "Media manifest merge", "Reduced-motion static", "Preload top 3 GIFs",
        "Trophy filter tabs", "Edition sort", "Mint height link", "Collectible disclaimer",
        "Peer transfer modal", "List edition wizard",
    ]),
    ("send_receive", 30, [
        "Address book picker", "Whitelist highlight", "Fee estimate chip", "Max minus fee",
        "Multi-step confirm", "2FA gate banner", "Recent recipients", "Memo field",
        "Validate debounce", "QR request amount", "BIP21 URI builder", "Deposit history",
        "Copy toast", "Share receive link", "Explorer address link", "Stale address badge",
        "Withdrawable chip", "Held MN2 explain", "Liquid vs staked", "Send result tx link",
        "Preview without broadcast", "Invalid address inline", "TOTP reminder", "Trusted only mode",
        "Receive single-flight", "Deposit refresh", "Amount formatter", "Fiat toggle send",
        "Clipboard guard", "Send cooldown hint",
    ]),
    ("monitors", 30, [
        "4D network strip", "5D explorer embed", "Peers sortable table", "Latency sparkline",
        "Mempool bytes KPI", "Connection target", "Inbound/outbound badge", "Staking panel",
        "Wallet 5d bars", "Alert bell strip", "History 24h chart", "Stall detector",
        "Sync warning sound", "Monitor pause hidden", "Auto-refresh 30s", "Peer copy addnode",
        "Block list overlay", "Search proxy", "User tx highlight", "Story strip optional",
        "Battle widget embed", "Masternode map grid", "Rich stats expander", "KPI source tag",
        "Daemon reachable", "RPC degraded banner", "On-ramp pulse", "P2P volume chip",
        "Hosting status", "Fleet map strip",
    ]),
    ("fun", 25, [
        "Fun mode toggle", "Network chime", "Block tick sound", "Trophy hover sting",
        "Battle join animation", "Confetti on send", "Holodeck scanline", "Neon accent pulse",
        "Achievement toast", "Level-up fanfare", "Upgrade unlock FX", "Carousel autoplay",
        "Map node glow", "Peer ping blip", "Mempool bubble", "Price flash green",
        "Streak counter", "Quest progress bar", "Easter egg konami", "Wallet mascot peek",
        "Seasonal border", "Sound volume slider", "Haptic desktop hint", "GIF cap six",
        "Reduced motion respect",
    ]),
    ("desktop", 25, [
        "Tauri tray peek", "Deep link router", "wallet:// tab map", "Offline banner",
        "Cookie bridge doc", "Auto-update feed", "System notify", "Title bar brand",
        "Window remember size", "Minimize to tray", "Balance tray poll", "Open in browser",
        "File protocol base", "Linux AppImage link", "Windows NSIS link", "macOS DMG link",
        "Secure store hint", "Desktop fun default", "Keyboard shortcuts", "Copy from tray",
        "Multi-monitor safe", "HiDPI sharp edges", "Launch at login opt", "Crash relaunch",
        "Version pin display",
    ]),
    ("discord", 25, [
        "Link status card", "Linked role OAuth", "VIP eligibility chip", "Hosting VIP chip",
        "Server invite CTA", "Manual ID paste", "Unlink confirm", "Avatar display",
        "Balance alert toggle", "Trophy drop toggle", "Block mint toggle", "Battle result toggle",
        "Share trophy embed", "Profile deep link", "OAuth login shortcut", "Guest banner",
        "Role chips row", "Notification note", "Webhook share flag", "DM scope future",
        "Casino VIP threshold", "Connect button primary", "Disconnect secondary", "Prefs localStorage",
        "Server join tracking",
    ]),
    ("security", 25, [
        "2FA enroll CTA", "Whitelist manager", "Withdraw verify gate", "TOTP on send",
        "Session timeout hint", "Trusted device note", "Address checksum", "Phishing warning",
        "Copy address verify", "Fee sanity check", "Max send guard", "Hold window explain",
        "PayPal hold lock", "Audit log link", "Ops token never client", "RPC secret server",
        "No local keys banner", "Platform ledger disclaimer", "Explorer tx verify",
        "Rate limit backoff", "Failed attempt lock", "Biometric future slot", "PIN future slot",
        "Security checklist", "Upgrade tier lock",
    ]),
]

TIERS = ("common", "rare", "epic")
UNLOCK_TYPES = ("default", "level", "achievement", "mn2_spent")


def _unlock(idx: int, category: str) -> dict:
    if idx <= 10:
        return {"type": "default", "value": 0, "label": "Available at wallet launch"}
    if idx <= 80:
        level = min(50, (idx // 5) + 1)
        return {"type": "level", "value": level, "label": f"Reach wallet level {level}"}
    if idx <= 160:
        ach = f"wallet_{category}_{idx:03d}"
        return {"type": "achievement", "value": ach, "label": f"Unlock achievement {ach}"}
    mn2 = (idx - 160) * 25
    return {"type": "mn2_spent", "value": mn2, "label": f"Spend {mn2} MN2 in wallet actions"}


def _effect(name: str, category: str) -> str:
    pains = {
        "speed": "Cuts wait time vs legacy profile wallet load.",
        "network_visibility": "Surfaces chain context missing from old wallet card.",
        "trophies": "Elevates trophies buried in shop/profile tabs.",
        "send_receive": "Fixes slow deposit RPC blocking overview in v1.",
        "monitors": "Adds operator-grade monitors absent in profile-mn2-wallet.js.",
        "fun": "Rewards engagement without blocking serious flows.",
        "desktop": "Extends web wallet to Tauri shell parity.",
        "discord": "Connects wallet events to Discord from Settings.",
        "security": "Hardens withdraw path from mn2-withdrawal-security.js patterns.",
    }
    return f"Enables {name.lower()} — {pains.get(category, 'Improves wallet UX.')}"


def main() -> None:
    upgrades = []
    idx = 1
    for category, _count, names in CATEGORIES:
        for i, name in enumerate(names):
            tier = TIERS[i % 3] if idx % 7 != 0 else TIERS[(i + 1) % 3]
            if idx % 25 == 0:
                tier = "epic"
            upgrades.append({
                "id": f"WR-UPG-{idx:03d}",
                "name": name,
                "effect": _effect(name, category),
                "category": category,
                "tier": tier,
                "unlock": _unlock(idx, category),
            })
            idx += 1

    assert len(upgrades) == 250, f"expected 250, got {len(upgrades)}"
    out_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "wallet_upgrades_catalog.json",
    )
    doc = {
        "version": 1,
        "generated_at": "2026-09-16",
        "total": 250,
        "categories": [c[0] for c in CATEGORIES],
        "upgrades": upgrades,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    print(f"Wrote {len(upgrades)} upgrades to {out_path}")


if __name__ == "__main__":
    main()
