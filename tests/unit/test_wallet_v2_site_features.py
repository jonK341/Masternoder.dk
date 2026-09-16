"""Unit tests for wallet v2 site features and rewards snapshot endpoints."""
from unittest.mock import patch

from flask import Flask


def _app():
    from backend.routes.wallet_v2_routes import wallet_v2_bp
    app = Flask(__name__)
    app.register_blueprint(wallet_v2_bp)
    return app


def test_site_features_returns_matrix():
    client = _app().test_client()
    r = client.get("/api/wallet/v2/site-features")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    features = data.get("features") or []
    assert len(features) >= 30
    primary = [f for f in features if f.get("primary")]
    assert len(primary) >= 2
    ids = {f.get("id") for f in features}
    assert "portal" in ids
    assert "rewards" in ids
    assert "shop" in ids
    assert "exchange" in ids
    portal = next(f for f in features if f.get("id") == "portal")
    assert portal.get("path") == "/command-center"


@patch("backend.routes.wallet_v2_routes.resolve_user_id")
def test_rewards_snapshot_guest(mock_resolve):
    mock_resolve.return_value = "default_user"
    client = _app().test_client()
    r = client.get("/api/wallet/v2/rewards/snapshot")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("guest") is True


@patch("backend.routes.wallet_v2_routes.resolve_user_id")
def test_rewards_snapshot_user(mock_resolve):
    mock_resolve.return_value = "test_wallet_user"
    client = _app().test_client()
    with patch(
        "backend.services.unified_points_database.unified_points_db"
    ) as mock_db:
        mock_db.get_all_points.return_value = {
            "success": True,
            "points": {
                "xp_total": 1200,
                "level": 5,
                "coins": 42,
                "trophy_points": 10,
                "quest_points": 3,
                "battle_points": 7,
                "mn2_balance": 1.5,
            },
        }
        r = client.get("/api/wallet/v2/rewards/snapshot?user_id=test_wallet_user")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("guest") is False
    pts = data.get("points") or {}
    assert pts.get("level") == 5
    assert pts.get("xp_total") == 1200
