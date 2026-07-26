import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_frontpage_and_nav_include_wallet_staking_portal_links():
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    smart_links = (ROOT / "static/js/frontpage-home.js").read_text(encoding="utf-8")
    nav = (ROOT / "static/js/navigation-toolbar.js").read_text(encoding="utf-8")

    for href in ("/wallets", "/staking-leaderboard", "/staking-teams"):
        assert href in index
        assert href in smart_links
        assert href in nav


def test_navigation_primary_order_and_removed_duplicates():
    nav = (ROOT / "static/js/navigation-toolbar.js").read_text(encoding="utf-8")
    expected_order = [
        "id: 'home'",
        "id: 'generator'",
        "id: 'game'",
        "id: 'battle'",
        "id: 'trophies'",
        "id: 'quests'",
        "id: 'shop'",
        "id: 'explorer'",
        "id: 'profile'",
        "id: 'agents'",
    ]
    positions = [nav.index(marker) for marker in expected_order]

    assert positions == sorted(positions)
    assert "id: 'stories'" not in nav
    assert "id: 'command-center'" not in nav
    assert "id: 'chat'" not in nav


def test_platform_news_announces_wallet_staking_pages():
    data = json.loads((ROOT / "data/platform_news.json").read_text(encoding="utf-8"))
    items = data.get("items") or []
    item = next((i for i in items if i.get("id") == "news-page-portal-wallet-staking-20260706"), None)

    assert item is not None
    assert item["href"] == "/wallets"
    assert "staking" in item["summary"].lower()


def test_platform_news_streamer_podcast_story():
    data = json.loads((ROOT / "data/platform_news.json").read_text(encoding="utf-8"))
    items = data.get("items") or []
    story = next((i for i in items if i.get("id") == "news-streamer-podcast-5d-monitor-20260726"), None)
    assert story is not None
    assert story["href"] == "/streamer/"
    assert "podcast" in story["summary"].lower()


def test_frontpage_includes_game_hub_stylesheet():
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    assert "game-hub-panel.css" in index


def test_podcast_portal_lines_include_streamer():
    data = json.loads((ROOT / "data/podcast_portal_lines.json").read_text(encoding="utf-8"))
    sites = data.get("sites") or []
    assert any(s.get("id") == "streamer" for s in sites)


def test_reader_launcher_stylesheet_exists():
    assert (ROOT / "static/css/calm-reader.css").is_file()


def test_lite_app_registers_frontpage_game_hub_api(monkeypatch):
    monkeypatch.setenv("LITE_APP", "1")
    monkeypatch.setenv("DAEMON_QUIET", "1")

    from src.app import create_app

    client = create_app().test_client()
    response = client.get("/api/game-hub/overview?user_id=default_user")

    assert response.status_code == 200
    assert response.get_json()["success"] is True
