"""Fleet stream chapter composer — rotating encoded AI chapters."""
import base64

from backend.services.fleet_stream_composer_service import (
    apply_template,
    chapter_public_view,
    decode_chapter_content,
    list_chapters_public,
    rotation_index,
)


def test_rotation_index_wraps():
    assert rotation_index(6, rotate_sec=75, at_ts=0) == 0
    assert rotation_index(6, rotate_sec=75, at_ts=75) == 1


def test_decode_and_template():
    ch = {
        "id": "t",
        "title": "Test",
        "content_b64": base64.b64encode(b"Level {commander_level} ok").decode(),
    }
    view = chapter_public_view(ch, fleet_snapshot={"progression": {"commander_level": 5}})
    assert view["ai_content"] == "Level 5 ok"
    assert view["encoded"] is True


def test_list_chapters_public_count():
    out = list_chapters_public(None, stream_mode=True)
    assert out["success"] is True
    assert out["chapter_count"] >= 6
    assert out["current"] and out["current"].get("title")
