"""Tier C5 — compendium paid chapters."""
import os
import shutil

import pytest


@pytest.fixture
def compendium_user(monkeypatch):
    base = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        ".pytest-tmp",
        "compendium-access",
        "user_engagement",
    )
    if os.path.isdir(base):
        shutil.rmtree(base, ignore_errors=True)
    os.makedirs(base, exist_ok=True)
    import backend.services.user_engagement as ue

    monkeypatch.setattr(ue, "_ENG_DIR", base)
    return "reader_c5"


def test_free_pages_no_unlock(compendium_user):
    from backend.services.compendium_access_service import can_access_page, get_access_status

    assert can_access_page(compendium_user, 1) is True
    assert can_access_page(compendium_user, 3) is True
    assert can_access_page(compendium_user, 4) is False
    st = get_access_status(compendium_user)
    assert 1 in st["unlocked_pages"]
    assert 4 in st["locked_pages"]


def test_volume_and_full_unlock(compendium_user):
    from backend.services.compendium_access_service import (
        TIER_FULL,
        TIER_VOLUME,
        can_access_page,
        grant_compendium_tier,
    )

    grant_compendium_tier(compendium_user, TIER_VOLUME)
    assert can_access_page(compendium_user, 10) is True
    assert can_access_page(compendium_user, 15) is False

    grant_compendium_tier(compendium_user, TIER_FULL)
    assert can_access_page(compendium_user, 25) is True


def test_milestone_progress_hooks(compendium_user, monkeypatch):
    from backend.services import compendium_milestone_service as cms
    from backend.services import user_engagement as ue

    monkeypatch.setattr(
        "backend.services.platform_news_publish.publish",
        lambda **kw: {"success": True},
    )
    monkeypatch.setattr(
        "backend.services.discord_service.post_message",
        lambda *a, **k: {"success": True},
    )
    monkeypatch.setattr("backend.services.activity_events_service.emit", lambda *a, **k: None)
    monkeypatch.setattr(
        "backend.services.game_mn2_rewards.credit_mn2",
        lambda *a, **k: {"success": True},
    )

    r = cms.maybe_celebrate_threshold(compendium_user, 3, total_read=3)
    assert r.get("celebrated") is True
    r2 = cms.maybe_celebrate_threshold(compendium_user, 3, total_read=3)
    assert r2.get("celebrated") is False

    ue.record_compendium_page(compendium_user, 1)
    ue.record_compendium_page(compendium_user, 2)
    ue.record_compendium_page(compendium_user, 3)
    data = ue._load(compendium_user, "compendium_pages.json")
    assert 3 in (data.get("milestones_celebrated") or [])


def test_compendium_view_blocks_premium(compendium_user):
    from backend.routes.compendium_routes import compendium_bp
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(compendium_bp)
    client = app.test_client()
    r = client.post(
        "/api/compendium/view",
        json={"user_id": compendium_user, "page_number": 5},
    )
    assert r.status_code == 403
    data = r.get_json()
    assert data.get("error") == "premium_required"
