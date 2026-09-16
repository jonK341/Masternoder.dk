"""Unit tests for GET /api/wallet/v2/casino/snapshot (WR-CASINO-1)."""
from unittest.mock import patch

from flask import Flask


def _app():
    from backend.routes.wallet_v2_routes import wallet_v2_bp

    app = Flask(__name__)
    app.register_blueprint(wallet_v2_bp)
    return app


@patch("backend.routes.wallet_v2_routes.build_casino_snapshot")
@patch("backend.routes.wallet_v2_routes.resolve_user_id")
def test_casino_snapshot_route(mock_resolve, mock_build):
    mock_resolve.return_value = "casino-player"
    mock_build.return_value = {
        "success": True,
        "user_id": "casino-player",
        "casino_url": "/casino/",
        "mn2_balance": 12.5,
        "featured_games_count": 3,
    }
    client = _app().test_client()
    r = client.get("/api/wallet/v2/casino/snapshot?user_id=casino-player")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("casino_url") == "/casino/"
    assert data.get("featured_games_count") == 3
    mock_build.assert_called_once_with("casino-player")


@patch("backend.services.discord_link_service.link_status")
@patch("backend.services.casino_service.get_vip_lounge")
@patch("backend.services.casino_service.get_balance")
@patch("backend.services.casino_service.get_public_config")
def test_build_casino_snapshot_user(mock_config, mock_balance, mock_vip, mock_link):
    mock_balance.return_value = {
        "success": True,
        "mn2_balance": 150.0,
        "balance": 4200,
        "fiat_balance": 5.0,
        "featured_games": [
            {"id": "crash", "label": "Crash", "icon": "🚀", "tag": "Hot"},
            {"id": "plinko", "label": "Plinko", "icon": "🟡"},
        ],
        "disclaimer": "Play for fun — set your limits.",
        "real_money": {"enabled": True},
    }
    mock_config.return_value = {"featured_games": []}
    mock_vip.return_value = {
        "enabled": True,
        "unlocked": True,
        "level": 7,
        "vip_tier": "gold",
        "user_xp": 8000,
        "xp_to_unlock": 0,
        "title": "VIP Lounge",
    }
    mock_link.return_value = {
        "linked": True,
        "casino_vip_eligible": True,
        "min_mn2_for_vip": 100,
    }

    from backend.services.wallet_v2_service import build_casino_snapshot

    data = build_casino_snapshot("vip-user")

    assert data["success"] is True
    assert data["guest"] is False
    assert data["casino_url"] == "/casino/"
    assert data["mn2_balance"] == 150.0
    assert data["casino_coins"] == 4200
    assert data["featured_games_count"] == 2
    assert len(data["featured_games"]) == 2
    assert data["vip"]["unlocked"] is True
    assert data["discord_vip_eligible"] is True
    assert data["responsible_gaming_disclaimer"] == "Play for fun — set your limits."
    assert data["real_money_enabled"] is True


def test_build_casino_snapshot_guest():
    from backend.services.wallet_v2_service import build_casino_snapshot

    with patch("backend.services.casino_service.get_balance") as mock_balance:
        mock_balance.return_value = {
            "success": True,
            "mn2_balance": 0,
            "balance": 0,
            "fiat_balance": 0,
            "featured_games": [{"id": "slots", "label": "Slots"}],
        }
        with patch("backend.services.casino_service.get_vip_lounge") as mock_vip:
            mock_vip.return_value = {"enabled": True, "unlocked": False}
            data = build_casino_snapshot("default_user")

    assert data["guest"] is True
    assert "message" in data
    assert data["discord_vip_eligible"] is False


def test_site_features_casino_primary():
    from backend.services.wallet_v2_service import build_site_features

    data = build_site_features()
    casino = next(f for f in data["features"] if f["id"] == "casino")
    assert casino.get("primary") is True
    assert casino.get("path") == "/casino/"
    assert "casino" in data["primary_ids"]
