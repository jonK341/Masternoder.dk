"""Discord Spiderbot — live platform facts, rewritten by an LLM when one is configured."""
from __future__ import annotations

import json
from typing import Any, Dict


def platform_facts() -> Dict[str, Any]:
    """Same snapshot the studio cards and NFT desk use."""
    from backend.services.studio_floor_service import snapshot

    floor = snapshot()
    names = [str(row.get("name") or row.get("sku")) for row in (floor.get("nfts") or [])[:8]]
    portraits = [
        {
            "name": row.get("display_name"),
            "picture_url": row.get("picture_url"),
            "nft_name": row.get("nft_name"),
        }
        for row in (floor.get("performers") or [])[:6]
    ]
    return {
        "hosting_spots": floor.get("hosting_spots"),
        "nft_editions": floor.get("nft_editions"),
        "nft_names": names,
        "audio_clips": floor.get("audio_clips") or [],
        "audio_url": floor.get("audio_url") or "",
        "portraits": portraits,
        "wallet": "one MN2 wallet per user, coins framed on that address",
        "together": floor.get("together"),
    }


def _calculated_reply(query: str, facts: Dict[str, Any]) -> str:
    q = (query or "").lower()
    portraits = facts.get("portraits") or []
    lead = portraits[0] if portraits else {}
    if lead.get("name"):
        bits = [
            (
                f"{lead.get('name')}'s portrait is on the floor with the {lead.get('nft_name')} NFT, "
                f"paid from one MN2 wallet."
            )
        ]
    else:
        bits = ["The floor shares one MN2 wallet per user."]
    bits.append(f"Hosting is capped at {facts.get('hosting_spots')} masternode spots.")
    bits.append(f"The NFT desk has {facts.get('nft_editions')} editions.")
    names = facts.get("nft_names") or []
    if names:
        bits.append("On the shelf: " + ", ".join(names[:4]) + ".")
    clips = facts.get("audio_clips") or []
    if clips:
        first = clips[0]
        bits.append(
            f"Latest Discord audio is {first.get('filename') or 'a clip'}"
            + (f" from {first.get('username')}" if first.get("username") else "")
            + "."
        )
    else:
        bits.append("No Discord audio clips are indexed yet.")
    if any(word in q for word in ("wallet", "address", "coin")):
        bits.append("Each user keeps one MN2 deposit wallet, and coins on it follow coins_per_mn2.")
    if "cam" in q or "picture" in q:
        bits.append("Camgirl cards use portrait pictures, including a close-up still.")
    if not q.strip():
        bits.append("Ask about hosting, NFTs, wallets, or Discord audio.")
    return " ".join(bits)


def reply(query: str, *, discord_id: str = "") -> Dict[str, Any]:
    """Answer like a floor host. LLM when configured; otherwise a calculated brief."""
    facts = platform_facts()
    prompt = (query or "").strip() or "What is live on MasterNoder right now?"
    system = (
        "You are Spiderbot, the MasterNoder Discord host. "
        "Write like a person on the floor: two or three short sentences, specific, no slogans. "
        "Use only the live facts you are given. Do not invent balances, addresses, or prices. "
        f"The speaker Discord id is {discord_id or 'unknown'}."
    )
    user = "Live facts:\n" + json.dumps(facts, default=str) + "\n\nUser:\n" + prompt
    try:
        from backend.services.llm_service import complete

        result = complete(
            user,
            system_prompt=system,
            temperature=0.55,
            max_tokens=220,
            timeout=12,
            task_type="speed",
        )
        text = (getattr(result, "content", None) or "").strip()
        if getattr(result, "success", False) and text:
            return {
                "success": True,
                "text": text[:1800],
                "source": "llm",
                "provider": getattr(result, "provider", None),
                "ai_score": 0.9,
                "audio_url": facts.get("audio_url") or "",
                "facts": facts,
            }
    except Exception:
        pass
    return {
        "success": True,
        "text": _calculated_reply(prompt, facts)[:1800],
        "source": "calculated",
        "ai_score": 0.45,
        "audio_url": facts.get("audio_url") or "",
        "facts": facts,
    }
