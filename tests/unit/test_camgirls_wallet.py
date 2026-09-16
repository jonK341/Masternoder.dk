"""Unit tests for wallet v2 camgirls catalog and upgrades."""
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
    return os.path.join(base, "data", "camgirls_upgrades_progress")


def _cleanup_user_progress(user_id: str):
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
    path = os.path.join(_progress_dir(), f"{safe}.json")
    if os.path.isfile(path):
        os.remove(path)


def test_camgirls_catalog_returns_25():
    client = _app().test_client()
    r = client.get("/api/wallet/v2/camgirls/catalog")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    performers = data.get("performers") or []
    assert len(performers) == 25
    assert performers[0].get("id")
    assert performers[0].get("name")
    assert performers[0].get("wallet_sfw") is True


def test_camgirls_upgrades_returns_250():
    client = _app().test_client()
    r = client.get("/api/wallet/v2/camgirls/upgrades")
    assert r.status_code == 200
    data = r.get_json()
    upgrades = data.get("upgrades") or []
    assert len(upgrades) == 250
    assert upgrades[0].get("id") == "WR-CAM-UPG-001"


def test_camgirls_upgrades_filter_category():
    client = _app().test_client()
    r = client.get("/api/wallet/v2/camgirls/upgrades?category=studio")
    assert r.status_code == 200
    data = r.get_json()
    upgrades = data.get("upgrades") or []
    assert len(upgrades) == 30
    assert all(u.get("category") == "studio" for u in upgrades)


@patch("backend.routes.wallet_v2_routes.resolve_user_id")
@patch("backend.services.camgirls_wallet_service._user_wallet_level", return_value=5)
@patch("backend.services.camgirls_wallet_service._user_mn2_spent", return_value=0.0)
@patch("backend.services.camgirls_wallet_service._user_trophy_count", return_value=0)
def test_camgirls_upgrades_progress(mock_trophies, mock_spent, mock_level, mock_resolve):
    user_id = "test_camgirl_wallet_user"
    mock_resolve.return_value = user_id
    _cleanup_user_progress(user_id)
    client = _app().test_client()
    r = client.get(f"/api/wallet/v2/camgirls/upgrades/progress?user_id={user_id}")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("total") == 250
    assert data.get("unlocked_count", 0) == 0
    assert "WR-CAM-UPG-001" in (data.get("available_ids") or [])
    _cleanup_user_progress(user_id)


@patch("backend.routes.wallet_v2_routes.resolve_user_id")
@patch("backend.services.camgirls_wallet_service._user_wallet_level", return_value=5)
@patch("backend.services.camgirls_wallet_service._user_mn2_spent", return_value=0.0)
@patch("backend.services.camgirls_wallet_service._user_trophy_count", return_value=0)
def test_camgirls_unlock_default_upgrade(mock_trophies, mock_spent, mock_level, mock_resolve):
    user_id = "test_camgirl_unlock_user"
    mock_resolve.return_value = user_id
    _cleanup_user_progress(user_id)
    client = _app().test_client()
    r = client.post(
        "/api/wallet/v2/camgirls/upgrades/unlock",
        json={"upgrade_id": "WR-CAM-UPG-001"},
        query_string={"user_id": user_id},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("upgrade_id") == "WR-CAM-UPG-001"
    _cleanup_user_progress(user_id)
