"""Fleet bot avatars and progress tier images."""
from backend.services.fleet_bot_visuals_service import (
    avatar_for_bot,
    enrich_bot_visuals,
    progress_tier_for_level,
)


def test_progress_tier_levels():
    t5 = progress_tier_for_level(22)
    assert t5["tier"] == 20
    assert "progress-tier-5" in t5["progress_image_url"]
    t1 = progress_tier_for_level(2)
    assert t1["tier"] == 1


def test_avatar_by_kind_and_badge():
    a = avatar_for_bot({"kind": "risk", "badge": "velocity"})
    assert "agents" in a
    b = avatar_for_bot({"kind": "analytics", "badge": "lane"})
    assert "analytics_agent" in b


def test_sanitize_bot_includes_visuals():
    from backend.services.exchange_fleet_progress_monitor_service import _sanitize_bot

    row = _sanitize_bot(
        {
            "id": "fleet_analytics_alpha",
            "label": "PA-α",
            "kind": "analytics",
            "badge": "lane",
            "enabled": True,
            "progression": {"level": 12, "rank_title": "Specialist", "xp_progress_pct": 42.0},
        }
    )
    assert row.get("avatar_url")
    assert row.get("progress_image_url")
    assert "progress-tier-3" in row["progress_image_url"]
