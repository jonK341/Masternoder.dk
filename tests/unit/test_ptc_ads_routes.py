from unittest.mock import MagicMock, patch

from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def _app(tmp_path, monkeypatch):
    from flask import Flask
    import backend.services.ptc_ads_service as ptc
    from backend.routes.ptc_ads_routes import ptc_ads_bp

    monkeypatch.setenv("MASTERNODER_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("PTC_ADS_CONFIG_PATH", str(tmp_path / "ptc_campaigns.json"))
    monkeypatch.setenv("PTC_ADS_ADMIN_KEY", "secret")
    monkeypatch.setattr(ptc, "_MIN_DWELL_SECONDS", 0)

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(ptc_ads_bp)
    return app


def test_ptc_rotator_returns_active_campaigns(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with app.test_client() as client:
        response = client.get("/api/ptc/rotator?placement=home_smartlinks&limit=2&user_id=user-a")

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["placement"] == "home_smartlinks"
    assert len(data["campaigns"]) >= 1
    assert data["campaigns"][0]["sponsored"] is True
    assert "destination_url" not in data["campaigns"][0]


def test_ptc_click_start_and_verify_awards_internal_points(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        start = client.post("/api/ptc/click/start", json={
            "campaign_id": "internal-generator-growth",
            "placement": "home_smartlinks",
            "user_id": "user-a",
        })
        assert start.status_code == 200
        click_id = start.get_json()["click_id"]

        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            verified = client.post("/api/ptc/click/verify", json={
                "click_id": click_id,
                "user_id": "user-a",
            })

    assert verified.status_code == 200
    data = verified.get_json()
    assert data["success"] is True
    assert data["reward_kind"] == "internal_points"
    assert data["reward_points"] > 0
    mock_points.add_points.assert_called_once()
    kwargs = mock_points.add_points.call_args.kwargs
    assert kwargs["user_id"] == "user-a"
    assert kwargs["point_type"] == "ptc_points"
    assert kwargs["source"] == "ptc_ads"


def test_ptc_verify_is_idempotent(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    mock_points = MagicMock()
    mock_points.add_points.return_value = {"success": True}

    with app.test_client() as client:
        start = client.post("/api/ptc/click/start", json={
            "campaign_id": "internal-mn2-wallet",
            "placement": "shop_mn2",
            "user_id": "user-a",
        })
        click_id = start.get_json()["click_id"]
        with patch("backend.services.unified_points_database.unified_points_db", mock_points):
            first = client.post("/api/ptc/click/verify", json={"click_id": click_id, "user_id": "user-a"})
            second = client.post("/api/ptc/click/verify", json={"click_id": click_id, "user_id": "user-a"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.get_json()["already_credited"] is True
    mock_points.add_points.assert_called_once()


def test_ptc_admin_report_requires_key_and_summarizes(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with app.test_client() as client:
        denied = client.get("/api/ptc/admin/report")
        allowed = client.get("/api/ptc/admin/report", headers={"X-PTC-Admin-Key": "secret"})

    assert denied.status_code == 403
    assert allowed.status_code == 200
    data = allowed.get_json()
    assert data["success"] is True
    assert data["totals"]["campaigns"] >= 1


def test_ptc_advertiser_packages_are_public(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)
    with app.test_client() as client:
        response = client.get("/api/ptc/advertiser-packages")

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert any(package["id"] == "ptc-verified-visits-100" for package in data["packages"])
