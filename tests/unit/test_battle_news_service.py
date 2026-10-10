"""Battle game channel news (M8 #56)."""
from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_notify_quick_battle_win_publishes(tmp_path, monkeypatch):
    news_path = tmp_path / "platform_news.json"
    news_path.write_text(json.dumps({"items": []}), encoding="utf-8")
    monkeypatch.setattr(
        "backend.services.platform_news_publish._NEWS",
        str(news_path),
    )
    monkeypatch.setattr(
        "backend.services.battle_news_service._discord_game",
        lambda *a, **k: None,
    )
    from backend.services.battle_news_service import notify_quick_battle

    out = notify_quick_battle("user-abc", "win", points_delta=10, streak=1)
    assert out.get("success") is True
    data = json.loads(news_path.read_text(encoding="utf-8"))
    assert data["items"][0]["channel"] == "game"


def test_notify_quick_battle_loss_skipped():
    from backend.services.battle_news_service import notify_quick_battle

    out = notify_quick_battle("user-abc", "loss", points_delta=-3, streak=0)
    assert out.get("skipped") is True
