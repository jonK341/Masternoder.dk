"""
Unit tests for PayPal service and routes.
Run: pytest tests/unit/test_12_paypal.py -v
Uses mocks — no real PayPal API calls.
"""
import os
import sys
from unittest.mock import patch, MagicMock

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


# --- PayPal service (no real API) ---

def test_paypal_get_base_url_sandbox():
    """_get_base_url returns sandbox when PAYPAL_MODE not live."""
    from backend.services import paypal_service as svc
    with patch.dict(os.environ, {"PAYPAL_MODE": "sandbox"}, clear=False):
        url = svc._get_base_url()
        assert "sandbox" in url


def test_paypal_get_base_url_live():
    """_get_base_url returns live when PAYPAL_MODE=live."""
    from backend.services import paypal_service as svc
    with patch.dict(os.environ, {"PAYPAL_MODE": "live"}, clear=False):
        url = svc._get_base_url()
        assert "sandbox" not in url
        assert "api-m.paypal.com" in url


def test_paypal_get_base_url_live_prefix():
    """_get_base_url returns live when PAYPAL_MODE starts with 'live'."""
    from backend.services import paypal_service as svc
    with patch.dict(os.environ, {"PAYPAL_MODE": "live for production"}, clear=False):
        url = svc._get_base_url()
        assert "sandbox" not in url
        assert "api-m.paypal.com" in url


def test_paypal_get_access_token_no_creds():
    """get_access_token returns None when no credentials."""
    from backend.services import paypal_service as svc
    svc._token_cache["token"] = None
    svc._token_cache["expires"] = 0
    with patch.dict(os.environ, {"PAYPAL_CLIENT_ID": "", "PAYPAL_CLIENT_SECRET": ""}, clear=False):
        token = svc.get_access_token()
        assert token is None


def test_paypal_create_order_no_requests():
    """create_order returns error when requests not installed."""
    import backend.services.paypal_service as svc
    with patch.object(svc, "requests", None):
        result = svc.create_order(amount=1.0, item_name="Test")
        assert result.get("success") is False
        assert "requests" in (result.get("error") or "").lower()


def test_paypal_create_order_no_token():
    """create_order returns error when auth fails."""
    from backend.services import paypal_service as svc
    svc._token_cache["token"] = None
    svc._token_cache["expires"] = 0
    with patch.object(svc, "get_access_token", return_value=None):
        result = svc.create_order(amount=1.0, item_name="Test")
        assert result.get("success") is False
        assert "auth" in (result.get("error") or "").lower() or "failed" in (result.get("error") or "").lower()


def test_paypal_create_order_success_mock():
    """create_order returns approve_url when PayPal API succeeds."""
    from backend.services import paypal_service as svc

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": "ORDER-123",
        "status": "CREATED",
        "links": [
            {"rel": "approve", "href": "https://www.sandbox.paypal.com/checkout/ORDER-123"},
        ],
    }

    with patch.object(svc, "get_access_token", return_value="mock_token"):
        with patch.object(svc, "requests") as req:
            req.post.return_value = mock_response
            result = svc.create_order(amount=4.99, item_name="Premium Pack")
            assert result.get("success") is True
            assert result.get("order_id") == "ORDER-123"
            assert result.get("approve_url") and "paypal" in result.get("approve_url", "")


def test_paypal_capture_order_no_requests():
    """capture_order returns error when requests not installed."""
    import backend.services.paypal_service as svc
    with patch.object(svc, "requests", None):
        result = svc.capture_order("ORDER-123")
        assert result.get("success") is False


def test_paypal_capture_order_success_mock():
    """capture_order returns success when PayPal capture succeeds."""
    from backend.services import paypal_service as svc

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "status": "COMPLETED",
        "purchase_units": [{
            "payments": {
                "captures": [{
                    "id": "CAP-123",
                    "amount": {"value": "4.99", "currency_code": "USD"},
                }],
            },
        }],
    }

    with patch.object(svc, "get_access_token", return_value="mock_token"):
        with patch.object(svc, "requests") as req:
            req.post.return_value = mock_response
            result = svc.capture_order("ORDER-123")
            assert result.get("success") is True
            assert result.get("order_id") == "ORDER-123"
            assert result.get("amount") == "4.99"


def test_paypal_create_order_api_failure():
    """create_order returns error when PayPal API returns non-2xx."""
    from backend.services import paypal_service as svc

    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = '{"error": "Invalid request"}'

    with patch.object(svc, "get_access_token", return_value="mock_token"):
        with patch.object(svc, "requests") as req:
            req.post.return_value = mock_response
            result = svc.create_order(amount=1.0, item_name="Test")
            assert result.get("success") is False
            assert "error" in result


def test_paypal_create_order_with_custom_urls_and_currency():
    """create_order passes return_url, cancel_url, metadata and currency to API."""
    from backend.services import paypal_service as svc

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": "ORD-X",
        "status": "CREATED",
        "links": [{"rel": "approve", "href": "https://paypal.com/checkout/ORD-X"}],
    }

    with patch.object(svc, "get_access_token", return_value="mock_token"):
        with patch.object(svc, "requests") as req:
            req.post.return_value = mock_response
            result = svc.create_order(
                amount=9.99,
                currency="EUR",
                item_name="500 Coins",
                return_url="https://example.com/return",
                cancel_url="https://example.com/cancel",
                metadata={"item_id": "coin-pack-m", "user_id": "user_123"},
            )
            assert result.get("success") is True
            payload = req.post.call_args[1]["json"]
            assert payload["purchase_units"][0]["amount"]["currency_code"] == "EUR"
            assert payload["purchase_units"][0]["amount"]["value"] == "9.99"
            assert payload["purchase_units"][0]["custom_id"] == "coin-pack-m"
            assert payload["application_context"]["return_url"] == "https://example.com/return"
            assert payload["application_context"]["cancel_url"] == "https://example.com/cancel"


def test_paypal_capture_order_api_failure():
    """capture_order returns error when PayPal API returns non-2xx."""
    from backend.services import paypal_service as svc

    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = '{"error": "Order not found"}'

    with patch.object(svc, "get_access_token", return_value="mock_token"):
        with patch.object(svc, "requests") as req:
            req.post.return_value = mock_response
            result = svc.capture_order("INVALID-ORDER")
            assert result.get("success") is False
            assert "error" in result


def test_paypal_capture_order_status_not_completed():
    """capture_order returns success=False when status is not COMPLETED."""
    from backend.services import paypal_service as svc

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "status": "PENDING",
        "purchase_units": [{
            "payments": {"captures": [{"id": "CAP-X", "amount": {"value": "1.00", "currency_code": "USD"}}]},
        }],
    }

    with patch.object(svc, "get_access_token", return_value="mock_token"):
        with patch.object(svc, "requests") as req:
            req.post.return_value = mock_response
            result = svc.capture_order("ORDER-X")
            assert result.get("success") is False
            assert result.get("status") == "PENDING"


# --- PayPal routes (Flask) ---

def _get_app():
    """Create minimal Flask app with paypal blueprint (avoid slow create_app)."""
    from flask import Flask
    app = Flask(__name__)
    app.config["TESTING"] = True
    try:
        from backend.routes.paypal_routes import paypal_bp
        app.register_blueprint(paypal_bp)
    except Exception:
        pass
    return app


def test_paypal_create_order_route_invalid_amount():
    """Create order with amount <= 0 returns 400."""
    app = _get_app()
    with app.test_client() as c:
        r = c.post("/vidgenerator/api/paypal/create-order", json={
            "amount": 0,
            "item_name": "Test",
        })
        assert r.status_code == 400
        data = r.get_json()
        assert data.get("success") is False


def test_paypal_create_order_route_invalid_amount_negative():
    """Create order with negative amount returns 400."""
    app = _get_app()
    with app.test_client() as c:
        r = c.post("/vidgenerator/api/paypal/create-order", json={
            "amount": -1.0,
            "item_name": "Test",
        })
        assert r.status_code == 400


def test_paypal_create_order_route_account_required():
    """Create order with default_user returns 400 ACCOUNT_REQUIRED."""
    app = _get_app()
    with app.test_client() as c:
        r = c.post("/vidgenerator/api/paypal/create-order", json={
            "amount": 1.0,
            "item_name": "Test",
            "user_id": "default_user",
        })
        assert r.status_code == 400
        data = r.get_json()
        assert data.get("code") == "ACCOUNT_REQUIRED"


def test_paypal_create_order_route_success_mock():
    """Create order route returns approve_url when service succeeds."""
    from backend.services import paypal_service as svc

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": "ORDER-456",
        "status": "CREATED",
        "links": [{"rel": "approve", "href": "https://sandbox.paypal.com/checkout/ORDER-456"}],
    }

    app = _get_app()
    with patch.object(svc, "get_access_token", return_value="mock_token"):
        with patch.object(svc, "requests") as req:
            req.post.return_value = mock_response
            with app.test_client() as c:
                r = c.post("/vidgenerator/api/paypal/create-order", json={
                    "amount": 2.99,
                    "item_id": "premium-pack",
                    "item_name": "Premium Pack",
                    "user_id": "test_user",
                })
                assert r.status_code == 200
                data = r.get_json()
                assert data.get("success") is True
                assert data.get("order_id") == "ORDER-456"
                assert data.get("approve_url")


def test_paypal_capture_route_missing_order_id():
    """Capture without order_id returns 400."""
    app = _get_app()
    with app.test_client() as c:
        r = c.post("/vidgenerator/api/paypal/capture", json={})
        assert r.status_code == 400
        data = r.get_json()
        assert data.get("success") is False


def test_paypal_capture_route_order_id_in_query():
    """Capture accepts order_id from query params."""
    from backend.services import paypal_service as svc

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "status": "COMPLETED",
        "purchase_units": [{
            "payments": {"captures": [{"id": "CAP-Q", "amount": {"value": "0.99", "currency_code": "USD"}}]},
        }],
    }

    app = _get_app()
    with patch.object(svc, "get_access_token", return_value="mock_token"):
        with patch.object(svc, "requests") as req:
            req.post.return_value = mock_response
            with patch("backend.services.unified_points_database.unified_points_db", MagicMock()):
                with patch("backend.services.purchase_notification_service.notify_purchase"):
                    with app.test_client() as c:
                        r = c.post(
                            "/vidgenerator/api/paypal/capture",
                            json={"user_id": "test_user", "item_id": "coin-pack-s"},
                            query_string={"order_id": "ORDER-FROM-QUERY"},
                        )
                        assert r.status_code == 200
                        data = r.get_json()
                        assert data.get("success") is True
                        assert data.get("coins_granted") == 100


def test_paypal_capture_route_grants_coins_for_coin_pack():
    """Capture grants coins when item_id is a coin pack."""
    from backend.services import paypal_service as svc

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "status": "COMPLETED",
        "purchase_units": [{
            "payments": {"captures": [{"id": "CAP-500", "amount": {"value": "4.99", "currency_code": "USD"}}]},
        }],
    }

    app = _get_app()
    with patch.object(svc, "get_access_token", return_value="mock_token"):
        with patch.object(svc, "requests") as req:
            req.post.return_value = mock_response
            with patch("backend.services.unified_points_database.unified_points_db", MagicMock()) as mock_db:
                with patch("backend.services.purchase_notification_service.notify_purchase"):
                    with app.test_client() as c:
                        r = c.post("/vidgenerator/api/paypal/capture", json={
                            "order_id": "ORD-500",
                            "user_id": "buyer_123",
                            "item_id": "coin-pack-m",
                            "item_name": "500 Coins",
                        })
                        assert r.status_code == 200
                        data = r.get_json()
                        assert data.get("coins_granted") == 500
                        assert data.get("amount") == "4.99"
                        if mock_db.add_points.called:
                            call_kw = mock_db.add_points.call_args[1]
                            assert call_kw.get("point_type") == "coins"
                            assert call_kw.get("amount") == 500


def test_paypal_capture_route_grants_monetization_for_non_coin_pack():
    """Capture grants monetization_points when item_id is not a coin pack."""
    from backend.services import paypal_service as svc

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "status": "COMPLETED",
        "purchase_units": [{
            "payments": {"captures": [{"id": "CAP-X", "amount": {"value": "2.99", "currency_code": "USD"}}]},
        }],
    }

    app = _get_app()
    with patch.object(svc, "get_access_token", return_value="mock_token"):
        with patch.object(svc, "requests") as req:
            req.post.return_value = mock_response
            with patch("backend.services.unified_points_database.unified_points_db", MagicMock()) as mock_db:
                with patch("backend.services.purchase_notification_service.notify_purchase"):
                    with app.test_client() as c:
                        r = c.post("/vidgenerator/api/paypal/capture", json={
                            "order_id": "ORD-OTHER",
                            "user_id": "buyer_456",
                            "item_id": "premium-theme",
                            "item_name": "Premium Theme",
                        })
                        assert r.status_code == 200
                        data = r.get_json()
                        assert data.get("coins_granted") == 0
                        if mock_db.add_points.called:
                            call_kw = mock_db.add_points.call_args[1]
                            assert call_kw.get("point_type") == "monetization_points"
                            assert call_kw.get("amount") == 299  # 2.99 * 100


def test_paypal_capture_route_service_failure():
    """Capture returns 500 when PayPal service fails."""
    from backend.services import paypal_service as svc

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    app = _get_app()
    with patch.object(svc, "get_access_token", return_value="mock_token"):
        with patch.object(svc, "requests") as req:
            req.post.return_value = mock_response
            with app.test_client() as c:
                r = c.post("/vidgenerator/api/paypal/capture", json={
                    "order_id": "ORD-500",
                    "user_id": "test_user",
                })
                assert r.status_code == 500
                data = r.get_json()
                assert data.get("success") is False


def test_paypal_create_order_return_url_contains_item_and_user():
    """Create order builds return URL with item_id and user_id."""
    from backend.services import paypal_service as svc

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": "ORD-URL",
        "status": "CREATED",
        "links": [{"rel": "approve", "href": "https://paypal.com/checkout/ORD-URL"}],
    }

    app = _get_app()
    with patch.object(svc, "get_access_token", return_value="mock_token"):
        with patch.object(svc, "requests") as req:
            req.post.return_value = mock_response
            with app.test_client() as c:
                r = c.post("/vidgenerator/api/paypal/create-order", json={
                    "amount": 1.0,
                    "item_id": "coin-pack-s",
                    "item_name": "100 Coins",
                    "user_id": "user_abc",
                })
                assert r.status_code == 200
                payload = req.post.call_args[1]["json"]
                return_url = payload["application_context"]["return_url"]
                assert "item_id=" in return_url and "coin-pack-s" in return_url
                assert "user_id=" in return_url and "user_abc" in return_url
                assert "paypal=success" in return_url


def test_paypal_capture_calls_notify_purchase():
    """Capture route calls notify_purchase on success."""
    from backend.services import paypal_service as svc

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "status": "COMPLETED",
        "purchase_units": [{
            "payments": {"captures": [{"id": "CAP-N", "amount": {"value": "0.99", "currency_code": "USD"}}]},
        }],
    }

    app = _get_app()
    with patch.object(svc, "get_access_token", return_value="mock_token"):
        with patch.object(svc, "requests") as req:
            req.post.return_value = mock_response
            with patch("backend.services.unified_points_database.unified_points_db", MagicMock()):
                with patch("backend.services.purchase_notification_service.notify_purchase") as mock_notify:
                    with app.test_client() as c:
                        r = c.post("/vidgenerator/api/paypal/capture", json={
                            "order_id": "ORD-NOTIFY",
                            "user_id": "user_xyz",
                            "item_id": "coin-pack-s",
                        })
                        assert r.status_code == 200
                        assert mock_notify.called
                        call_kw = mock_notify.call_args[1]
                        assert call_kw.get("amount") == 0.99
                        assert call_kw.get("user_id") == "user_xyz"
                        assert call_kw.get("coins_granted") == 100
                        assert call_kw.get("source") == "paypal"


def test_paypal_capture_grants_shop_item():
    """Capture adds shop item to inventory when item_id is PayPal-priced item."""
    from backend.services import paypal_service as svc

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "status": "COMPLETED",
        "purchase_units": [{
            "payments": {"captures": [{"id": "CAP-SHOP", "amount": {"value": "1.50", "currency_code": "USD"}}]},
        }],
    }

    app = _get_app()
    with patch.object(svc, "get_access_token", return_value="mock_token"):
        with patch.object(svc, "requests") as req:
            req.post.return_value = mock_response
            with patch("backend.services.unified_points_database.unified_points_db", MagicMock()):
                with patch("backend.services.purchase_notification_service.notify_purchase"):
                    with patch("backend.services.shop_db_service.record_purchase") as mock_record:
                        with patch("backend.services.shop_db_service.add_to_inventory") as mock_inv:
                            mock_record.return_value = 999
                            with app.test_client() as c:
                                # Use a real shop item id from seed (e.g. shop-1 has coin price)
                                r = c.post("/vidgenerator/api/paypal/capture", json={
                                    "order_id": "ORD-SHOP",
                                    "user_id": "buyer_shop",
                                    "item_id": "shop-1",
                                    "item_name": "Galaxy Dark",
                                })
                                assert r.status_code == 200
                                data = r.get_json()
                                assert data.get("item_granted") == "shop-1"
                                assert data.get("coins_granted") == 0
                                assert mock_inv.called or mock_record.called


def test_coin_pack_map_structure():
    """COIN_PACK_MAP has expected coin packs with coins_granted."""
    from backend.routes.shop_routes import COIN_PACK_MAP, PAYPAL_COIN_PACKS

    assert len(PAYPAL_COIN_PACKS) >= 3
    assert "coin-pack-s" in COIN_PACK_MAP
    assert "coin-pack-m" in COIN_PACK_MAP
    assert "coin-pack-l" in COIN_PACK_MAP
    assert COIN_PACK_MAP["coin-pack-s"]["coins_granted"] == 100
    assert COIN_PACK_MAP["coin-pack-m"]["coins_granted"] == 500
    assert COIN_PACK_MAP["coin-pack-l"]["coins_granted"] == 2000
