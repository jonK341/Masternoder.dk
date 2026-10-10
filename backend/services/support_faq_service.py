"""
Site + Discord support FAQ — keyword fallback + optional free-tier LLM.

No custody or fund movement via chat. Directs users to Profile, Shop, and on-site flows.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

_BASE_URL = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")

SUPPORT_FAQ_TOPICS: List[Dict[str, str]] = [
    {"q": "deposit", "a": "Get your MN2 deposit address on Profile → wallet. Credits arrive after daemon confirms on-chain (not from Discord or chat)."},
    {"q": "withdraw", "a": "Withdraw from Profile when balance is liquid and verification/whitelist rules pass. The daemon broadcasts the tx — never via chat."},
    {"q": "staking", "a": "Stake MN2 from Profile; rewards come from the pool daemon minting. Browser rig is engagement-only."},
    {"q": "hosting", "a": "Rent masternode hosting slots at /hosting/ or Shop — PayPal $4.99/slot, coins, or MN2. Fleet provisioning runs on-site after purchase."},
    {"q": "shop", "a": "Coin packs, boosters, hosting, and Pro subscription at /shop/. Promo codes: DISCORD-STARTER, HOSTMN5, GENERATE10, MARKET-BONUS."},
    {"q": "casino", "a": "Casino supports coins, MN2, and PayPal USD at /casino/. Enable account security on Profile for real-money play."},
    {"q": "discord", "a": "Link Discord on Profile for VIP perks. Redeem DISCORD-STARTER (+100 coins) or HOSTMN5 (5% off hosting) in the Shop promo box — on-site only."},
    {"q": "market", "a": "Trade MN2 for in-app coins at /explorer?tab=market — limit orders and agent liquidity. No custody on Discord."},
    {"q": "generator", "a": "Create AI videos at /generator/ with coins, generation credits, or Pro tier. Themes and MN2 pay options on the same page."},
    {"q": "pro", "a": "MasterNoder Pro subscription unlocks longer videos, copy assist, and premium generator caps — subscribe via Shop when the live PayPal plan is active."},
    {"q": "camgirls", "a": "Browse performers at /camgirls/ — unlock and tip with in-app coins. All rewards claimed on-site."},
    {"q": "compendium", "a": "Read V1–V16 rulebooks at /compendium/?calm=1 — calm mode syncs progress to Game Hub."},
    {"q": "library", "a": "Same as compendium — open /compendium/?calm=1 for the rulebook library and reading progress."},
    {"q": "wallet", "a": "Your web wallet lives under Profile. We never ask for seed phrases or move funds through chat or Discord."},
]


def list_topics() -> List[str]:
    return [row["q"] for row in SUPPORT_FAQ_TOPICS]


def _keyword_answer(query: str) -> Optional[Dict[str, Any]]:
    q = (query or "").strip().lower()
    if not q:
        return None
    for row in SUPPORT_FAQ_TOPICS:
        if row["q"] in q or q in row["a"].lower():
            return {"success": True, "topic": row["q"], "answer": row["a"], "source": "keyword"}
    return None


def _faq_context_block() -> str:
    lines = [f"- {row['q']}: {row['a']}" for row in SUPPORT_FAQ_TOPICS]
    return "\n".join(lines)


def _llm_answer(query: str, channel: str = "web") -> Optional[Dict[str, Any]]:
    try:
        from backend.services.llm_service import chat
    except Exception:
        return None
    system = (
        f"You are the MasterNoder.dk support assistant ({channel}). "
        "Answer in 2–4 short sentences. Be friendly and precise.\n"
        "RULES:\n"
        "- Never promise to move, send, or refund MN2/coins via chat or Discord.\n"
        "- Never ask for passwords, seed phrases, or private keys.\n"
        "- Direct wallet/deposit/withdraw/staking actions to Profile on the website.\n"
        "- Direct purchases to /shop/ or /hosting/.\n"
        f"- Base URL: {_BASE_URL}\n\n"
        "KNOWLEDGE BASE:\n"
        f"{_faq_context_block()}"
    )
    result = chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": (query or "").strip()[:500]},
        ],
        temperature=0.3,
        max_tokens=220,
        task_type="free",
    )
    if not result.success or not (result.content or "").strip():
        return None
    return {
        "success": True,
        "answer": result.content.strip(),
        "source": "llm",
        "provider": getattr(result, "provider", None),
    }


def faq_answer(
    query: str,
    *,
    use_llm: bool = True,
    channel: str = "web",
) -> Dict[str, Any]:
    """Return FAQ answer — keyword first for exact topics; LLM for open questions when enabled."""
    q = (query or "").strip()
    if not q:
        return {
            "success": True,
            "answer": "Ask about deposit, withdraw, staking, hosting, shop, casino, market, generator, Pro, camgirls, compendium, or Discord linking.",
            "topics": list_topics(),
            "source": "static",
        }

    hit = _keyword_answer(q)
    if hit and len(q.split()) <= 3:
        hit["topics"] = list_topics()
        return hit

    if use_llm:
        llm = _llm_answer(q, channel=channel)
        if llm:
            llm["topics"] = list_topics()
            return llm

    if hit:
        hit["topics"] = list_topics()
        return hit

    return {
        "success": True,
        "answer": "For account help visit Profile or open /shop/ for purchases. We cannot move funds via chat — all wallet actions happen on-site.",
        "topics": list_topics(),
        "source": "fallback",
    }
