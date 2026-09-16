"""Unit tests for camgirl AI feature bundles (animation + payment + sound)."""
from unittest.mock import patch

from flask import Flask


def _app():
    from backend.routes.wallet_v2_routes import wallet_v2_bp
    app = Flask(__name__)
    app.register_blueprint(wallet_v2_bp)
    return app


def test_ai_features_catalog_returns_100():
    client = _app().test_client()
    r = client.get("/api/wallet/v2/camgirls/ai-features")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    features = data.get("features") or []
    assert len(features) == 100
    assert features[0].get("id") == "CAM-AI-001"
    assert features[0].get("animation", {}).get("type")
    assert features[0].get("sound", {}).get("url")
    assert features[0].get("payment", {}).get("price_mn2") is not None


def test_ai_features_filter_category():
    client = _app().test_client()
    r = client.get("/api/wallet/v2/camgirls/ai-features?category=greetings")
    assert r.status_code == 200
    data = r.get_json()
    features = data.get("features") or []
    assert len(features) == 10
    assert all(f.get("category") == "greetings" for f in features)


def test_ai_feature_detail():
    client = _app().test_client()
    r = client.get("/api/wallet/v2/camgirls/ai-features/CAM-AI-001")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    feat = data.get("feature") or {}
    assert feat.get("id") == "CAM-AI-001"
    assert feat.get("name") == "Wave hello"


@patch("backend.routes.wallet_v2_routes.resolve_user_id")
@patch("backend.services.mn2_gift_service.transfer")
def test_ai_feature_trigger_payment(mock_transfer, mock_resolve):
    mock_resolve.return_value = "payer_user_1"
    mock_transfer.return_value = {
        "success": True,
        "amount_mn2": 2.0,
        "from_user": "payer_user_1",
        "to_user": "camgirl_cg_wallet_nova",
    }
    client = _app().test_client()
    r = client.post(
        "/api/wallet/v2/camgirls/ai-features/CAM-AI-002/trigger",
        json={"performer_id": "cg_wallet_luna"},
        query_string={"user_id": "payer_user_1"},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("feature_id") == "CAM-AI-002"
    assert data.get("paid_mn2", 0) > 0
    assert data.get("playback", {}).get("animation")
    assert data.get("playback", {}).get("sound")
    mock_transfer.assert_called_once()
    args = mock_transfer.call_args[0]
    assert args[0] == "payer_user_1"
    assert args[1] == "camgirl_cg_wallet_luna"


@patch("backend.routes.wallet_v2_routes.resolve_user_id")
@patch("backend.services.camgirls_wallet_service.load_user_progress")
@patch("backend.services.mn2_gift_service.transfer")
def test_ai_feature_trigger_free_when_upgrade_unlocked(mock_transfer, mock_progress, mock_resolve):
    mock_resolve.return_value = "payer_user_2"
    mock_progress.return_value = {"unlocked_ids": ["WR-CAM-UPG-007"], "unlocked_at": {}}
    client = _app().test_client()
    r = client.post(
        "/api/wallet/v2/camgirls/ai-features/CAM-AI-007/trigger",
        json={"performer_id": "cg_wallet_coral"},
        query_string={"user_id": "payer_user_2"},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("paid_mn2") == 0.0
    assert data.get("unlocked_via_upgrade") is True
    mock_transfer.assert_not_called()
