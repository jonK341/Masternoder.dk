"""Unit tests for GET /api/wallet/v2/trophies — wallet trophy gallery (W-U3)."""
from unittest.mock import patch

from flask import Flask


def _app():
    from backend.routes.wallet_v2_routes import wallet_v2_bp

    app = Flask(__name__)
    app.register_blueprint(wallet_v2_bp)
    return app


@patch("backend.routes.wallet_v2_routes.resolve_user_id")
def test_trophies_guest(mock_resolve):
    mock_resolve.return_value = "default_user"
    client = _app().test_client()
    r = client.get("/api/wallet/v2/trophies")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("guest") is True
    assert data.get("on_chain_mint") is False
    assert data.get("editions") == []


@patch("backend.services.shop_db_service.get_inventory")
@patch("backend.routes.wallet_v2_routes.resolve_user_id")
def test_trophies_expands_inventory(mock_resolve, mock_inv):
    mock_resolve.return_value = "collector"
    mock_inv.return_value = [
        {"item_id": "top25-01", "item_name": "Legend #1", "quantity": 2, "created_at": "2026-01-01T00:00:00Z"},
    ]
    client = _app().test_client()
    r = client.get("/api/wallet/v2/trophies?series=top25")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("on_chain_mint") is False
    assert len(data.get("editions") or []) == 2
    assert data["editions"][0]["edition_no"] == 1
    assert data["editions"][0]["edition_key"] == "top25-01#1"
    assert data["editions"][0]["legacy_stack"] is True
    assert data.get("counts", {}).get("top25_owned") == 2


@patch("backend.services.wallet_trophies_service.build_wallet_trophies")
@patch("backend.routes.wallet_v2_routes.resolve_user_id")
def test_trophies_route_delegates(mock_resolve, mock_build):
    mock_resolve.return_value = "u1"
    mock_build.return_value = {"success": True, "editions": [], "on_chain_mint": False}
    client = _app().test_client()
    r = client.get("/api/wallet/v2/trophies?series=block-mint")
    assert r.status_code == 200
    mock_build.assert_called_once_with("u1", series="block-mint")
