"""Fleet XP, levels, and reward unlocks."""
from backend.services.exchange_fleet_progression_service import (
    apply_tick_progression,
    default_progression,
    enrich_fleet_bot,
    fleet_progression_summary,
    level_from_total_xp,
    progression_view,
    xp_gain_for_tick,
)


def test_level_from_total_xp_bands():
    assert level_from_total_xp(0)["level"] == 1
    assert level_from_total_xp(199)["level"] == 1
    assert level_from_total_xp(200)["level"] == 2
    info = level_from_total_xp(250)
    assert info["xp_in_level"] == 50
    assert info["xp_to_next"] == 200


def test_apply_tick_progression_success_and_streak():
    bot = {"id": "fleet_risk_steady", "progression": default_progression()}
    g1 = apply_tick_progression(bot, {"success": True})
    assert g1["xp_gain"] >= 10
    g2 = apply_tick_progression(bot, {"success": True, "executed": True, "executed_count": 1})
    assert bot["progression"]["ok_streak"] >= 2
    assert g2["xp_gain"] > g1["xp_gain"]


def test_reward_unlock_at_level():
    bot = {"id": "x", "progression": {**default_progression(), "total_xp": 400}}
    view = progression_view(bot)
    assert view["level"] >= 3
    unlocked = [r for r in view["rewards"] if r.get("unlocked")]
    assert any(r["id"] == "rookie_clear" for r in unlocked)


def test_enrich_from_account_idempotent():
    bot = {"id": "fleet_analytics_alpha", "progression": default_progression()}
    acct = {"trade_count": 5, "realized_profit_usd": 10.0}
    assert enrich_fleet_bot(bot, acct) is True
    xp1 = bot["progression"]["total_xp"]
    assert enrich_fleet_bot(bot, acct) is False
    assert bot["progression"]["total_xp"] == xp1
    view = progression_view(bot)
    assert view["rank_title"]
    assert "_sync_trade_count" not in view


def test_fleet_progression_summary():
    bots = [
        {"progression": progression_view({"progression": {**default_progression(), "total_xp": 200}})},
        {"progression": progression_view({"progression": {**default_progression(), "total_xp": 0}})},
    ]
    s = fleet_progression_summary(bots)
    assert s["fleet_total_xp"] == 200
    assert s["avg_bot_level"] == 1.5
    assert s["fleet_commander_level"] >= 1


def test_xp_gain_for_tick_executed():
    assert xp_gain_for_tick({"success": True, "executed": True}, ok_streak=1) > xp_gain_for_tick(
        {"success": False}, ok_streak=0
    )
