"""Best-effort auto-publish hooks into platform_news (+ optional Discord later)."""
from __future__ import annotations

from typing import Any, Dict, Optional


def publish_event(
    *,
    item_id: str,
    title: str,
    summary: str,
    channel: str,
    href: str = "/",
    featured: bool = False,
    channels: Optional[list] = None,
) -> Dict[str, Any]:
    try:
        from backend.services.platform_news_publish import publish

        return publish(
            item_id=item_id,
            title=title,
            summary=summary,
            channel=channel,
            href=href,
            featured=featured,
            channels=channels,
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)[:200]}


def on_agent_funding(*, agent_id: str, amount: float, dry_run: bool = False) -> Dict[str, Any]:
    if dry_run or float(amount or 0) <= 0:
        return {"success": True, "skipped": True}
    return publish_event(
        item_id=f"agent-fund-{agent_id}",
        title=f"Trader agent funded: {agent_id}",
        summary=f"{amount} MN2 credited to {agent_id} from the agent treasury pool.",
        channel="agents",
        href="/dashboard/agents_control/",
        channels=["agents", "ops", "market"],
    )


def on_market_fill(*, mn2_amount: float, price: float, buyer: str = "", seller: str = "") -> Dict[str, Any]:
    amt = float(mn2_amount or 0)
    # Only notable fills — avoid news spam.
    if amt < 25:
        return {"success": True, "skipped": True, "reason": "below_threshold"}
    return publish_event(
        item_id=f"market-fill-{buyer}-{seller}-{int(amt * 1000)}",
        title=f"Market fill: {amt:.2f} MN2",
        summary=f"{amt:.4f} MN2 traded at {price:.2f} coins/MN2.",
        channel="market",
        href="/market/",
        channels=["market", "home"],
    )


def on_security_alert(*, title: str, summary: str, item_id: str = "security-alert") -> Dict[str, Any]:
    return publish_event(
        item_id=item_id,
        title=title,
        summary=summary,
        channel="ops",
        href="/debugger/",
        featured=True,
        channels=["ops", "discord"],
    )
