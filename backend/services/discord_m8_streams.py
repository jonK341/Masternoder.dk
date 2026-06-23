"""M8 Discord income streams #53–60 (Gate S: no custody on Discord; rewards on-site only)."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE_URL = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")

_ALERT_TYPES = frozenset({
    "staking_stopped",
    "height_stall",
    "casino_jackpot_win",
    "casino_big_win",
    "casino_tournament_end",
    "casino_tournament_prize",
    "casino_mn2_promo",
    "casino_discord_promo_created",
    "platform_news",
    "generator_complete",
    "p2p_market_fill",
    "p2p_market_order",
    "trader_market_tick",
    "camgirl_unlock",
    "camgirl_tip",
    "agent_funded",
    "agent_treasury_deposit",
    "game_mn2_reward",
    "compendium_complete",
    "discord_post_failed",
})

_AFFILIATE_ROTATION = [
    {"id": "casino", "label": "Casino", "path": "/casino/"},
    {"id": "market", "label": "MN2 market", "path": "/explorer?tab=market"},
    {"id": "shop", "label": "Shop boosters", "path": "/shop/"},
    {"id": "generator", "label": "Video generator", "path": "/generator/"},
    {"id": "staking", "label": "MN2 staking", "path": "/profile/"},
    {"id": "camgirls", "label": "Camgirls", "path": "/camgirls/"},
    {"id": "compendium", "label": "Rulebook library", "path": "/compendium/?calm=1"},
    {"id": "explorer", "label": "Explorer", "path": "/explorer/"},
    {"id": "quests", "label": "Daily quests", "path": "/quests/"},
]

_SUPPORT_FAQ = [
    {"q": "deposit", "a": "Get your MN2 deposit address on Profile → wallet. Credits arrive after daemon confirms on-chain (not from Discord)."},
    {"q": "withdraw", "a": "Withdraw from Profile when balance is liquid and verification/whitelist rules pass. The daemon broadcasts the tx."},
    {"q": "staking", "a": "Stake MN2 from Profile; rewards come from the pool daemon minting. Browser rig is engagement-only."},
    {"q": "casino", "a": "Casino supports coins, MN2, and PayPal USD. Enable account security on Profile for real-money play."},
    {"q": "discord", "a": "Link Discord on Profile for VIP perks. Redeem **DISCORD-STARTER** (+100 coins) or **HOSTMN5** (5% off hosting) in the Shop promo box — on-site only."},
    {"q": "market", "a": "Trade MN2 for in-app coins at /explorer?tab=market — limit orders and agent liquidity. No custody on Discord."},
    {"q": "camgirls", "a": "Browse performers at /camgirls/ — unlock and tip with in-app coins. All rewards claimed on-site."},
    {"q": "compendium", "a": "Read V1–V16 rulebooks at /compendium/?calm=1 — calm mode syncs progress to Game Hub."},
    {"q": "library", "a": "Same as compendium — open /compendium/?calm=1 for the rulebook library and reading progress."},
]


def _iso_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def run_alert_funnel(*, limit: int = 8) -> Dict[str, Any]:
    """M8 #53 — high-signal activity_events → Discord #activity embed."""
    from backend.services.activity_events_service import recent
    from backend.services.discord_service import post_message

    rows = recent(limit=80)
    picked = [r for r in rows if (r.get("type") or "") in _ALERT_TYPES][:limit]
    if not picked:
        return {"success": True, "posted": 0, "reason": "no_alert_events"}
    lines = []
    for r in picked:
        ch = r.get("channel") or "site"
        typ = r.get("type") or "event"
        txt = (r.get("text") or "")[:100]
        lines.append(f"• **{typ}** [{ch}] {txt}")
    payload = {
        "embeds": [{
            "title": "Platform alert funnel",
            "description": "\n".join(lines),
            "url": f"{_BASE_URL}/staking-monitor/",
            "footer": {"text": "Ops signal only — no funds move via Discord."},
        }],
    }
    result = post_message("activity", payload, message_id=f"alert-funnel:{_iso_day()}")
    return {"success": result.get("success"), "posted": len(picked), "discord": result}


def publish_partner_spotlight(
    *,
    title: str,
    summary: str,
    href: str = "/shop/",
    partner_id: Optional[str] = None,
) -> Dict[str, Any]:
    """M8 #54 — partner/market spotlight → platform_news + Discord."""
    try:
        from backend.services.platform_news_publish import publish
        from backend.services.discord_service import post_message

        pid = partner_id or f"partner-{int(datetime.now(timezone.utc).timestamp())}"
        pub = publish(
            item_id=pid,
            title=title,
            summary=summary,
            channel="market",
            href=href,
            featured=True,
        )
        if not pub.get("success"):
            return {"success": False, "error": pub.get("error") or "publish_failed", "news": pub}

        payload = {
            "embeds": [{
                "title": f"Partner spotlight: {title}",
                "description": summary[:500],
                "url": f"{_BASE_URL}{href if href.startswith('/') else '/' + href}",
                "footer": {"text": "Affiliate/partner disclosure may apply."},
            }],
        }
        disc = post_message("market", payload, message_id=f"partner:{pid}")
        return {"success": True, "news": pub.get("item"), "discord": disc}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def run_quest_bot_digest() -> Dict[str, Any]:
    """M8 #56 — daily quest links (rewards claimed on-site only)."""
    from backend.services.discord_service import post_message
    from backend.services.user_engagement import _QUEST_TEMPLATES

    daily = [q for q in _QUEST_TEMPLATES if q.get("type") == "daily"][:5]
    lines = [
        f"• **{q.get('title', 'Quest')}** — {q.get('description', '')[:80]}"
        for q in daily
    ]
    payload = {
        "embeds": [{
            "title": "Today's quests",
            "description": "\n".join(lines) or "Check the site for quests.",
            "url": f"{_BASE_URL}/quests/",
            "footer": {"text": "Complete and claim rewards on masternoder.dk only."},
        }],
    }
    result = post_message("quests", payload, message_id=f"quest-bot:{_iso_day()}")
    return {"success": result.get("success"), "quests_listed": len(daily), "discord": result}


_PROMO_ROTATION = [
    {
        "code": "DISCORD-STARTER",
        "headline": "Discord welcome bonus",
        "detail": "Redeem **DISCORD-STARTER** in Shop → +100 coins (one per user).",
        "path": "/shop/",
    },
    {
        "code": "HOSTMN5",
        "headline": "Hosting checkout promo",
        "detail": "Use **HOSTMN5** at checkout for 5% off masternode hosting slots.",
        "path": "/shop?tab=mn2",
    },
    {
        "code": "MARKET-BONUS",
        "headline": "Trader market bonus",
        "detail": "Redeem **MARKET-BONUS** in Shop → +75 coins and +0.25 MN2.",
        "path": "/explorer?tab=market",
    },
    {
        "code": "GENERATE10",
        "headline": "Generator upsell",
        "detail": "Checkout code **GENERATE10** — 10% off coin packs + 25 bonus coins.",
        "path": "/generator/",
    },
]


def _promo_for_affiliate_link(link_id: str) -> str:
    hints = {
        "shop": "Promo: **DISCORD-STARTER** (+100 coins) · **HOSTMN5** (5% hosting)",
        "market": "Promo: **MARKET-BONUS** (+75 coins + 0.25 MN2)",
        "generator": "Checkout: **GENERATE10** (10% off + bonus coins)",
        "staking": "Bundle: **MN2 starter** — coins + 7-day staking boost",
    }
    return hints.get(link_id, "")


def promo_rotator_payload() -> Dict[str, Any]:
    """M8 #52 — rotate shop promo codes in Discord announcements."""
    from backend.services.discord_service import post_message, track_click

    if not _PROMO_ROTATION:
        return {"success": False, "error": "no_promos"}
    idx = datetime.now(timezone.utc).toordinal() % len(_PROMO_ROTATION)
    promo = _PROMO_ROTATION[idx]
    url = f"{_BASE_URL}{promo['path']}"
    payload = {
        "embeds": [{
            "title": f"Shop promo: {promo['headline']}",
            "description": f"{promo['detail']}\n\n→ {url}",
            "url": url,
            "footer": {"text": f"Code: {promo['code']} · redeem on masternoder.dk only"},
        }],
    }
    result = post_message("announcements", payload, message_id=f"promo-rot:{promo['code']}:{_iso_day()}")
    track_click(None, f"promo-{promo['code'].lower()}", {"source": "promo_rotator", "url": url})
    return {"success": result.get("success"), "promo": promo, "discord": result}


def affiliate_rotator_payload() -> Dict[str, Any]:
    """M8 #57 — rotate featured affiliate link by UTC day."""
    from backend.services.discord_service import post_message, track_click

    if not _AFFILIATE_ROTATION:
        return {"success": False, "error": "no_links"}
    idx = datetime.now(timezone.utc).toordinal() % len(_AFFILIATE_ROTATION)
    link = _AFFILIATE_ROTATION[idx]
    url = f"{_BASE_URL}{link['path']}"
    promo_hint = _promo_for_affiliate_link(link.get("id") or "")
    description = f"Today's spotlight → {url}"
    if promo_hint:
        description += f"\n\n{promo_hint}"
    payload = {
        "embeds": [{
            "title": f"Featured: {link['label']}",
            "description": description,
            "url": url,
            "footer": {"text": "Affiliate disclosure: platform-operated links."},
        }],
    }
    result = post_message("announcements", payload, message_id=f"affiliate-rot:{_iso_day()}")
    track_click(None, link["id"], {"source": "affiliate_rotator", "url": url})
    return {"success": result.get("success"), "link": link, "discord": result}


def post_generator_showcase(
    *,
    job_id: str,
    title: str,
    user_id: Optional[str] = None,
    video_url: Optional[str] = None,
) -> Dict[str, Any]:
    """M8 #59 — new generator completion → platform_news channel=generator + Discord."""
    from backend.services.platform_news_publish import publish
    from backend.services.discord_service import post_message

    href = video_url or f"/generator/?job={job_id}"
    summary = f"New video ready — job {job_id[:8]}…"
    pub = publish(
        item_id=f"gen-{job_id}",
        title=title[:120] or "New generator video",
        summary=summary,
        channel="generator",
        href=href,
        featured=False,
    )
    payload = {
        "embeds": [{
            "title": title[:120] or "Generator showcase",
            "description": summary,
            "url": f"{_BASE_URL}{href if href.startswith('/') else '/' + href}",
        }],
    }
    disc = post_message("generator", payload, message_id=f"gen-showcase:{job_id}")
    try:
        from backend.services.activity_events_service import emit
        emit("generator_complete", channel="generator", text=title[:80], payload={"job_id": job_id, "user_id": user_id})
    except Exception:
        pass
    return {"success": pub.get("success"), "news": pub.get("item"), "discord": disc}


def support_faq_answer(query: str) -> Dict[str, Any]:
    """M8 #60 — lightweight FAQ (no custody; directs users to site)."""
    q = (query or "").strip().lower()
    if not q:
        return {
            "success": True,
            "answer": "Ask about deposit, withdraw, staking, casino, market, camgirls, compendium, or discord linking.",
            "topics": [row["q"] for row in _SUPPORT_FAQ],
        }
    for row in _SUPPORT_FAQ:
        if row["q"] in q or q in row["a"].lower():
            return {"success": True, "topic": row["q"], "answer": row["a"]}
    return {
        "success": True,
        "answer": "For account help visit Profile or contact ops. We cannot move funds via chat.",
        "topics": [row["q"] for row in _SUPPORT_FAQ],
    }
