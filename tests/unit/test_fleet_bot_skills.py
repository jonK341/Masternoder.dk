"""Fleet roster monetization skills — ten-skill set on supervisor bots."""
from backend.services.exchange_fleet_bot_skills_service import (
    FLEET_ROSTER_SKILL_IDS,
    fleet_skills_catalog,
    profit_execution_threshold_bps,
)
from backend.services.exchange_supervisor_fleet_service import default_fleet_bots, fleet_overview, merge_fleet_into_controls


def test_fleet_roster_has_ten_monetization_skills():
    cat = fleet_skills_catalog()
    assert cat["skill_count"] == 10
    assert len(FLEET_ROSTER_SKILL_IDS) == 10
    assert cat["skill_set"]["id"] == "fleet_roster_monetization"


def test_default_fleet_bots_get_skill_meta():
    controls = {"fleet_bots": [], "fleet_meta": {}}
    merge_fleet_into_controls(controls)
    alpha = next(b for b in controls["fleet_bots"] if b["id"] == "fleet_analytics_alpha")
    meta = alpha.get("skill_meta") or {}
    assert meta.get("skill_count", 0) >= 10
    assert float(meta.get("blended_edge_bps") or 0) > 0
    assert "hot_lane_snipe" in (alpha.get("skills") or [])


def test_profit_threshold_lowers_with_skills():
    controls = {"fleet_bots": [], "fleet_meta": {}}
    merge_fleet_into_controls(controls)
    alpha = next(b for b in controls["fleet_bots"] if b["id"] == "fleet_analytics_alpha")
    thr = profit_execution_threshold_bps(alpha, base=10.0)
    assert thr < 10.0
    assert thr >= 5.0


def test_fleet_overview_includes_monetization(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import trading_bots_control_service as ctl

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ctl, "_CONTROL_PATH", str(data / "trading_bots_control.json"))

    controls = ctl._load_controls()
    ov = fleet_overview(controls)
    assert ov["mechanics_count"] == 28
    assert ov.get("fleet_skills", {}).get("skill_count") == 10
    assert ov.get("monetization_skills", {}).get("stream_id") == "fleet-roster-skills"
    assert ov["bots"][0].get("skill_meta")
