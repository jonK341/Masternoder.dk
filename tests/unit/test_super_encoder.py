"""Unit tests for Super Encoder creator app."""
import os
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)


def test_max_videos_is_125():
    from backend.services.super_encoder_service import get_config, _MAX_VIDEOS
    cfg = get_config()
    assert int(cfg.get("max_videos") or _MAX_VIDEOS) == 125


def test_storage_stats():
    from backend.services.super_encoder_service import get_storage_stats
    stats = get_storage_stats()
    assert stats["success"] is True
    assert stats["max_videos"] == 125
    assert "stored_videos" in stats
    assert "slots_remaining" in stats


def test_ai_status():
    from backend.services.super_encoder_service import get_ai_status
    status = get_ai_status()
    assert status["success"] is True
    assert "ai_routing" in status
    assert status["max_videos"] == 125


def test_rating_config():
    from backend.services.creator_rating_service import get_rating_config
    cfg = get_rating_config()
    assert cfg["success"] is True
    assert cfg["max_score"] == 5
    assert cfg["min_score"] == 1


def test_mobile_config():
    from backend.services.super_encoder_service import get_mobile_config
    mobile = get_mobile_config()
    assert mobile["success"] is True
    assert mobile["package_id"] == "dk.masternoder.creator"
    assert mobile["max_videos"] == 125


def test_music_hook_status():
    from backend.services.music_api_service import get_music_provider_status
    status = get_music_provider_status()
    assert status["success"] is True
    assert status["preferred"] in ("suno", "replicate_musicgen", "tts_fallback")
    assert "configured" in status["suno"]
    assert "missing" in status["suno"]
    assert status["fallback_chain"] == ["suno", "replicate_musicgen", "tts"]


def test_encoder_modes_count():
    from backend.services.super_encoder_service import list_encoder_modes
    catalog = list_encoder_modes()
    assert catalog["success"] is True
    assert catalog["count"] == 25
    assert len(catalog["modes"]) == 25
    ids = {m["id"] for m in catalog["modes"]}
    assert "full_mv" in ids
    assert "crypto_anthem" in ids


def test_encoder_mode_selection():
    from backend.services.super_encoder_service import get_encoder_mode, _resolve_mode_params
    mode = get_encoder_mode("lyrics_only")
    assert mode["id"] == "lyrics_only"
    assert mode["layers"]["lyrics"] is True
    assert mode["layers"]["audio"] is False
    mode, layers, duration, genre, mood = _resolve_mode_params(
        "short_reel", "Test", "", "", 60
    )
    assert mode["id"] == "short_reel"
    assert duration == 30
    assert layers["video"] is True


def test_encoder_mode_default_fallback():
    from backend.services.super_encoder_service import get_encoder_mode
    mode = get_encoder_mode(None)
    assert mode.get("id") == "full_mv"
    unknown = get_encoder_mode("nonexistent_mode_xyz")
    assert unknown.get("id") in ("full_mv", unknown.get("id"))


def test_encoder_modes_unique_ids():
    from backend.services.super_encoder_service import list_encoder_modes
    modes = list_encoder_modes()["modes"]
    ids = [m["id"] for m in modes]
    assert len(ids) == len(set(ids))
    for m in modes:
        assert m.get("label")
        assert m.get("icon")
        assert m.get("description")
        assert isinstance(m.get("layers"), dict)
