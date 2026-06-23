"""Tests for game Discord fan-out, link service, shop promos."""
from __future__ import annotations

import json
import os
import tempfile

import pytest


def test_discord_link_status_not_linked():
    from backend.services import discord_link_service as dls

    with tempfile.TemporaryDirectory() as tmp:
        ident = os.path.join(tmp, "user_identifiers")
        os.makedirs(ident)
        old = dls._IDENT_DIR
        dls._IDENT_DIR = ident
        try:
            r = dls.link_status("test-user-no-link")
            assert r["success"] is True
            assert r["linked"] is False
        finally:
            dls._IDENT_DIR = old


def test_discord_link_and_unlink():
    from backend.services import discord_link_service as dls

    with tempfile.TemporaryDirectory() as tmp:
        ident = os.path.join(tmp, "user_identifiers")
        os.makedirs(ident)
        old = dls._IDENT_DIR
        dls._IDENT_DIR = ident
        try:
            assert dls.link_user("u1", "999888777").get("success") is True
            assert dls.get_discord_id_for_user("u1") == "999888777"
            st = dls.link_status("u1")
            assert st["linked"] is True
            assert dls.unlink_user("u1").get("unlinked") is True
            assert dls.get_discord_id_for_user("u1") is None
        finally:
            dls._IDENT_DIR = old


def test_game_discord_fanout_dry_run(tmp_path, monkeypatch):
    from backend.services import game_discord_fanout as gdf

    log = tmp_path / "activity_events.jsonl"
    log.write_text(
        json.dumps({
            "type": "battle_win",
            "channel": "game",
            "ts": "t1",
            "payload": {"battle_id": "b1", "points_delta": 10, "difficulty": "balanced", "battle_mode": "rps"},
        }) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(gdf, "_EVENTS", str(log))
    monkeypatch.setattr(gdf, "_CURSOR", str(tmp_path / "cursor.json"))
    r = gdf.run_fanout(dry_run=True)
    assert r["success"] is True
    assert r["processed"] == 1
    assert r["posted"] == 1


def test_shop_discord_promo_create_and_redeem(tmp_path, monkeypatch):
    from backend.services import shop_discord_promo_service as sdps
    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    promo_path = tmp_path / "discord_promo_codes.json"
    monkeypatch.setattr(sdps, "_PROMOS_PATH", str(promo_path))
    base = tmp_path / "app"
    db = upd.UnifiedPointsDatabase(base_dir=str(base))
    monkeypatch.setattr(upd, "unified_points_db", db)

    @contextmanager
    def _noop():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop)

    created = sdps.create_promo(reward_coins=25, max_redemptions=5)
    code = created["promo"]["code"]
    r = sdps.redeem("shop-promo-user", code)
    assert r.get("success") is True
    assert r.get("reward_coins") == 25
    r2 = sdps.redeem("shop-promo-user", code)
    assert r2.get("error") == "already_redeemed"


def test_discord_link_routes():
    from flask import Flask
    from backend.routes.discord_routes import discord_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(discord_bp)
    with app.test_client() as c:
        r = c.get("/api/discord/link/status?user_id=route-test-user")
        assert r.status_code == 200
        assert r.get_json().get("success") is True
