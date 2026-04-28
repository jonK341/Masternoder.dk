"""
Unit tests for Shop routes (items, currency, purchase).
Run: pytest tests/unit/test_11_shop_routes.py -v
"""
from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _get_app():
    """Create minimal Flask app with shop blueprint (avoid slow create_app)."""
    from flask import Flask
    app = Flask(__name__)
    app.config["TESTING"] = True
    try:
        from backend.routes.shop_routes import shop_bp
        app.register_blueprint(shop_bp)
    except Exception:
        pass
    return app


def test_shop_items_endpoint():
    """Shop items returns success and list."""
    app = _get_app()
    with app.test_client() as c:
        r = c.get("/api/game/shop/items")
        assert r.status_code == 200
        data = r.get_json()
        assert data is not None
        assert data.get("success") is True
        assert isinstance(data.get("items"), list)
        assert len(data.get("items", [])) > 0


def test_shop_items_with_category():
    """Shop items filtered by category."""
    app = _get_app()
    with app.test_client() as c:
        r = c.get("/api/game/shop/items?category=themes")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("success") is True
        items = data.get("items", [])
        for i in items:
            assert (i.get("category") or "").lower() == "themes"


def test_shop_paypal_items():
    """PayPal items endpoint returns items with price_usd."""
    app = _get_app()
    with app.test_client() as c:
        r = c.get("/api/shop/paypal-items")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("success") is True
        items = data.get("paypal_items", {})
        assert isinstance(items, dict)
        # Should have items with price_usd (from coin-priced items)
        if items:
            for iid, info in list(items.items())[:3]:
                assert "price_usd" in info
                assert "name" in info


def test_shop_coin_packs():
    """Coin packs endpoint returns PayPal coin packs."""
    app = _get_app()
    with app.test_client() as c:
        r = c.get("/api/shop/coin-packs")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("success") is True
        packs = data.get("coin_packs", [])
        assert isinstance(packs, list)
        assert len(packs) >= 1
        for p in packs:
            assert "id" in p and "price_usd" in p and "coins_granted" in p


def test_shop_currency_endpoint():
    """Shop currency returns success and currency value (unified_points mocked)."""
    mock_db = MagicMock()
    mock_db.get_all_points.return_value = {"success": True, "points": {"coins": 42}}
    app = _get_app()
    with app.test_client() as c:
        with patch("backend.services.unified_points_database.unified_points_db", mock_db):
            r = c.get("/api/shop/currency?user_id=test_user")
        assert r.status_code == 200
        data = r.get_json()
        assert data is not None
        assert data.get("success") is True
        assert "currency" in data
        assert isinstance(data.get("currency"), (int, float))
        assert int(data.get("currency")) == 42


def test_game_shop_currency_alias_matches_smoke_contract():
    """Shop smoke checks use the legacy /api/game/shop/currency URL."""
    mock_db = MagicMock()
    mock_db.get_all_points.return_value = {"success": True, "points": {"coins": 42}}
    app = _get_app()
    with app.test_client() as c:
        with patch("backend.services.unified_points_database.unified_points_db", mock_db):
            r = c.get("/api/game/shop/currency?user_id=test_user")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("success") is True
        assert data.get("currency") == 42
        assert data.get("coins") == 42
        assert data.get("balance", {}).get("coins") == 42


def test_shop_config_has_ui_version():
    """Shop config exposes shop_ui_version (matches SHOP_UI_VERSION) and profile URL."""
    from backend.routes.shop_routes import SHOP_UI_VERSION

    app = _get_app()
    with app.test_client() as c:
        r = c.get("/api/shop/config")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("success") is True
        assert data.get("shop_ui_version") == SHOP_UI_VERSION
        assert data.get("profile_url")
        alc = data.get("api_line_checks") or {}
        assert isinstance(alc.get("checks"), list)
        assert len(alc["checks"]) == 10


def test_shop_payment_health():
    """Payment health returns mn2_daemon, paypal, and shop_storage (MN2 RPC mocked)."""
    app = _get_app()
    with app.test_client() as c:
        with patch("backend.services.mn2_rpc_client.health_check") as mn2_h:
            mn2_h.return_value = {"status": "ok", "block_height": 1, "latency_ms": 0}
            r = c.get("/api/shop/payment-health")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("success") is True
        assert "mn2_daemon" in data
        assert "paypal" in data
        assert "shop_storage" in data
        ss = data.get("shop_storage") or {}
        assert ss.get("mode") in ("database", "file", "unknown")


def test_shop_v3_items():
    """Shop v3 items returns unified format."""
    app = _get_app()
    with app.test_client() as c:
        r = c.get("/api/shop-v3/items")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("success") is True
        assert "items" in data
        assert "boosters" in data
        assert isinstance(data.get("items"), list)


def test_shop_purchase_missing_item_id():
    """Purchase without item_id returns 400."""
    app = _get_app()
    with app.test_client() as c:
        r = c.post("/api/shop-v3/purchase", json={"user_id": "test"})
        assert r.status_code == 400
        data = r.get_json()
        assert data.get("success") is False
        assert "item_id" in (data.get("error") or "").lower() or "missing" in (data.get("error") or "").lower()


def test_shop_purchase_nonexistent_item():
    """Purchase nonexistent item returns 404."""
    app = _get_app()
    with app.test_client() as c:
        r = c.post("/api/shop-v3/purchase", json={
            "item_id": "nonexistent-item-99999",
            "user_id": "test_user",
            "quantity": 1,
        })
        assert r.status_code == 404
        data = r.get_json()
        assert data.get("success") is False


def test_shop_purchase_valid_item():
    """Coin-priced item with zero balance returns 400 (unified_points mocked; deterministic)."""
    mock_db = MagicMock()
    mock_db.get_all_points.return_value = {"success": True, "points": {"coins": 0}}
    app = _get_app()
    with app.test_client() as c:
        items_r = c.get("/api/game/shop/items")
        items_data = items_r.get_json()
        items = items_data.get("items", [])
        if not items:
            return
        item_id = None
        for it in items:
            p = it.get("price")
            if isinstance(p, int) and p > 0:
                item_id = it.get("id")
                break
        if not item_id:
            return
        with patch("backend.services.unified_points_database.unified_points_db", mock_db):
            r = c.post("/api/shop-v3/purchase", json={
                "item_id": item_id,
                "user_id": "test_user",
                "quantity": 1,
            })
        assert r.status_code == 400
        data = r.get_json()
        assert data.get("success") is False
