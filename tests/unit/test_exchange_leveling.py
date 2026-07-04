"""Trader leveling, rewards, achievements and agent game-time/levels."""
import pytest


@pytest.fixture
def lvl_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_leveling_service as lvl

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(lvl, "_STATE_DIR", str(data / "exchange_leveling"))

    credits = []
    monkeypatch.setattr(ex, "_adjust_quote_balance",
                        lambda uid, q, delta, source, meta=None: credits.append((uid, q, delta, source)))
    return {"ex": ex, "lvl": lvl, "credits": credits}


def test_level_for_xp_curve(lvl_env):
    lvl = lvl_env["lvl"]
    assert lvl.level_for_xp(0)["level"] == 1
    assert lvl.level_for_xp(50)["level"] == 1
    assert lvl.level_for_xp(100)["level"] == 2
    high = lvl.level_for_xp(5000)
    assert high["level"] > 5
    assert 0 <= high["progress_pct"] <= 100


def test_award_xp_and_level_up(lvl_env):
    lvl = lvl_env["lvl"]
    r1 = lvl.award_xp("u1", 60, "buy_crypto")
    assert r1["success"] is True
    assert r1["level"] == 1
    r2 = lvl.award_xp("u1", 60, "buy_crypto")
    assert r2["leveled_up"] is True
    assert r2["level"] == 2


def test_agent_purchase_unlocks_first_agent_achievement(lvl_env):
    lvl = lvl_env["lvl"]
    res = lvl.record_agent_purchase("u1", premium=True)
    ids = {a["id"] for a in res["new_achievements"]}
    assert "first_agent" in ids
    assert "premium_elite" in ids
    prog = lvl.user_progress("u1")
    assert prog["stats"]["agents_owned"] == 1
    assert prog["stats"]["premium_owned"] == 1


def test_agent_tick_accrues_game_time_and_profit_achievement(lvl_env):
    lvl = lvl_env["lvl"]
    res = lvl.record_agent_tick("u1", 150.0, tick_seconds=3600)
    ids = {a["id"] for a in res["new_achievements"]}
    assert "profit_century" in ids
    prog = lvl.user_progress("u1")
    assert prog["stats"]["total_game_time_sec"] == 3600
    assert prog["stats"]["total_ticks"] == 1
    assert prog["stats"]["total_agent_profit_usd"] == pytest.approx(150.0)


def test_claim_level_reward_once(lvl_env):
    lvl = lvl_env["lvl"]
    lvl.award_xp("u1", 500, "seed")  # ensure >= level 2
    claim = lvl.claim_level_reward("u1", 2)
    assert claim["success"] is True
    assert claim["reward_mn2"] > 0
    again = lvl.claim_level_reward("u1", 2)
    assert again.get("already_claimed") is True
    too_high = lvl.claim_level_reward("u1", 999)
    assert too_high["success"] is False


def test_agent_level_and_edge_bonus(lvl_env):
    lvl = lvl_env["lvl"]
    assert lvl.agent_level_for_xp(0) == 1
    assert lvl.agent_level_for_xp(10000) > 3
    bonus_lo = lvl.agent_edge_bonus_bps(1)
    bonus_hi = lvl.agent_edge_bonus_bps(10)
    assert bonus_lo == 0
    assert bonus_hi > bonus_lo


def test_user_progress_shape(lvl_env):
    lvl = lvl_env["lvl"]
    prog = lvl.user_progress("u_new")
    assert prog["success"] is True
    assert prog["level"] == 1
    assert prog["rank"]["name"]
    assert prog["achievements_total"] >= 10
    assert isinstance(prog["achievements"], list)
