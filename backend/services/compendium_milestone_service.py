"""Compendium 25/25 reading milestone → platform_news + Discord (M8 cross-road)."""
from __future__ import annotations

from typing import Any, Dict, List

_BASE_URL = None

MILESTONE_THRESHOLDS = (
    (3, "Free chapters complete", "Finished pages 1–3 — premium volumes await in Shop."),
    (10, "Compendium halfway", "10 of 25 rulebook volumes read — calm reader milestone."),
    (25, "Rulebook library complete", "All 25 compendium pages finished — calm mode V1–V16."),
)


def _base_url() -> str:
    global _BASE_URL
    if _BASE_URL is None:
        import os

        _BASE_URL = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")
    return _BASE_URL


def _load_data(user_id: str) -> dict:
    from backend.services.user_engagement import _load

    return _load(user_id, "compendium_pages.json")


def _save_data(user_id: str, data: dict) -> None:
    from backend.services.user_engagement import _save

    _save(user_id, "compendium_pages.json", data)


def _celebrated_thresholds(data: dict) -> List[int]:
    raw = data.get("milestones_celebrated")
    if isinstance(raw, list):
        return [int(x) for x in raw if str(x).isdigit()]
    if data.get("milestone_celebrated"):
        return [25]
    return []


def _mark_celebrated(user_id: str, threshold: int) -> None:
    data = _load_data(user_id)
    done = set(_celebrated_thresholds(data))
    if threshold in done:
        return
    done.add(threshold)
    data["milestones_celebrated"] = sorted(done)
    if threshold >= 25:
        data["milestone_celebrated"] = True
    _save_data(user_id, data)


def _post_milestone(
    user_id: str,
    *,
    threshold: int,
    title: str,
    summary: str,
    mn2_amount: float = 0.0,
) -> Dict[str, Any]:
    news = {"success": False}
    discord = {"success": False}
    mn2 = {"success": False, "skipped": True}

    try:
        from backend.services.platform_news_publish import publish

        news = publish(
            item_id=f"compendium-milestone-{threshold}-{user_id}",
            title=title,
            summary=summary,
            channel="compendium",
            href="/compendium/?calm=1",
            featured=threshold >= 25,
        )
    except Exception as exc:
        news = {"success": False, "error": str(exc)}

    try:
        from backend.services.discord_service import post_message

        payload = {
            "embeds": [{
                "title": f"📚 {title}",
                "description": (
                    f"**{user_id}** — {summary}\n"
                    f"Continue at {_base_url()}/compendium/?calm=1"
                ),
                "url": f"{_base_url()}/compendium/?calm=1",
                "footer": {"text": f"Milestone {threshold}/25 · Rewards sync on-site."},
            }],
        }
        discord = post_message(
            "announcements",
            payload,
            message_id=f"compendium-milestone:{threshold}:{user_id}",
        )
    except Exception as exc:
        discord = {"success": False, "error": str(exc)}

    try:
        from backend.services.activity_events_service import emit

        emit(
            "compendium_milestone",
            user_id=user_id,
            channel="compendium",
            text=title,
            payload={"threshold": threshold, "summary": summary},
        )
    except Exception:
        pass

    if mn2_amount > 0:
        try:
            from backend.services.game_mn2_rewards import credit_mn2

            mn2 = credit_mn2(
                user_id,
                mn2_amount,
                source=f"compendium_milestone_{threshold}",
                reference=f"compendium-ms-{threshold}-{user_id}",
                metadata={"threshold": threshold},
            )
        except Exception as exc:
            mn2 = {"success": False, "error": str(exc)}

    return {"news": news, "discord": discord, "mn2": mn2}


def maybe_celebrate_threshold(
    user_id: str,
    threshold: int,
    *,
    total_read: int,
    total_pages: int = 25,
) -> Dict[str, Any]:
    if total_read < threshold or not user_id:
        return {"celebrated": False, "reason": "below_threshold"}

    data = _load_data(user_id)
    if threshold in _celebrated_thresholds(data):
        return {"celebrated": False, "reason": "already_celebrated", "threshold": threshold}

    title = summary = ""
    for t, ti, su in MILESTONE_THRESHOLDS:
        if t == threshold:
            title, summary = ti, su
            break
    if not title:
        return {"celebrated": False, "reason": "unknown_threshold"}

    _mark_celebrated(user_id, threshold)
    mn2_amount = 0.01 if threshold >= 25 else (0.005 if threshold >= 10 else 0.0)
    effects = _post_milestone(
        user_id,
        threshold=threshold,
        title=title,
        summary=summary.replace("25", str(total_pages)),
        mn2_amount=mn2_amount,
    )

    if threshold >= 25:
        try:
            from backend.services.activity_events_service import emit

            emit(
                "compendium_complete",
                user_id=user_id,
                channel="compendium",
                text=f"Completed {total_pages} compendium pages",
                payload={"total_pages": total_pages},
            )
        except Exception:
            pass

    return {
        "celebrated": True,
        "threshold": threshold,
        "user_id": user_id,
        **effects,
    }


def maybe_celebrate_progress(user_id: str, *, total_read: int, total_pages: int = 25) -> Dict[str, Any]:
    """Fire idempotent Discord/news hooks at 3, 10, and 25 pages read."""
    results = []
    for threshold, _, _ in MILESTONE_THRESHOLDS:
        if total_read >= threshold:
            results.append(
                maybe_celebrate_threshold(
                    user_id,
                    threshold,
                    total_read=total_read,
                    total_pages=total_pages,
                )
            )
    celebrated = [r for r in results if r.get("celebrated")]
    return {"success": True, "celebrated_count": len(celebrated), "results": results}


def maybe_celebrate_complete(user_id: str, *, total_read: int, total_pages: int = 25) -> Dict[str, Any]:
    """Idempotent celebration when a user finishes all compendium pages."""
    return maybe_celebrate_threshold(
        user_id,
        25,
        total_read=max(total_read, total_pages),
        total_pages=total_pages,
    )
