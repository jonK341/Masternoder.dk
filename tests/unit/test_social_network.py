import json
import tempfile
from pathlib import Path

import pytest
from flask import Flask


@pytest.fixture
def social_app(monkeypatch):
    import backend.routes.social_routes as social_routes

    with tempfile.TemporaryDirectory(prefix="social_tests_") as temp_dir:
        base = Path(temp_dir)
        social_path = base / "social_structure.json"
        networks_path = base / "social_networks.json"
        networks_path.write_text(
            json.dumps({
                "share_base_url": "https://example.test",
                "default_share_text": "Share MasterNoder",
                "default_share_hashtags": "MasterNoder,HuntersGame",
                "networks": [
                    {
                        "id": "x",
                        "name": "X",
                        "icon": "X",
                        "color": "#000000",
                        "share_url": "https://twitter.com/intent/tweet?text={text}&url={url}",
                        "encode_text": True,
                    }
                ],
            }),
            encoding="utf-8",
        )

        monkeypatch.setattr(social_routes, "SOCIAL_DATA_PATH", str(social_path))
        monkeypatch.setattr(social_routes, "SOCIAL_NETWORKS_PATH", str(networks_path))
        monkeypatch.setattr(
            social_routes,
            "_award_social_mn2",
            lambda user_id, amount, metadata: {"success": True, "user_id": user_id, "amount": amount},
        )
        synced_profiles = {}

        def fake_sync(user_id, scan):
            synced_profiles[user_id] = scan
            return {"success": True, "user_id": user_id}

        monkeypatch.setattr(social_routes, "_sync_social_appearance_to_profile", fake_sync)
        monkeypatch.setattr(
            social_routes,
            "_member_game_signals",
            lambda user_id: {
                "xp_total": 200 if user_id == "captain" else 100,
                "game_points": 50 if user_id == "captain" else 25,
                "battle_wins": 2 if user_id == "captain" else 1,
                "starmap_secured": 1,
            },
        )
        app_synced_profiles = synced_profiles

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.register_blueprint(social_routes.social_bp)
        app.synced_profiles = app_synced_profiles
        yield app


def test_friends_add_is_mutual_and_summary_counts_friend(social_app):
    client = social_app.test_client()

    add_res = client.post("/api/social/friends/add", json={"user_id": "u1", "friend_id": "u2"})
    assert add_res.status_code == 200
    assert add_res.get_json()["success"] is True

    friends_res = client.get("/api/social/friends?user_id=u2")
    payload = friends_res.get_json()
    assert payload["success"] is True
    assert [friend["user_id"] for friend in payload["friends"]] == ["u1"]

    summary_res = client.get("/api/social/summary?user_id=u1")
    assert summary_res.get_json()["friends_count"] == 1


def test_social_networks_endpoint_uses_configured_share_targets(social_app):
    client = social_app.test_client()

    res = client.get("/api/social/networks")
    payload = res.get_json()

    assert res.status_code == 200
    assert payload["success"] is True
    assert payload["default_share_text"] == "Share MasterNoder"
    assert payload["networks"][0]["share_url"].endswith("text={text}&url={url}")


def test_google_oauth_provider_reads_env_names(monkeypatch):
    import backend.services.social_auth_service as social_auth_service

    monkeypatch.setenv("SOCIAL_AUTH_BASE_URL", "https://example.test")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "google-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "google-secret")

    google = social_auth_service._provider_defs()["google"]

    assert google["client_id"] == "google-client"
    assert google["client_secret"] == "google-secret"
    assert google["scope"] == "openid email profile"
    assert google["redirect_uri"] == "https://example.test/api/auth/google/callback"


def test_social_rewards_referrals_chat_and_monitor(social_app):
    client = social_app.test_client()

    reward_status = client.get("/api/social/rewards/status?user_id=referrer").get_json()
    assert reward_status["success"] is True
    referral_code = reward_status["referral_code"]

    referral_res = client.post(
        "/api/social/referrals/register",
        json={"user_id": "new_user", "referral_code": referral_code},
    )
    assert referral_res.status_code == 200
    assert referral_res.get_json()["success"] is True

    chat_res = client.post(
        "/api/social/chat/send",
        json={"user_id": "new_user", "message": "Hello social network"},
    )
    assert chat_res.status_code == 200
    assert chat_res.get_json()["message"]["room"] == "social"

    claim_res = client.post(
        "/api/social/rewards/claim",
        json={"user_id": "new_user", "option_id": "signup_signal"},
    )
    assert claim_res.status_code == 200
    assert claim_res.get_json()["claim"]["amount_mn2"] > 0

    monitor = client.get("/api/social/monitor").get_json()
    assert monitor["success"] is True
    assert monitor["totals"]["referral_signups"] == 1
    assert monitor["totals"]["chat_messages"] == 1
    assert monitor["totals"]["reward_claims"] == 1


def test_challenge_lifecycle_crew_invites_leaderboard_and_notifications(social_app):
    client = social_app.test_client()

    assert client.post("/api/social/friends/add", json={"user_id": "captain", "friend_id": "scout"}).status_code == 200
    crew_res = client.post("/api/social/crews/create", json={"user_id": "captain", "name": "Signal Crew"})
    assert crew_res.status_code == 200

    invite_res = client.post("/api/social/crews/invite", json={"user_id": "captain", "to_user_id": "scout"})
    invite = invite_res.get_json()["invite"]
    assert invite_res.status_code == 200
    assert invite["status"] == "pending"

    notifications = client.get("/api/social/notifications?user_id=scout").get_json()
    assert notifications["counts"]["crew_invites"] == 1

    accept_invite = client.post(
        "/api/social/crews/invites/respond",
        json={"user_id": "scout", "invite_id": invite["id"], "action": "accept"},
    )
    assert accept_invite.status_code == 200
    assert accept_invite.get_json()["invite"]["status"] == "accepted"

    challenge_res = client.post(
        "/api/social/challenges/send",
        json={"user_id": "captain", "to_user_id": "scout", "challenge_type": "social_race", "target": {"count": 2}},
    )
    challenge_id = challenge_res.get_json()["challenge_id"]
    assert challenge_res.status_code == 200

    accept_challenge = client.post(f"/api/social/challenges/{challenge_id}/accept", json={"user_id": "scout"})
    assert accept_challenge.status_code == 200
    assert accept_challenge.get_json()["challenge"]["status"] == "in_progress"

    progress_one = client.post(
        "/api/social/challenges/progress",
        json={"user_id": "scout", "challenge_id": challenge_id, "progress_delta": 1},
    )
    assert progress_one.get_json()["challenge"]["status"] == "in_progress"

    progress_two = client.post(
        "/api/social/challenges/progress",
        json={"user_id": "scout", "challenge_id": challenge_id, "progress_delta": 1},
    )
    assert progress_two.get_json()["challenge"]["status"] == "completed"
    assert progress_two.get_json()["challenge"]["winner_user_id"] == "scout"

    leaderboard = client.get("/api/social/crews/leaderboard").get_json()
    assert leaderboard["success"] is True
    assert leaderboard["leaderboard"][0]["name"] == "Signal Crew"
    assert leaderboard["leaderboard"][0]["completed_challenges"] == 1
    assert leaderboard["leaderboard"][0]["xp_total"] == 300
    assert leaderboard["leaderboard"][0]["battle_wins"] == 3

    monitor = client.get("/api/social/monitor").get_json()
    assert monitor["totals"]["completed_challenges"] == 1
    assert monitor["totals"]["pending_crew_invites"] == 0


def test_social_appearance_scan_syncs_to_profile(social_app):
    client = social_app.test_client()

    client.post("/api/social/friends/add", json={"user_id": "scanner_user", "friend_id": "friend_a"})
    client.post("/api/social/crews/create", json={"user_id": "scanner_user", "name": "Scanner Crew"})
    client.post("/api/social/chat/send", json={"user_id": "scanner_user", "message": "Scanning my network"})

    res = client.post(
        "/api/social/appearance/scan",
        json={"user_id": "scanner_user", "sync_profile": True},
    )
    payload = res.get_json()

    assert res.status_code == 200
    assert payload["success"] is True
    assert payload["profile_synced"] is True
    assert payload["scan"]["summary"]["friends_count"] == 1
    assert payload["scan"]["summary"]["crew"]["name"] == "Scanner Crew"
    assert payload["scan"]["summary"]["chat_messages_count"] == 1
    assert payload["scan"]["tier"] in {"emerging_node", "active_connector", "network_anchor"}
    assert social_app.synced_profiles["scanner_user"]["appearance"]["referral_code"].startswith("MN-")


def test_privacy_moderation_cooldowns_agent_and_schema(social_app):
    client = social_app.test_client()

    client.post("/api/social/friends/add", json={"user_id": "u1", "friend_id": "u2"})
    privacy = client.post(
        "/api/social/privacy",
        json={"user_id": "u2", "challenge_permissions": "none", "activity_visibility": "private"},
    ).get_json()
    assert privacy["privacy"]["challenge_permissions"] == "none"

    blocked_challenge = client.post(
        "/api/social/challenges/send",
        json={"user_id": "u1", "to_user_id": "u2"},
    )
    assert blocked_challenge.status_code == 403

    block = client.post("/api/social/moderation/block", json={"user_id": "u1", "target_user_id": "u2"}).get_json()
    assert "u2" in block["blocked_user_ids"]

    blocked_friend = client.post("/api/social/friends/add", json={"user_id": "u1", "friend_id": "u2"})
    assert blocked_friend.status_code == 403

    report = client.post(
        "/api/social/moderation/report",
        json={"user_id": "u1", "target_user_id": "u2", "reason": "spam"},
    ).get_json()
    assert report["report"]["status"] == "open"

    client.post("/api/social/chat/send", json={"user_id": "u1", "message": "cooldown proof"})
    claim_one = client.post("/api/social/rewards/claim", json={"user_id": "u1", "option_id": "chat_ping"})
    assert claim_one.status_code == 200
    claim_two = client.post("/api/social/rewards/claim", json={"user_id": "u1", "option_id": "chat_ping"})
    assert claim_two.status_code == 429

    agent_status = client.get("/api/social/agent/status?user_id=u1").get_json()
    assert agent_status["success"] is True
    assert agent_status["mutates"] is False

    recommendations = client.get("/api/social/agent/recommendations?user_id=u1").get_json()
    assert recommendations["success"] is True
    assert recommendations["mutates"] is False

    schema = client.get("/api/social/schema").get_json()
    assert schema["success"] is True
    assert any(row["name"] == "social_challenges" for row in schema["recommended_tables"])

    hidden = client.post("/api/social/activity/hide", json={"user_id": "u1", "activity_id": "missing-ok"}).get_json()
    assert "missing-ok" in hidden["hidden_activity"]
