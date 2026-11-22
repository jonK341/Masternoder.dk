"""Play-path Hot tables featured order."""
from tests.unit.test_utils import ensure_project_root

ensure_project_root()


def test_featured_hot_tables_order():
    from backend.services import casino_service

    cfg = casino_service.get_public_config()
    ids = [row.get("id") for row in (cfg.get("featured_games") or [])]
    assert ids == ["dice", "keno", "slots", "coin-flip", "crash", "roulette"]
    for row in cfg["featured_games"]:
        assert row.get("rails")
        assert row.get("edge_hint") or row.get("blurb")


def test_casino_html_has_play_path_tabs():
    from pathlib import Path

    html = Path("casino/index.html").read_text(encoding="utf-8")
    assert 'id="casino-tab-home"' in html
    assert "Hot tables" in html
    assert 'id="casino-tab-all-games"' in html
    assert 'id="casino-tab-free-play"' in html
    assert 'id="casino-tab-lounge"' in html
    assert html.index('id="casino-fund-play"') < html.index('id="casino-main-tabs"')
    assert html.index('id="casino-main-tabs"') < html.index('id="casino-tab-lounge"')
