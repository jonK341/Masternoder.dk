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


def test_frontpage_drops_dead_blocks_and_keeps_news_podcast():
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    frontpage = (ROOT / "static/js/frontpage-home.js").read_text(encoding="utf-8")
    assert "Agent void" not in index
    assert "Live surface" not in index
    assert "fp-game-hub" not in index
    assert "fp-v20-upgrade" not in index
    assert 'id="fp-news-list"' in index
    assert 'id="fp-podcast-title"' in index
    assert 'id="fp-podcast-latest"' in index
    assert "game-hub-panel.js" not in index
    assert "loadPodcastPanel" in frontpage
    assert "fetchJsonTimed" in frontpage
    # Home news must not wait on requestIdleCallback / cold aggregator.
    assert "loadNews();" in frontpage
    assert "aggregators/intelligence/news" in frontpage
    assert "lite=1" in frontpage


def test_news_podcast_skip_path_correction_hot_paths():
    from backend.middleware.signal_processor_middleware import _SKIP_PATH_CORRECTION_PREFIXES

    prefixes = set(_SKIP_PATH_CORRECTION_PREFIXES)
    assert "/api/news/" in prefixes
    assert "/api/podcast/" in prefixes
    assert "/api/profit-daemon/" in prefixes


def test_platform_news_covers_november_upgrade_wave():
    data = json.loads((ROOT / "data/platform_news.json").read_text(encoding="utf-8"))
    items = data.get("items") or []
    ids = {i.get("id") for i in items}
    assert "news-upgrade-wave-fast-news-podcast-20261113" in ids
    assert "news-upgrade-starmap-ideas-loading-20261113" in ids
    episodes = json.loads((ROOT / "data/podcast_episodes.json").read_text(encoding="utf-8")).get("episodes") or []
    assert episodes and episodes[0].get("id") == "ep-006-upgrade-briefing-nov13"


def test_starmap25_ideas_board_present():
    starmap = (ROOT / "starmap25/index.html").read_text(encoding="utf-8")
    map_data = json.loads((ROOT / "data/star_map_25.json").read_text(encoding="utf-8"))
    assert 'data-starmap-tab="ideas"' in starmap
    assert "ideas-grid" in starmap
    ideas = map_data.get("ideas") or []
    assert len(ideas) >= 4
    assert any(i.get("id") == "chronoscout_4d" for i in ideas)


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
