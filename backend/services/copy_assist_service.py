"""
Pro-gated copy assistant — titles, descriptions, forum posts, shop listings.

Requires monetization tier `pro` when MONETIZATION_TIER_ENFORCEMENT=1.
When enforcement is off, `creator` tier may also use copy assist (dev/staging friendly).
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

COPY_KINDS: Dict[str, Dict[str, str]] = {
    "product_title": {
        "label": "Product title",
        "hint": "Short punchy title for a shop SKU or coin pack.",
    },
    "product_description": {
        "label": "Product description",
        "hint": "2–3 sentences selling the benefit; mention MN2/coins if relevant.",
    },
    "shop_listing": {
        "label": "Marketplace listing",
        "hint": "Player stall listing — title + one-line hook.",
    },
    "video_title": {
        "label": "Video title",
        "hint": "Catchy title for an AI-generated video on MasterNoder.",
    },
    "video_description": {
        "label": "Video description",
        "hint": "Scene summary / prompt expansion for the generator.",
    },
    "forum_post": {
        "label": "Forum / community post",
        "hint": "Friendly post about MN2, staking, or platform features.",
    },
}


def list_kinds() -> Dict[str, Any]:
    return {
        "success": True,
        "kinds": [
            {"id": k, "label": v["label"], "hint": v["hint"]}
            for k, v in COPY_KINDS.items()
        ],
    }


def _tier_allowed(user_id: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    from backend.services.monetization_tier_service import resolve_user_tier, _tier_enforcement_enabled

    tier = resolve_user_tier(user_id or "default_user")
    if tier == "pro":
        return True, tier, None
    if not _tier_enforcement_enabled() and tier == "creator":
        return True, tier, None
    upsell = {
        "target_tier": "pro",
        "reason": "copy_assist",
        "message": "Copy Assist is a Pro feature. Upgrade via Shop → MasterNoder Pro subscription.",
        "shop_url": "/shop/",
    }
    return False, tier, upsell


def _prompt_for_kind(kind: str, context: Dict[str, Any]) -> str:
    meta = COPY_KINDS.get(kind) or COPY_KINDS["product_description"]
    subject = (context.get("subject") or context.get("topic") or "").strip()
    keywords = (context.get("keywords") or "").strip()
    tone = (context.get("tone") or "friendly, professional").strip()
    existing = (context.get("existing_text") or context.get("draft") or "").strip()
    platform = (context.get("platform") or "MasterNoder.dk").strip()

    parts = [
        f"Task: {meta['label']} for {platform}.",
        meta["hint"],
        f"Tone: {tone}.",
    ]
    if subject:
        parts.append(f"Subject: {subject}.")
    if keywords:
        parts.append(f"Keywords: {keywords}.")
    if existing:
        parts.append(f"Improve or expand this draft:\n{existing[:800]}")
    parts.append("Output only the final copy — no preamble or quotes.")
    return "\n".join(parts)


def _template_copy(kind: str, ctx: Dict[str, Any], tier: str) -> Dict[str, Any]:
    subject = (ctx.get("subject") or ctx.get("topic") or "Your item").strip()
    fallback = {
        "product_title": f"{subject} — MasterNoder",
        "video_title": f"{subject} | AI Video",
        "video_description": f"A short video about {subject}. Created on MasterNoder generator.",
        "forum_post": f"Sharing an update about {subject} on MasterNoder — staking, shop, and generator all in one place.",
        "shop_listing": f"{subject} — fair price, instant delivery on-site.",
        "product_description": f"{subject}: boost your MasterNoder experience with coins, MN2 utilities, and on-site rewards.",
    }
    return {
        "success": True,
        "text": fallback.get(kind, subject),
        "kind": kind,
        "tier": tier,
        "source": "template",
        "provider": None,
    }


def generate_copy(user_id: str, kind: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    kind = (kind or "product_description").strip()
    if kind not in COPY_KINDS:
        return {"success": False, "error": "unknown_kind", "allowed_kinds": list(COPY_KINDS.keys())}

    allowed, tier, upsell = _tier_allowed(user_id)
    if not allowed:
        return {
            "success": False,
            "error": "pro_required",
            "http_status": 403,
            "tier": tier,
            "upsell": upsell,
        }

    ctx = dict(context or {})
    prompt = _prompt_for_kind(kind, ctx)

    try:
        from backend.services.llm_service import complete, is_available
    except Exception:
        is_available = lambda: False  # noqa: E731
        complete = None  # type: ignore

    if not is_available() or complete is None:
        return _template_copy(kind, ctx, tier)

    result = complete(
        prompt=prompt,
        system_prompt="You are a concise marketing copywriter for a crypto + creator platform. Plain text only.",
        temperature=0.65,
        max_tokens=280,
        task_type="free",
    )
    if not result.success or not (result.content or "").strip():
        out = _template_copy(kind, ctx, tier)
        out["llm_error"] = (result.error or "llm_failed")[:200]
        return out

    return {
        "success": True,
        "text": result.content.strip(),
        "kind": kind,
        "tier": tier,
        "source": "llm",
        "provider": getattr(result, "provider", None),
    }


def _cli_main(argv: Optional[list] = None) -> int:
    import argparse
    import json
    import os
    import sys

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if root not in sys.path:
        sys.path.insert(0, root)

    p = argparse.ArgumentParser(
        description="Copy Assist CLI — list kinds or generate marketing copy (Pro-gated).",
        epilog="Examples:\n"
        "  python scripts/copy_assist.py list\n"
        "  python scripts/copy_assist.py generate --kind video_title --subject \"Nature doc\"",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List available copy kinds")

    gen = sub.add_parser("generate", help="Generate copy for a kind")
    gen.add_argument("--kind", default="product_description", choices=list(COPY_KINDS.keys()))
    gen.add_argument("--subject", default="", help="Topic or product name")
    gen.add_argument("--keywords", default="")
    gen.add_argument("--tone", default="friendly, professional")
    gen.add_argument("--user", default="default_user", help="User id for tier check")
    gen.add_argument("--json", action="store_true", help="Print raw JSON response")

    args = p.parse_args(argv)
    if args.command == "list":
        print(json.dumps(list_kinds(), indent=2))
        return 0

    ctx = {
        "subject": args.subject,
        "keywords": args.keywords,
        "tone": args.tone,
    }
    out = generate_copy(args.user, args.kind, ctx)
    if args.json:
        print(json.dumps(out, indent=2))
    elif out.get("success"):
        print(out.get("text", ""))
        src = out.get("source")
        if src:
            print(f"\n(source: {src}, tier: {out.get('tier', '?')})", file=sys.stderr)
    else:
        print(json.dumps(out, indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
