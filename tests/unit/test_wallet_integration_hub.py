"""Unit tests for wallet v2 integration hub BFF endpoint."""
from flask import Flask


def _app():
    from backend.routes.wallet_v2_routes import wallet_v2_bp
    app = Flask(__name__)
    app.register_blueprint(wallet_v2_bp)
    return app


def test_integration_hub_returns_units():
    client = _app().test_client()
    r = client.get("/api/wallet/v2/integration/hub?user_id=test_hub_user")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    units = data.get("units") or {}
    expected = [
        "WR-INT-EXCH",
        "WR-INT-ENC",
        "WR-INT-SHOP",
        "WR-INT-NEWS",
        "WR-INT-POD",
        "WR-INT-CHAT",
        "WR-INT-CAM",
        "WR-INT-CAM-UPG",
    ]
    for key in expected:
        assert key in units
        assert units[key].get("path")
        assert units[key].get("wallet_tab")


def test_integration_hub_camgirls_counts():
    client = _app().test_client()
    r = client.get("/api/wallet/v2/integration/hub")
    data = r.get_json()
    cam = data["units"]["WR-INT-CAM"]
    cam_upg = data["units"]["WR-INT-CAM-UPG"]
    assert cam.get("performer_count") == 25
    assert cam_upg.get("upgrade_count") == 250


def test_integration_hub_tab_groups():
    client = _app().test_client()
    r = client.get("/api/wallet/v2/integration/hub")
    data = r.get_json()
    groups = data.get("tab_groups") or {}
    assert "core" in groups
    assert "media" in groups
    assert "encoder" in groups["media"]
    assert "camgirls" in groups["camgirls"]
