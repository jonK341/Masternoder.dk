"""Unit tests for 25-source community ledger population."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest


@pytest.fixture
def population_env(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    logs = tmp_path / "logs"
    logs.mkdir()

    (data / "youtube_leads.json").write_text(
        json.dumps(
            {
                "subscribers": [{"youtube_id": "yt1", "display_name": "Sub1", "user_id": "u-yt-1"}],
                "commenters": [{"youtube_id": "ytc1", "display_name": "Cmt1", "discord_id": "111"}],
            }
        ),
        encoding="utf-8",
    )
    (data / "facebook_leads.json").write_text(
        json.dumps(
            {
                "page_fans": [{"facebook_id": "fb1", "display_name": "Fan1"}],
                "group_members": [{"facebook_id": "fb2", "user_id": "u-fb-2"}],
                "messenger_leads": [{"facebook_id": "fb3", "intent": "mn2"}],
            }
        ),
        encoding="utf-8",
    )
    (data / "shop_checkout_abandoned.json").write_text(
        json.dumps({"abandoned": [{"user_id": "u-shop", "discord_id": "222"}]}),
        encoding="utf-8",
    )
    (data / "newsletter_optins.json").write_text(
        json.dumps({"optins": [{"user_id": "u-nl", "discord_id": "333"}]}),
        encoding="utf-8",
    )
    (data / "ledger_population_sources.json").write_text(
        json.dumps(
            {
                "sources": [
                    {"id": "youtube_subscriber", "enabled": True, "scan": "scan_youtube_subscribers", "weight": 8},
                    {"id": "youtube_commenter", "enabled": True, "scan": "scan_youtube_commenters", "weight": 7},
                    {"id": "facebook_page_fan", "enabled": True, "scan": "scan_facebook_page_fans", "weight": 8},
                    {"id": "shop_checkout_abandoned", "enabled": True, "scan": "scan_shop_checkout_abandoned", "weight": 12},
                    {"id": "newsletter_optin", "enabled": True, "scan": "scan_newsletter_optins", "weight": 5},
                    {"id": "local_linked", "enabled": True, "scan": "scan_local_linked_users", "weight": 10},
                ]
            }
        ),
        encoding="utf-8",
    )

    import backend.services.community_ledger_population as clp

    monkeypatch.setattr(clp, "_BASE", str(tmp_path))
    monkeypatch.setattr(clp, "_POPULATION_CONFIG", str(data / "ledger_population_sources.json"))
    monkeypatch.setattr(clp, "_YOUTUBE_LEADS", str(data / "youtube_leads.json"))
    monkeypatch.setattr(clp, "_FACEBOOK_LEADS", str(data / "facebook_leads.json"))
    yield data


def test_youtube_subscriber_scan(population_env):
    from backend.services.community_ledger_population import scan_youtube_subscribers

    rows = scan_youtube_subscribers()
    assert len(rows) == 1
    assert rows[0]["youtube_id"] == "yt1"
    assert rows[0]["source_id"] == "youtube_subscriber"


def test_youtube_commenter_scan(population_env):
    from backend.services.community_ledger_population import scan_youtube_commenters

    rows = scan_youtube_commenters()
    assert any(r["discord_id"] == "111" for r in rows)


def test_facebook_page_fan_scan(population_env):
    from backend.services.community_ledger_population import scan_facebook_page_fans

    rows = scan_facebook_page_fans()
    assert rows[0]["facebook_id"] == "fb1"


def test_shop_abandoned_scan(population_env):
    from backend.services.community_ledger_population import scan_shop_checkout_abandoned

    rows = scan_shop_checkout_abandoned()
    assert rows[0]["discord_id"] == "222"
    assert "shop_abandoned" in rows[0]["buyer_signals"]


def test_newsletter_scan(population_env):
    from backend.services.community_ledger_population import scan_newsletter_optins

    rows = scan_newsletter_optins()
    assert rows[0]["user_id"] == "u-nl"


def test_scan_all_enabled_counts(population_env):
    from backend.services.community_ledger_population import scan_all_enabled_sources

    with patch("backend.services.discord_fulfillment_ledger_service.scan_local_linked_users", return_value=[]):
        result = scan_all_enabled_sources(use_discord_api=False)
    counts = result.get("source_counts") or {}
    assert counts.get("youtube_subscriber", 0) >= 1
    assert counts.get("facebook_page_fan", 0) >= 1
    assert len(result.get("rows") or []) >= 4


def test_merge_youtube_and_discord_ids(tmp_path, monkeypatch):
    import backend.services.discord_fulfillment_ledger_service as dfl

    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(dfl, "_BASE", str(tmp_path))
    monkeypatch.setattr(dfl, "_data_dir", lambda: str(data))
    monkeypatch.setattr(dfl, "_ledger_path", lambda: str(data / "ledger.json"))
    monkeypatch.setattr(dfl, "_order_list_path", lambda: str(data / "order_list.json"))
    monkeypatch.setattr(dfl, "_config_path", lambda: str(data / "config.json"))
    (data / "config.json").write_text(json.dumps({"buyer_signal_threshold": 20, "priority_weights": {}}), encoding="utf-8")

    merged: dict = {}
    index: dict = {}
    dfl._merge_seed(
        merged,
        index,
        {"youtube_id": "yt1", "user_id": "u1", "display_name": "YT User", "buyer_signals": [], "buyer_score": 0},
        "youtube_subscriber",
    )
    dfl._merge_seed(
        merged,
        index,
        {"discord_id": "999", "user_id": "u1", "discord_username": "DiscordUser", "buyer_signals": [], "buyer_score": 0},
        "local_linked",
    )
    assert len(merged) == 1
    row = next(iter(merged.values()))
    assert row.get("discord_id") == "999"
    assert row.get("youtube_id") == "yt1"
    assert "youtube_subscriber" in row.get("sources")
    assert "local_linked" in row.get("sources")


def test_build_order_list_assigns_ledger_rank(tmp_path, monkeypatch):
    import backend.services.discord_fulfillment_ledger_service as dfl
    import backend.services.community_ledger_population as clp

    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(dfl, "_BASE", str(tmp_path))
    monkeypatch.setattr(clp, "_BASE", str(tmp_path))
    monkeypatch.setattr(dfl, "_data_dir", lambda: str(data))
    monkeypatch.setattr(dfl, "_ledger_path", lambda: str(data / "ledger.json"))
    monkeypatch.setattr(dfl, "_order_list_path", lambda: str(data / "order_list.json"))
    monkeypatch.setattr(dfl, "_config_path", lambda: str(data / "config.json"))
    (data / "config.json").write_text(
        json.dumps({"buyer_signal_threshold": 20, "priority_weights": {"local_linked": 10}}),
        encoding="utf-8",
    )

    fake_rows = [
        {"source_id": "local_linked", "discord_id": "a", "user_id": "u1", "buyer_score": 5, "buyer_signals": []},
        {"source_id": "youtube_subscriber", "youtube_id": "yt9", "user_id": "u2", "buyer_score": 0, "buyer_signals": []},
    ]
    with patch("backend.services.community_ledger_population.scan_all_enabled_sources", return_value={"rows": fake_rows, "source_counts": {"local_linked": 1, "youtube_subscriber": 1}, "api_used": False, "api_notes": []}):
        with patch.object(dfl, "_mn2_balance_for_user", return_value=0.0):
            result = dfl.build_order_list(use_all_sources=True, use_discord_api=False)

    assert result["total"] == 2
    orders = dfl.get_order_list()["orders"]
    assert orders[0].get("ledger_rank") == 1
    assert orders[1].get("ledger_rank") == 2
