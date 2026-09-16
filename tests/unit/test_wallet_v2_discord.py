"""Unit tests for GET /api/wallet/v2/discord/status."""
from unittest.mock import patch

from flask import Flask


def _app():
    from backend.routes.wallet_v2_routes import wallet_v2_bp

    app = Flask(__name__)
    app.register_blueprint(wallet_v2_bp)
    return app


@patch("backend.routes.wallet_v2_routes.build_discord_status")
@patch("backend.routes.wallet_v2_routes.resolve_user_id")
def test_discord_status_guest(mock_resolve, mock_build):
    mock_resolve.return_value = "default_user"
    mock_build.return_value = {
        "success": True,
        "user_id": "default_user",
        "guest": True,
        "linked": False,
    }
    client = _app().test_client()
    r = client.get("/api/wallet/v2/discord/status")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("guest") is True
    mock_build.assert_called_once_with("default_user")


@patch("backend.services.discord_link_service.link_status")
@patch("backend.services.wallet_v2_service._discord_profile_from_user")
@patch("backend.services.wallet_v2_service._discord_invite_url")
def test_build_discord_status_linked_user(mock_invite, mock_profile, mock_link):
    mock_invite.return_value = "https://discord.gg/masternoder"
    mock_profile.return_value = {"username": "tester", "avatar_url": "https://cdn.discordapp.com/a.png"}
    mock_link.return_value = {
        "success": True,
        "linked": True,
        "discord_id": "123456789",
        "mn2_balance": 150.0,
        "casino_vip_eligible": True,
        "min_mn2_for_vip": 100,
        "hosting_customer": False,
        "hosting_vip_eligible": False,
    }

    with patch("backend.services.discord_linked_roles_service.configured", return_value=False):
        with patch("backend.services.discord_linked_roles_service.build_metadata_for_user", return_value={"account_linked": 1}):
            from backend.services.wallet_v2_service import build_discord_status

            data = build_discord_status("wallet-user")

    assert data["success"] is True
    assert data["linked"] is True
    assert data["discord_id"] == "123456789"
    assert data["server_invite_url"] == "https://discord.gg/masternoder"
    assert "casino_vip" in data["roles_available"]
    assert data["username"] == "tester"
