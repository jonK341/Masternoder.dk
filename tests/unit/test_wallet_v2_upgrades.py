"""Unit tests for wallet v2 upgrades catalog and progress endpoints."""
import json
import os
from unittest.mock import patch

from flask import Flask


def _app():
    from backend.routes.wallet_v2_routes import wallet_v2_bp
    app = Flask(__name__)
    app.register_blueprint(wallet_v2_bp)
    return app


def test_upgrades_list_returns_catalog():
    client = _app().test_client()
    r = client.get("/api/wallet/v2/upgrades")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    upgrades = data.get("upgrades") or []
    assert len(upgrades) >= 250
    assert upgrades[0].get("id") == "WR-UPG-001"
    assert "category" in upgrades[0]
    assert "tier" in upgrades[0]
    assert "unlock" in upgrades[0]


def test_upgrades_list_filter_category():
    client = _app().test_client()
    r = client.get("/api/wallet/v2/upgrades?category=speed")
    assert r.status_code == 200
    data = r.get_json()
    upgrades = data.get("upgrades") or []
    assert len(upgrades) == 30
    assert all(u.get("category") == "speed" for u in upgrades)


@patch("backend.routes.wallet_v2_routes.resolve_user_id")
@patch("backend.services.wallet_upgrades_service._user_wallet_level", return_value=5)
@patch("backend.services.wallet_upgrades_service._user_achievements", return_value=set())
@patch("backend.services.wallet_upgrades_service._user_mn2_spent", return_value=0.0)
def test_upgrades_progress_returns_unlock_counts(mock_spent, mock_ach, mock_level, mock_resolve):
    mock_resolve.return_value = "test_wallet_user"
    client = _app().test_client()
    r = client.get("/api/wallet/v2/upgrades/progress?user_id=test_wallet_user")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("user_id") == "test_wallet_user"
    assert data.get("total") == 250
    assert data.get("unlocked_count", 0) >= 10
    assert "unlocked_ids" in data
    assert "by_category" in data


@patch("backend.services.mn2_explorer_data.masternodes")
def test_network_masternodes_endpoint(mock_mn):
    mock_mn.return_value = {
        "total": 3,
        "enabled": 2,
        "list": [
            {"rank": 1, "addr": "1.2.3.4:19997", "status": "ENABLED", "activetime": 100},
            {"rank": 2, "addr": "5.6.7.8:19997", "status": "POSE_BANNED", "activetime": 0},
        ],
    }
    client = _app().test_client()
    r = client.get("/api/wallet/v2/network/masternodes?limit=10")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("total") == 3
    assert data.get("enabled") == 2
    nodes = data.get("nodes") or []
    assert len(nodes) == 2
    assert nodes[0].get("online") is True
    assert nodes[1].get("online") is False


def test_catalog_file_has_250_entries():
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "data", "wallet_upgrades_catalog.json")
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    assert doc.get("total") == 250
    assert len(doc.get("upgrades") or []) == 250
