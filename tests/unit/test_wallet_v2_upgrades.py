"""Unit tests for wallet v2 upgrades catalog, progress, and unlock endpoints."""
import json
import os
from unittest.mock import patch

from flask import Flask


def _app():
    from backend.routes.wallet_v2_routes import wallet_v2_bp
    app = Flask(__name__)
    app.register_blueprint(wallet_v2_bp)
    return app


def _progress_dir():
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "data", "wallet_upgrades_progress")


def _cleanup_user_progress(user_id: str):
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
    path = os.path.join(_progress_dir(), f"{safe}.json")
    if os.path.isfile(path):
        os.remove(path)


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
@patch("backend.services.wallet_upgrades_service._user_trophy_count", return_value=0)
@patch("backend.services.wallet_upgrades_service._user_clicks_today", return_value=0)
def test_upgrades_progress_returns_unlock_counts(
    mock_clicks, mock_trophies, mock_spent, mock_ach, mock_level, mock_resolve
):
    user_id = "test_wallet_user_progress"
    mock_resolve.return_value = user_id
    _cleanup_user_progress(user_id)
    client = _app().test_client()
    r = client.get(f"/api/wallet/v2/upgrades/progress?user_id={user_id}")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("user_id") == user_id
    assert data.get("total") == 250
    assert data.get("unlocked_count", 0) == 0
    assert data.get("available_count", 0) >= 10
    assert "WR-UPG-001" in (data.get("available_ids") or [])
    assert "unlocked_ids" in data
    assert "available_ids" in data
    assert "effects_summary" in data
    assert "by_category" in data
    _cleanup_user_progress(user_id)


@patch("backend.routes.wallet_v2_routes.resolve_user_id")
@patch("backend.services.wallet_upgrades_service._user_wallet_level", return_value=1)
@patch("backend.services.wallet_upgrades_service._user_achievements", return_value=set())
@patch("backend.services.wallet_upgrades_service._user_mn2_spent", return_value=0.0)
@patch("backend.services.wallet_upgrades_service._user_trophy_count", return_value=0)
@patch("backend.services.wallet_upgrades_service._user_clicks_today", return_value=0)
def test_unlock_success_persists(
    mock_clicks, mock_trophies, mock_spent, mock_ach, mock_level, mock_resolve
):
    user_id = "test_wallet_user_unlock_ok"
    mock_resolve.return_value = user_id
    _cleanup_user_progress(user_id)
    client = _app().test_client()
    r = client.post(
        "/api/wallet/v2/upgrades/unlock",
        json={"upgrade_id": "WR-UPG-001"},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("upgrade_id") == "WR-UPG-001"
    assert data.get("effects", {}).get("summary_cache_ttl_bonus") == 15
    prog = data.get("progress") or {}
    assert "WR-UPG-001" in (prog.get("unlocked_ids") or [])

    r2 = client.get(f"/api/wallet/v2/upgrades/progress?user_id={user_id}")
    data2 = r2.get_json()
    assert "WR-UPG-001" in (data2.get("unlocked_ids") or [])
    assert data2.get("unlocked_count") == 1
    _cleanup_user_progress(user_id)


@patch("backend.routes.wallet_v2_routes.resolve_user_id")
@patch("backend.services.wallet_upgrades_service._user_wallet_level", return_value=1)
@patch("backend.services.wallet_upgrades_service._user_achievements", return_value=set())
@patch("backend.services.wallet_upgrades_service._user_mn2_spent", return_value=0.0)
@patch("backend.services.wallet_upgrades_service._user_trophy_count", return_value=0)
@patch("backend.services.wallet_upgrades_service._user_clicks_today", return_value=0)
def test_unlock_denied_when_conditions_not_met(
    mock_clicks, mock_trophies, mock_spent, mock_ach, mock_level, mock_resolve
):
    user_id = "test_wallet_user_unlock_denied"
    mock_resolve.return_value = user_id
    _cleanup_user_progress(user_id)
    client = _app().test_client()
    r = client.post(
        "/api/wallet/v2/upgrades/unlock",
        json={"upgrade_id": "WR-UPG-011"},
    )
    assert r.status_code == 400
    data = r.get_json()
    assert data.get("success") is False
    assert data.get("error") == "conditions_not_met"
    assert data.get("upgrade_id") == "WR-UPG-011"
    _cleanup_user_progress(user_id)


@patch("backend.routes.wallet_v2_routes.resolve_user_id")
@patch("backend.services.wallet_upgrades_service._user_wallet_level", return_value=1)
@patch("backend.services.wallet_upgrades_service._user_achievements", return_value=set())
@patch("backend.services.wallet_upgrades_service._user_mn2_spent", return_value=0.0)
@patch("backend.services.wallet_upgrades_service._user_trophy_count", return_value=0)
@patch("backend.services.wallet_upgrades_service._user_clicks_today", return_value=0)
def test_unlock_duplicate_rejected(
    mock_clicks, mock_trophies, mock_spent, mock_ach, mock_level, mock_resolve
):
    user_id = "test_wallet_user_unlock_dup"
    mock_resolve.return_value = user_id
    _cleanup_user_progress(user_id)
    client = _app().test_client()
    r1 = client.post(
        "/api/wallet/v2/upgrades/unlock",
        json={"upgrade_id": "WR-UPG-002"},
    )
    assert r1.status_code == 200
    r2 = client.post(
        "/api/wallet/v2/upgrades/unlock",
        json={"upgrade_id": "WR-UPG-002"},
    )
    assert r2.status_code == 400
    data = r2.get_json()
    assert data.get("success") is False
    assert data.get("error") == "already_unlocked"
    _cleanup_user_progress(user_id)


def test_unlock_condition_types_supported():
    from backend.services.wallet_upgrades_service import _check_unlock_condition

    ctx = {
        "level": 2,
        "achievements": set(),
        "mn2_spent": 10.0,
        "trophy_count": 3,
        "clicks_today": 7,
        "upgrade_count": 5,
    }
    assert _check_unlock_condition({"type": "always", "value": 0}, ctx)[0] is True
    assert _check_unlock_condition({"type": "default", "value": 0}, ctx)[0] is True
    assert _check_unlock_condition({"type": "level", "value": 3}, ctx)[0] is False
    assert _check_unlock_condition({"type": "level", "value": 2}, ctx)[0] is True
    assert _check_unlock_condition({"type": "upgrade_count", "value": 6}, ctx)[0] is False
    assert _check_unlock_condition({"type": "upgrade_count", "value": 5}, ctx)[0] is True
    assert _check_unlock_condition({"type": "clicks_today", "value": 8}, ctx)[0] is False
    assert _check_unlock_condition({"type": "clicks_today", "value": 7}, ctx)[0] is True
    assert _check_unlock_condition({"type": "trophy_count", "value": 4}, ctx)[0] is False
    assert _check_unlock_condition({"type": "trophy_count", "value": 3}, ctx)[0] is True
    assert _check_unlock_condition({"type": "mn2_spent", "value": 25}, ctx)[0] is False
    assert _check_unlock_condition({"type": "mn2_spent", "value": 10}, ctx)[0] is True


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
