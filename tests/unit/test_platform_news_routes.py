"""Platform news API tests."""
from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_platform_news_endpoint(tmp_path, monkeypatch):
    from flask import Flask
    from backend.routes.platform_news_routes import platform_news_bp
    import backend.routes.platform_news_routes as pnr

    news_file = tmp_path / "platform_news.json"
    news_file.write_text(
        '{"items":[{"id":"t1","title":"Test headline","date":"2026-05-19","featured":true}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(pnr, "_NEWS_PATH", str(news_file))

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(platform_news_bp)

    with app.test_client() as client:
        res = client.get("/api/news/platform?limit=5")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["news"]) == 1
    assert data["news"][0]["title"] == "Test headline"
