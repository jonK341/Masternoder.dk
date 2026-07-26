import os

from flask import Flask


def _app():
    from backend.middleware.auto_fix_404_middleware import register_auto_fix_middleware
    from backend.routes.all_page_routes import all_page_bp

    app = Flask(__name__)
    app.register_blueprint(all_page_bp)
    register_auto_fix_middleware(app)
    return app


def test_registered_pages_have_backing_index_files():
    from backend.routes.all_page_routes import PAGES, _base_path

    missing = [
        page for page in PAGES
        if not os.path.isfile(os.path.join(_base_path(), page, "index.html"))
    ]

    assert missing == []


def test_served_pages_include_content_version_header():
    from backend.routes.all_page_routes import CONTENT_VERSION, PAGES

    client = _app().test_client()

    for page in PAGES + ["agents"]:
        response = client.get(f"/{page}/")
        assert response.status_code == 200, page
        assert response.headers.get("X-Content-Version") == CONTENT_VERSION, page
        assert "Page Not Found" not in response.get_data(as_text=True), page


def test_retired_page_aliases_redirect_to_served_pages():
    client = _app().test_client()

    expected = {
        "/achievements": "/trophies",
        "/chat": "/lab#discussion",
    }
    for path, target in expected.items():
        response = client.get(path)
        assert response.status_code == 301, path
        assert response.headers["Location"].endswith(target), path


def test_fleet_progress_monitor_page_and_stream_alias():
    client = _app().test_client()

    response = client.get("/fleet-progress-monitor/")
    assert response.status_code == 200
    assert "5D Fleet Progress Monitor" in response.get_data(as_text=True)

    stream = client.get("/fleet-stream/")
    assert stream.status_code == 302
    assert "mode=stream" in stream.headers["Location"]


def test_streamer_hub_embeds_fleet_monitor():
    client = _app().test_client()

    response = client.get("/streamer/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Streamer hub" in body
    assert "/fleet-progress-monitor/?mode=stream" in body


def test_wallet_and_staking_pages_are_first_class():
    client = _app().test_client()

    expected = {
        "/wallets/": "Wallets",
        "/staking-leaderboard/": "Staking leaderboard",
        "/staking-teams/": "Staking teams",
    }
    for path, marker in expected.items():
        response = client.get(path)
        assert response.status_code == 200, path
        assert marker in response.get_data(as_text=True), path
