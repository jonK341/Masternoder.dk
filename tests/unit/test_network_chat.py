"""Unit tests for wallet v2 network chat."""
import os
from unittest.mock import patch

from flask import Flask


def _app():
    from backend.routes.wallet_v2_routes import wallet_v2_bp
    app = Flask(__name__)
    app.register_blueprint(wallet_v2_bp)
    return app


def _base():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _cleanup_chat_files():
    for name in (
        "network_chat_messages.jsonl",
        "network_chat_presence.json",
        "network_chat_rewards_state.json",
    ):
        path = os.path.join(_base(), "data", name)
        if os.path.isfile(path):
            os.remove(path)


@patch("backend.routes.wallet_v2_routes.resolve_user_id")
def test_network_chat_status(mock_resolve):
    mock_resolve.return_value = "test_chat_user"
    client = _app().test_client()
    r = client.get("/api/wallet/v2/network-chat/status?user_id=test_chat_user")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("enabled") is True
    assert "online_users" in data
    assert data.get("online_count", 0) >= 1
    assert "rewards" in data


@patch("backend.routes.wallet_v2_routes.resolve_user_id")
@patch("backend.services.network_chat_service._credit_reward")
def test_network_chat_post_message(mock_credit, mock_resolve):
    mock_resolve.return_value = "test_chat_post_user"
    mock_credit.return_value = {"success": True, "mn2_awarded": 0.001}
    _cleanup_chat_files()
    client = _app().test_client()
    r = client.post(
        "/api/wallet/v2/network-chat/message",
        json={"text": "Hello network!", "display_name": "Tester"},
        query_string={"user_id": "test_chat_post_user"},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data["message"].get("text") == "Hello network!"
    _cleanup_chat_files()


@patch("backend.routes.wallet_v2_routes.resolve_user_id")
def test_network_chat_guest_cannot_post(mock_resolve):
    mock_resolve.return_value = "guest"
    client = _app().test_client()
    r = client.post(
        "/api/wallet/v2/network-chat/message",
        json={"text": "nope"},
    )
    assert r.status_code == 400
    data = r.get_json()
    assert data.get("success") is False


@patch("backend.routes.wallet_v2_routes.resolve_user_id")
@patch("backend.services.network_chat_service._credit_reward")
def test_network_chat_rating(mock_credit, mock_resolve):
    mock_resolve.return_value = "test_chat_rate_user"
    mock_credit.return_value = {"success": True, "mn2_awarded": 0.0005}
    _cleanup_chat_files()
    client = _app().test_client()
    post = client.post(
        "/api/wallet/v2/network-chat/message",
        json={"text": "Rate me"},
        query_string={"user_id": "test_chat_rate_user"},
    )
    msg_id = post.get_json()["message"]["id"]
    r = client.post(
        "/api/wallet/v2/network-chat/rating",
        json={"message_id": msg_id, "stars": 5},
        query_string={"user_id": "test_chat_rate_user"},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data["message"].get("rating_count") == 1
    _cleanup_chat_files()


@patch("backend.routes.wallet_v2_routes.resolve_user_id")
def test_network_chat_heartbeat(mock_resolve):
    mock_resolve.return_value = "test_chat_hb_user"
    client = _app().test_client()
    r = client.post(
        "/api/wallet/v2/network-chat/heartbeat",
        json={"display_name": "HB User"},
        query_string={"user_id": "test_chat_hb_user"},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
