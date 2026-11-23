"""Growth rails: email digest prefs, push subscribe, clip export, partner codes."""
from __future__ import annotations

import json
import os

import pytest


@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    monkeypatch.setenv("OUTPUT_DIR", str(tmp_path / "output"))
    from flask import Flask
    from backend.routes.casino_routes import casino_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(casino_bp)
    return app.test_client()


def test_social_prefs_growth_flags(tmp_path, monkeypatch):
    from backend.services import casino_social_service as css

    monkeypatch.setattr(css, "_PREFS_DIR", str(tmp_path / "prefs"))
    out = css.set_preferences(
        "user_growth_1",
        email_win_digest=True,
        push_free_daily=True,
        push_jackpot=True,
        digest_email="player@example.com",
    )
    assert out["success"] is True
    prefs = css.get_preferences("user_growth_1")
    assert prefs["email_win_digest"] is True
    assert prefs["push_free_daily"] is True
    assert prefs["push_jackpot"] is True
    assert prefs["digest_email"] == "player@example.com"


def test_partner_resolve_and_stats(tmp_path, monkeypatch):
    from backend.services import casino_partner_affiliate_service as pas

    monkeypatch.setattr(pas, "_PARTNERS_PATH", str(tmp_path / "partners.json"))
    monkeypatch.setattr(pas, "_STATS_PATH", str(tmp_path / "stats.json"))
    created = pas.upsert_partner(
        code="TWITCH-NOVA",
        partner_id="nova",
        display_name="Nova",
        referrer_user_id="host_nova",
    )
    assert created["success"] is True
    resolved = pas.resolve_code("twitch-nova")
    assert resolved["kind"] == "partner"
    assert resolved["referrer_user_id"] == "host_nova"
    assert "utm_source=partner" in resolved["cta_url"]
    click = pas.track_click("TWITCH-NOVA")
    assert click["clicks"] == 1
    stats = pas.partner_stats("TWITCH-NOVA")
    assert stats["clicks"] == 1


def test_vertical_svg_and_clip_export(tmp_path, monkeypatch):
    from backend.services import casino_social_service as css
    from backend.services import casino_clip_export_service as ces

    monkeypatch.setattr(ces, "_CLIPS_DIR", str(tmp_path / "clips"))
    svg = css.build_big_win_svg(
        game="crash",
        net=5000,
        currency="coins",
        multiplier=12.5,
        handle="Player#ab12",
        aspect="vertical",
    )
    assert 'width="1080"' in svg
    assert 'height="1920"' in svg
    assert "TIKTOK" in svg

    out = ces.export_big_win_clip(
        user_id="clip_user",
        game="slots",
        net=2500,
        currency="coins",
        multiplier=8,
        handle="Player#clip",
    )
    assert out["success"] is True
    assert out["width"] == 1080
    assert out["height"] == 1920
    assert out["poster_url"]
    assert os.path.isfile(out["poster_path"])


def test_push_subscribe_and_vapid(tmp_path, monkeypatch):
    from backend.services import casino_push_service as cps

    monkeypatch.setattr(cps, "_SUBS_PATH", str(tmp_path / "subs.json"))
    monkeypatch.setattr(cps, "_VAPID_PATH", str(tmp_path / "vapid.json"))
    monkeypatch.setattr(cps, "_LOG_PATH", str(tmp_path / "push.jsonl"))
    keys = cps.get_vapid_public_key()
    assert keys["success"] is True
    assert keys["public_key"]
    sub = cps.subscribe(
        "push_user",
        {
            "endpoint": "https://example.push/endpoint",
            "keys": {"p256dh": "abc", "auth": "def"},
        },
    )
    assert sub["success"] is True
    sent = cps.send_to_user("push_user", title="Hi", body="Test")
    assert sent["attempted"] == 1


def test_digest_build_body(monkeypatch):
    from backend.services import casino_win_digest_service as dig

    monkeypatch.setattr(
        "backend.services.casino_service.get_big_win_hall_of_fame",
        lambda days=7, limit=8: {
            "wins": [{"game": "crash", "net": 1000, "currency": "coins", "display": "P1"}]
        },
    )
    monkeypatch.setattr(
        "backend.services.casino_social_service.get_referral_quests",
        lambda uid: {"referrals": [{"display": "Guest", "bet_count": 2, "tiers": []}], "party": {}},
    )
    monkeypatch.setattr(
        "backend.services.casino_social_service.get_referral_invite",
        lambda uid: {
            "referral_code": "MN-TEST",
            "successful_invites": 2,
            "invite_url": "https://masternoder.dk/r/MN-TEST",
            "party": {"level": {"current": {"name": "Starter"}}},
        },
    )
    body = dig.build_digest_body("digest_user")
    assert "Weekly" in body["subject"] or "digest" in body["subject"].lower()
    assert "MN-TEST" in body["body"]
    assert "crash" in body["body"].lower() or "1000" in body["body"]


def test_partner_and_clip_routes(app_client, tmp_path, monkeypatch):
    from backend.services import casino_partner_affiliate_service as pas
    from backend.services import casino_clip_export_service as ces

    monkeypatch.setattr(pas, "_PARTNERS_PATH", str(tmp_path / "partners.json"))
    monkeypatch.setattr(pas, "_STATS_PATH", str(tmp_path / "stats.json"))
    monkeypatch.setattr(ces, "_CLIPS_DIR", str(tmp_path / "clips"))
    pas.upsert_partner(
        code="YT-ACE",
        partner_id="ace",
        display_name="Ace",
        referrer_user_id="host_ace",
    )
    resp = app_client.get("/api/casino/partner/YT-ACE/stats")
    assert resp.status_code == 200
    assert resp.get_json()["partner"]["code"] == "YT-ACE"

    clip = app_client.post(
        "/api/casino/share/big-win/clip",
        json={"user_id": "u1", "game": "plinko", "net": 900, "currency": "coins", "multiplier": 5},
    )
    assert clip.status_code == 200
    data = clip.get_json()
    assert data["success"] is True
    assert data["poster_url"]
