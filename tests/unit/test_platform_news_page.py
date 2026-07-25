"""Platform news API tests."""
from flask import Flask


def _app(monkeypatch=None, tmp_path=None):
    from backend.routes.platform_news_routes import platform_news_bp
    import backend.routes.platform_news_routes as pnr
    app = Flask(__name__)
    app.register_blueprint(platform_news_bp)
    if monkeypatch is not None and tmp_path is not None:
        news_file = tmp_path / "platform_news.json"
        news_file.write_text(
            '''{"items":[
              {"id":"a","title":"Casino","date":"2026-07-01","channel":"casino","category":"casino"},
              {"id":"b","title":"Multi","date":"2026-07-02","channel":"home","channels":["home","explorer"],"category":"home"},
              {"id":"c","title":"Ops","date":"2026-07-03","channel":"ops","category":"ops","featured":true}
            ]}''',
            encoding="utf-8",
        )
        monkeypatch.setattr(pnr, "_NEWS_PATH", str(news_file))
        monkeypatch.setattr(pnr, "_SUBS_PATH", str(tmp_path / "subs.json"))
        (tmp_path / "subs.json").write_text('{"casino": 4, "home": 2}', encoding="utf-8")
    return app


def test_platform_news_list():
    c = _app().test_client()
    r = c.get("/api/news/platform?limit=5")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert isinstance(data.get("news"), list)


def test_platform_news_channel_filter():
    c = _app().test_client()
    r = c.get("/api/news/platform?channel=casino&limit=10")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    for item in data.get("news") or []:
        ch = (item.get("channel") or item.get("category") or "").lower()
        channels = [str(x).lower() for x in (item.get("channels") or [])]
        assert ch == "casino" or "casino" in channels


def test_platform_news_channels(tmp_path, monkeypatch):
    c = _app(monkeypatch, tmp_path).test_client()
    r = c.get("/api/news/channels")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert isinstance(data.get("channels"), list)
    by_id = {ch["id"]: ch for ch in data["channels"]}
    assert by_id["casino"]["count"] == 1
    assert by_id["casino"]["subscribers"] == 4
    assert by_id["explorer"]["count"] == 1  # from channels[]


def test_platform_news_channels_array_filter(tmp_path, monkeypatch):
    c = _app(monkeypatch, tmp_path).test_client()
    r = c.get("/api/news/platform?channel=explorer&limit=10")
    assert r.status_code == 200
    news = r.get_json().get("news") or []
    assert len(news) == 1
    assert news[0]["id"] == "b"


def test_platform_news_publish_and_rss(tmp_path, monkeypatch):
    monkeypatch.delenv("MN2_OPS_SECRET", raising=False)
    monkeypatch.delenv("DISCORD_OPS_SECRET", raising=False)
    monkeypatch.delenv("ADMIN_OPS_SECRET", raising=False)
    import backend.routes.platform_news_routes as pnr
    import backend.services.platform_news_publish as pub
    news_file = tmp_path / "platform_news.json"
    news_file.write_text('{"items":[]}', encoding="utf-8")
    monkeypatch.setattr(pnr, "_NEWS_PATH", str(news_file))
    monkeypatch.setattr(pub, "_NEWS", str(news_file))
    c = _app().test_client()
    r = c.post(
        "/api/news/publish",
        json={
            "id": "pub1",
            "title": "Hello",
            "summary": "World",
            "channel": "ops",
            "channels": ["ops", "discord"],
        },
        environ_base={"REMOTE_ADDR": "127.0.0.1"},
    )
    assert r.status_code == 200
    assert r.get_json().get("success") is True
    rss = c.get("/api/news/rss/ops")
    assert rss.status_code == 200
    assert b"Hello" in rss.data
    assert b"<rss" in rss.data
