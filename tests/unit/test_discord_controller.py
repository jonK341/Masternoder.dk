"""Discord controller — link, earn, slash commands."""
from __future__ import annotations

import os
import tempfile

import pytest


@pytest.fixture
def controller_state(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        state_dir = os.path.join(tmp, "dc")
        os.makedirs(state_dir, exist_ok=True)
        import backend.services.discord_controller_service as svc

        monkeypatch.setattr(svc, "_STATE_DIR", state_dir)
        monkeypatch.setattr(svc, "_USERS_PATH", os.path.join(state_dir, "users.json"))
        monkeypatch.setattr(svc, "_CODES_PATH", os.path.join(state_dir, "link_codes.json"))
        yield svc


def test_link_code_flow(controller_state, monkeypatch):
    svc = controller_state
    monkeypatch.setattr(
        "backend.services.discord_link_service.link_user",
        lambda uid, did: {"success": True, "user_id": uid, "discord_id": did},
    )
    monkeypatch.setattr(
        "backend.services.game_mn2_rewards.credit_mn2",
        lambda uid, amt, **kw: {"success": True, "amount": amt, "user_id": uid},
    )
    code_out = svc.create_link_code("site_user_1")
    assert code_out["success"] is True
    link = svc.complete_link_with_code("discord_999", code_out["code"])
    assert link["success"] is True
    welcome = link.get("welcome_reward") or {}
    assert welcome.get("first_time") is True
    assert welcome.get("granted_mn2") == 50.0
    link2 = svc.complete_link_with_code("discord_999", svc.create_link_code("site_user_2")["code"])
    assert (link2.get("welcome_reward") or {}).get("already_claimed") is True


def test_new_user_reward_idempotent(controller_state, monkeypatch):
    svc = controller_state
    monkeypatch.setattr(
        "backend.services.game_mn2_rewards.credit_mn2",
        lambda uid, amt, **kw: {"success": True, "amount": amt},
    )
    first = svc.grant_discord_new_user_reward("player_welcome", "discord_welcome_1")
    assert first["success"] is True
    assert first["granted_mn2"] == 50.0
    second = svc.grant_discord_new_user_reward("player_welcome", "discord_welcome_1")
    assert second.get("already_claimed") is True
    assert second.get("granted_mn2") == 0.0


def test_casino_play_earn_linked(controller_state, monkeypatch):
    svc = controller_state
    monkeypatch.setattr(
        "backend.services.discord_link_service.get_discord_id_for_user",
        lambda uid: "discord_42" if uid == "player1" else None,
    )
    monkeypatch.setattr(
        "backend.services.unified_points_database.unified_points_db.add_points",
        lambda *a, **k: {"success": True},
    )
    out = svc.record_casino_play_earn("player1", game="crash", outcome="win", net=50, currency="coins")
    assert out["success"] is True
    assert out.get("granted_coins", 0) > 0


def test_slash_casino_command(controller_state):
    svc = controller_state
    resp = svc.handle_slash_command("casino", "discord_1", {})
    assert resp["type"] == 4
    assert "Casino" in resp["data"]["content"] or "casino" in resp["data"]["content"].lower()


def test_app_manifest(controller_state):
    svc = controller_state
    m = svc.get_app_manifest()
    assert m["success"] is True
    ids = {a["id"] for a in m.get("activities") or []}
    assert "casino_social" in ids
    assert "hosting" in ids
