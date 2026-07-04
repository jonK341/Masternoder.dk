import json
from unittest.mock import patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _app(tmp_path, monkeypatch):
    from flask import Flask
    import backend.services.casino_service as casino
    from backend.routes.casino_routes import casino_bp

    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    cfg = tmp_path / "casino_config.json"
    cfg.write_text(
        json.dumps({
            "currency": "coins",
            "social_links": [{"id": "discord", "label": "Discord", "url": "https://discord.gg/test", "type": "follow"}],
            "mobile": {"package_id": "dk.masternoder.casino", "play_store_url": "https://play.google.com/store/apps/details?id=dk.masternoder.casino"},
            "discord_integration": {"invite_url": "https://discord.gg/test", "earn_coins_join": 25},
            "facebook": {"page_url": "https://facebook.com/MasterNoder", "og_image": "/static/img/casino/og-share.svg"},
            "social": {"default_share_text": "Test casino share"},
            "min_bet": 5,
            "max_bet": 500,
            "max_bets_per_day": 50,
            "games": {"coin_flip": {"label": "Coin flip", "payout_multiplier": 1.9, "choices": ["heads", "tails"]}},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(casino, "_CONFIG_PATH", str(cfg))
    monkeypatch.setattr("backend.services.casino_social_service._load_casino_config", lambda: json.loads(cfg.read_text(encoding="utf-8")))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(casino_bp)
    return app


def test_casino_mobile_config_route(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with app.test_client() as client:
        resp = client.get("/api/casino/mobile/config")
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["package_id"] == "dk.masternoder.casino"
    assert "manifest_url" in data
    assert data["twa_app_param"] == "casino-twa"


def test_casino_social_links_route(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with app.test_client() as client:
        resp = client.get("/api/casino/social/links")
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert len(data["follow_links"]) >= 1
    assert data["discord"]["earn_coins_join"] == 25
    assert "facebook" in data["facebook"]["page_url"]
    assert data["facebook"]["pixel_id_env"] == "META_PIXEL_ID"
    assert data["facebook"]["pixel_id"] is None


def test_casino_social_links_exposes_pixel_when_env_set(tmp_path, monkeypatch):
    monkeypatch.setenv("META_PIXEL_ID", "123456789012345")
    app = _app(tmp_path, monkeypatch)
    with app.test_client() as client:
        resp = client.get("/api/casino/social/links")
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["facebook"]["pixel_id"] == "123456789012345"


def test_casino_share_big_win_route(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with app.test_client() as client:
        resp = client.post(
            "/api/casino/share/big-win",
            json={"user_id": "player-1", "game": "crash", "net": 1500, "currency": "coins", "multiplier": 5.2},
        )
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["card"]["game"] == "crash"
    assert "facebook" in data["share_urls"]
    assert "share=big-win" in data["card"]["share_url"]


def test_casino_discord_notify_requires_ops(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    monkeypatch.delenv("DISCORD_OPS_SECRET", raising=False)
    with app.test_client() as client:
        resp = client.post("/api/casino/discord/notify", json={})
    assert resp.status_code == 403


def test_casino_discord_notify_fanout(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    monkeypatch.setenv("DISCORD_OPS_SECRET", "test-secret")
    with app.test_client() as client:
        with patch("backend.services.casino_discord_fanout.run_fanout", return_value={"success": True, "posted": 0}) as fanout:
            resp = client.post(
                "/api/casino/discord/notify",
                json={},
                headers={"X-Ops-Secret": "test-secret"},
            )
    assert resp.status_code == 200
    fanout.assert_called_once()


def test_casino_discord_fanout_jackpot_always_posts(tmp_path, monkeypatch):
    events = tmp_path / "activity_events.jsonl"
    cursor = tmp_path / "cursor.json"
    events.write_text(
        json.dumps({
            "ts": "2026-05-18T12:00:00Z",
            "type": "casino_jackpot_win",
            "channel": "casino",
            "user_id": "u1",
            "payload": {
                "share_ok": False,
                "anonymized": "Player#abcd",
                "amount": 5000,
                "currency": "coins",
                "reason": "must_drop",
            },
        }) + "\n",
        encoding="utf-8",
    )

    from backend.services import casino_discord_fanout
    monkeypatch.setattr(casino_discord_fanout, "_EVENTS", str(events))
    monkeypatch.setattr(casino_discord_fanout, "_CURSOR", str(cursor))

    with patch("backend.services.discord_service.post_message", return_value={"success": True}) as post:
        result = casino_discord_fanout.run_fanout()

    assert result["posted"] == 1
    post.assert_called_once()
    assert post.call_args[0][0] == "casino"


def test_build_big_win_share_service():
    from backend.services.casino_social_service import build_big_win_share

    card = build_big_win_share("user-secret", game="plinko", net=200, currency="coins", multiplier=4.0)
    assert card["success"] is True
    assert card["card"]["handle"].startswith("Player#")
    assert "plinko" in card["card"]["share_url"]
    assert "whatsapp" in card["share_urls"]
    assert card.get("thread_share", {}).get("lines")


def _patch_social_state(tmp_path, monkeypatch):
    import backend.services.casino_social_service as css
    state = tmp_path / "casino_social"
    state.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(css, "_SOCIAL_STATE_DIR", str(state))
    monkeypatch.setattr(css, "_FOLLOWS_PATH", str(state / "follows.json"))
    monkeypatch.setattr(css, "_REACTIONS_PATH", str(state / "feed_reactions.json"))
    monkeypatch.setattr(css, "_CASINO_REFERRALS_PATH", str(state / "casino_referrals.json"))


def test_casino_referral_invite_route(tmp_path, monkeypatch):
    _patch_social_state(tmp_path, monkeypatch)
    app = _app(tmp_path, monkeypatch)
    with app.test_client() as client:
        resp = client.get("/api/casino/social/referral?user_id=player-ref")
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert data["referral_code"].startswith("MN-")
    assert "ref=" in data["invite_url"]
    assert "whatsapp_url" in data


def test_casino_referral_register_route(tmp_path, monkeypatch):
    _patch_social_state(tmp_path, monkeypatch)
    app = _app(tmp_path, monkeypatch)
    with app.test_client() as client:
        inviter = client.get("/api/casino/social/referral?user_id=referrer-a").get_json()
        code = inviter["referral_code"]
        reg = client.post(
            "/api/casino/social/referral/register",
            json={"user_id": "new-player", "referral_code": code},
        )
    data = reg.get_json()
    assert reg.status_code == 200
    assert data["success"] is True
    assert data["referral"]["referrer_user_id"] == "referrer-a"


def test_casino_follow_player_route(tmp_path, monkeypatch):
    _patch_social_state(tmp_path, monkeypatch)
    app = _app(tmp_path, monkeypatch)
    with app.test_client() as client:
        follow = client.post(
            "/api/casino/social/follow",
            json={"user_id": "viewer-1", "target_user_id": "top-player-2"},
        )
    data = follow.get_json()
    assert follow.status_code == 200
    assert data["success"] is True
    assert data["following"] is True


def test_casino_feed_reactions_route(tmp_path, monkeypatch):
    _patch_social_state(tmp_path, monkeypatch)
    app = _app(tmp_path, monkeypatch)
    with app.test_client() as client:
        react = client.post(
            "/api/casino/social/feed/reactions",
            json={"user_id": "u1", "item_id": "bet-abc", "reaction": "fire"},
        )
        get_r = client.get("/api/casino/social/feed/reactions?item_ids=bet-abc")
    assert react.status_code == 200
    assert react.get_json()["success"] is True
    assert get_r.get_json()["reactions"]["bet-abc"]["fire"] >= 1


def test_casino_crew_challenge_hook_route(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with app.test_client() as client:
        resp = client.get("/api/casino/social/crew-challenge?user_id=solo-player")
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["success"] is True
    assert "compete_tab_hint" in data
