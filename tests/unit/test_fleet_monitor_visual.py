"""Fleet monitor theme + encoded background API."""
from backend.services.fleet_monitor_visual_service import (
    encoded_background_pool,
    load_themes,
    visual_payload,
)


def test_load_themes_has_ten():
    cat = load_themes()
    assert cat["theme_count"] == 10
    assert len(cat["themes"]) == 10


def test_visual_payload_default():
    d = visual_payload()
    assert d["success"] is True
    assert d["active_theme_id"]
    assert isinstance(d["encoded_pool"], list)


def test_encoded_pool_theme_profile():
    pool = encoded_background_pool("generator_premium")
    assert pool
    assert any("ENCODE_PROFILE" in __import__("base64").b64decode(p).decode("utf-8", "ignore") for p in pool[:3])
