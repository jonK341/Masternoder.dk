"""Player profiler picture features + camgirl studio board."""
from backend.routes.player_profiler import profiler_bp
from backend.services.player_profiler import player_profiler


def test_profiler_picture_save_and_avatar():
    uid = "test-profiler-pics"
    player_profiler.profiles.pop(uid, None)
    saved = player_profiler.add_picture(uid, "/static/camgirls/media/nova/gallery-2.webp", source="test")
    assert saved["success"] is True
    avatar = player_profiler.set_avatar_url(uid, "/static/camgirls/media/nova/icon.webp")
    assert avatar["success"] is True
    features = player_profiler.get_picture_features(uid)
    assert features["avatar_url"].endswith("icon.webp")
    assert features["total_saved"] >= 1


def test_profiler_pictures_route():
    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(profiler_bp)
    client = app.test_client()
    response = client.get("/api/profiler/pictures?user_id=route-test-user")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert "camgirl_pictures" in payload


def test_catalog_exposes_picture_and_upgrades(monkeypatch):
    from backend.services.camgirls_service import list_performers_catalog

    monkeypatch.setattr(
        "backend.services.camgirls_service._is_unlocked",
        lambda _uid, _pid: True,
    )
    monkeypatch.setattr(
        "backend.services.camgirls_service._is_age_verified",
        lambda _uid: True,
    )
    catalog = list_performers_catalog(user_id="pic-user", lite=False)
    nova = next(row for row in catalog["performers"] if row["id"] == "performer_nova")
    assert nova.get("picture_url")
    assert "portrait_pictures" in (nova.get("studio_upgrades") or [])
