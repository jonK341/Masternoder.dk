"""Supervisor fleet bots — counts and merge."""
import pytest


def test_default_fleet_counts():
    from backend.services.exchange_supervisor_fleet_service import default_fleet_bots

    bots = default_fleet_bots()
    kinds = {}
    for b in bots:
        kinds[b["kind"]] = kinds.get(b["kind"], 0) + 1
    assert kinds.get("analytics") == 5
    assert kinds.get("extended_profit") == 6
    assert kinds.get("treasury") == 3
    assert kinds.get("risk") == 5
    assert kinds.get("winnable_pairs") == 4
    assert len(bots) == 23


def test_fleet_merge_into_controls(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import trading_bots_control_service as ctl
    from backend.services.exchange_supervisor_fleet_service import merge_fleet_into_controls, fleet_overview

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ctl, "_CONTROL_PATH", str(data / "trading_bots_control.json"))

    controls = ctl._load_controls()
    ov = fleet_overview(controls)
    assert ov["mechanics_count"] == 27
    assert len(ov["bots"]) == 23
    assert "progression_summary" in ov
    assert ov["bots"][0].get("progression", {}).get("level") == 1


def test_fleet_ops_meta_on_tick(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import trading_bots_control_service as ctl
    from backend.services.exchange_supervisor_fleet_service import (
        fleet_overview,
        run_fleet_tick,
    )

    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ctl, "_CONTROL_PATH", str(data / "trading_bots_control.json"))

    controls = ctl._load_controls()
    run_fleet_tick(controls, kind="risk")
    ov = fleet_overview(controls)
    assert ov["health"]["bot_count"] == 23
    assert ov["meta"].get("last_run_at")
    assert ov["meta"].get("last_results", {}).get("risk")


def test_fleet_bot_labels():
    from backend.services.exchange_supervisor_fleet_service import default_fleet_bots

    bots = default_fleet_bots()
    alpha = next(b for b in bots if b["id"] == "fleet_analytics_alpha")
    assert alpha["label"] == "PA-α"
    assert alpha["name"] == "Profit Analyst Alpha"
    assert alpha["type_label"] == "Profit Analyst"
    assert alpha["supervisor_name"] == "Profit Analyst"
    ext = next(b for b in bots if b["label"] == "EXT-1")
    assert ext["supervisor_name"] == "Extended Profit Director"
