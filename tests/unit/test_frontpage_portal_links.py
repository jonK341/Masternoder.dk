import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_frontpage_and_nav_include_wallet_staking_portal_links():
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    frontpage = (ROOT / "static/js/frontpage-home.js").read_text(encoding="utf-8")
    nav = (ROOT / "static/js/navigation-toolbar.js").read_text(encoding="utf-8")

    for href in ("/wallets", "/staking-leaderboard", "/staking-teams"):
        assert href in nav
        assert href in frontpage or "MN_NAV_TOP_20_IDS" in nav

    assert "/wallets" in index
    assert "/staking-leaderboard" in index
    assert "/staking-teams" in index


def test_navigation_primary_order_and_portal_grouping():
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
    assert "id: 'chat'" not in nav
    assert "NAV_CATEGORIES" in nav


def test_platform_news_announces_wallet_staking_pages():
    data = json.loads((ROOT / "data/platform_news.json").read_text(encoding="utf-8"))
    items = data.get("items") or []
    item = next((i for i in items if i.get("id") == "news-page-portal-wallet-staking-20260706"), None)

    assert item is not None
    assert item["href"] == "/wallets"
    assert "staking" in item["summary"].lower()


def test_front_page_starmap_monitor_shows_jon_and_the_live_stream():
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    start = index.index('id="fp-starmap-title"')
    section_start = index.rfind("<section", 0, start)
    section_end = index.index("</section>", start)
    block = index[section_start:section_end]

    assert "Star Map 25 monitor" in block
    assert 'data-starmap-monitor' in block
    assert "Profit daemon Jon" in block
    assert 'data-daemon-jon' in block
    assert 'data-live-stream' in block
    assert "https://www.youtube.com/embed/-iSYSBSn_8E" in block
    assert block.index("data-daemon-jon") < block.index("data-live-stream")
    assert block.index("data-starmap-monitor") < block.index("data-daemon-jon")


def test_starmap25_monitor_tab_includes_jon_and_the_live_stream():
    page = (ROOT / "starmap25" / "index.html").read_text(encoding="utf-8")
    panel_start = page.index('id="monitor-panel"')
    panel_end = page.index('id="buildup-panel"')
    panel = page[panel_start:panel_end]

    assert "Profit daemon Jon" in panel
    assert 'data-live-stream' in panel
    assert "https://www.youtube.com/embed/-iSYSBSn_8E" in panel


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
