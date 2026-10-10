"""Camgirls platform status and info-bar payload."""
from backend.services.camgirls_status_service import platform_status, studio_tech_for_performer


def test_platform_status_includes_tech_and_todos():
    out = platform_status()
    assert out.get("success") is True
    assert out.get("performers_count", 0) >= 15
    assert out.get("agents_linked", 0) >= 15
    assert isinstance(out.get("next_todos"), list)
    assert len(out.get("next_todos") or []) >= 1
    assert "platform_tech" in out
    roster = out.get("performers") or []
    assert roster
    first = roster[0]
    assert first.get("agent_id")
    assert "features" in first
    assert "payments" in first


def test_studio_tech_for_performer_nova():
    livekit = {"configured": False, "mode": "stub"}
    tech = studio_tech_for_performer(
        {"id": "performer_nova", "ai_enabled": True},
        livekit=livekit,
        paypal_on=False,
    )
    assert tech.get("task_kind") in ("speed", "free", "default", "creative")
    assert tech.get("agent_id") == "camgirl_agent_nova"
    assert "mn2" in tech.get("payments", [])
    assert "paypal_checkout" not in tech.get("features", [])
