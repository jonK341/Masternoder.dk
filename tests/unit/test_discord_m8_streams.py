"""M8 Discord stream tests."""
import pytest


def test_support_faq_deposit():
    from backend.services.discord_m8_streams import support_faq_answer

    r = support_faq_answer("how do I deposit mn2")
    assert r.get("success") is True
    assert "deposit" in r.get("answer", "").lower() or r.get("topic") == "deposit"


def test_support_faq_market():
    from backend.services.discord_m8_streams import support_faq_answer

    r = support_faq_answer("market order book")
    assert r.get("success") is True
    assert r.get("topic") == "market" or "market" in r.get("answer", "").lower()


def test_affiliate_rotator(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    from backend.services.discord_m8_streams import affiliate_rotator_payload

    r = affiliate_rotator_payload()
    assert r.get("success") is True
    assert r.get("link", {}).get("path")


def test_quest_bot_digest(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    from backend.services.discord_m8_streams import run_quest_bot_digest

    r = run_quest_bot_digest()
    assert r.get("success") is True
    assert r.get("quests_listed", 0) >= 1


def test_partner_spotlight(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    from backend.services import discord_m8_streams as m8

    monkeypatch.setattr(
        "backend.services.platform_news_publish.publish",
        lambda **kw: {"success": True, "item": {"channel": kw.get("channel"), "title": kw.get("title")}},
    )
    r = m8.publish_partner_spotlight(title="Test Partner", summary="Great deal", href="/shop/")
    assert r.get("success") is True
    assert r.get("news", {}).get("channel") == "market"
