"""Tests for compendium milestone + M8 promo rotator."""
import os
import shutil
import pytest


def test_promo_rotator(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    from backend.services.discord_m8_streams import promo_rotator_payload

    r = promo_rotator_payload()
    assert r.get("success") is True
    assert r.get("promo", {}).get("code") in {
        "DISCORD-STARTER", "HOSTMN5", "MARKET-BONUS", "GENERATE10",
    }


def test_affiliate_rotator_includes_shop_promo_hint(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    from backend.services import discord_m8_streams as m8

    monkeypatch.setattr(m8, "_AFFILIATE_ROTATION", [{"id": "shop", "label": "Shop boosters", "path": "/shop/"}])
    r = m8.affiliate_rotator_payload()
    assert r.get("success") is True
    assert r.get("link", {}).get("id") == "shop"


def test_promo_for_affiliate_link():
    from backend.services.discord_m8_streams import _promo_for_affiliate_link

    assert "DISCORD-STARTER" in _promo_for_affiliate_link("shop")
    assert "HOSTMN5" in _promo_for_affiliate_link("shop")
    assert _promo_for_affiliate_link("unknown") == ""


def test_compendium_milestone_idempotent(monkeypatch):
    from backend.services import compendium_milestone_service as cms
    from backend.services import user_engagement as ue

    base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".pytest-tmp", "compendium-milestone", "user_engagement")
    if os.path.isdir(base):
        shutil.rmtree(base, ignore_errors=True)
    os.makedirs(base, exist_ok=True)
    monkeypatch.setattr(ue, "_ENG_DIR", base)

    monkeypatch.setattr(
        "backend.services.platform_news_publish.publish",
        lambda **kw: {"success": True, "item": kw},
    )
    monkeypatch.setattr(
        "backend.services.discord_service.post_message",
        lambda *a, **k: {"success": True},
    )
    monkeypatch.setattr("backend.services.activity_events_service.emit", lambda *a, **k: None)
    monkeypatch.setattr(
        "backend.services.game_mn2_rewards.credit_mn2",
        lambda *a, **k: {"success": True, "amount": 0.01},
    )

    r1 = cms.maybe_celebrate_complete("reader_a", total_read=25, total_pages=25)
    assert r1.get("celebrated") is True
    r2 = cms.maybe_celebrate_complete("reader_a", total_read=25, total_pages=25)
    assert r2.get("celebrated") is False
