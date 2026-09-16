"""Unit tests for GET /api/wallet/v2/summary — no deposit RPC."""
from unittest.mock import patch

from flask import Flask


def _app():
    from backend.routes.wallet_v2_routes import wallet_v2_bp
    app = Flask(__name__)
    app.register_blueprint(wallet_v2_bp)
    return app


@patch("backend.services.wallet_v2_service._network_snapshot")
@patch("backend.services.wallet_v2_service._trophy_counts")
@patch("backend.services.mn2_wallet_service.get_balance")
@patch("backend.routes.wallet_v2_routes.resolve_user_id")
def test_summary_returns_200_without_deposit_rpc(mock_resolve, mock_get_balance, mock_trophy, mock_network):
    mock_resolve.return_value = "test_user"
    mock_get_balance.return_value = {"success": True, "mn2_balance": 2.5, "user_id": "test_user"}
    mock_trophy.return_value = {"total": 3, "top25_owned": 2, "shop_items": 5}
    mock_network.return_value = {
        "block_height": 12345,
        "connections": 8,
        "mempool_tx": 2,
        "mn2_usd_price": 0.42,
        "pool_apr_percent": 12.0,
    }
    client = _app().test_client()
    with patch("backend.services.mn2_wallet_service.get_or_create_deposit_address") as mock_deposit:
        r = client.get("/api/wallet/v2/summary?user_id=test_user")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("success") is True
        assert data.get("mn2_balance") == 2.5
        assert data.get("trophy_counts", {}).get("total") == 3
        assert data.get("network", {}).get("block_height") == 12345
        assert data.get("wallet_v2_enabled") is True
        mock_deposit.assert_not_called()


@patch("backend.routes.wallet_v2_routes.build_summary")
@patch("backend.routes.wallet_v2_routes.resolve_user_id")
def test_summary_respects_sections_param(mock_resolve, mock_build):
    mock_resolve.return_value = "u1"
    mock_build.return_value = {"success": True, "user_id": "u1", "sections": ["balance"]}
    client = _app().test_client()
    r = client.get("/api/wallet/v2/summary?sections=balance")
    assert r.status_code == 200
    mock_build.assert_called_once_with("u1", sections_raw="balance")
