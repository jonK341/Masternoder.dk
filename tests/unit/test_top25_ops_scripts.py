"""Light ops scripts — prefund rotation and payout sweep status."""
import json
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def script_env(tmp_path, monkeypatch):
    data = tmp_path / "crypto_exchange"
    data.mkdir(parents=True)
    monkeypatch.setenv("DAEMON_QUIET", "1")
    monkeypatch.setenv("LITE_APP", "1")
    return {"data": data}


def test_prefund_list_no_actions(script_env, monkeypatch):
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.suggest_swap_actions",
        lambda **kw: {"actions": [], "funding_skip_count": 0},
    )
    from scripts import prefund_arb_legs as pf

    import sys

    monkeypatch.setattr(sys, "argv", ["prefund_arb_legs.py"])
    assert pf.main() == 1


def test_prefund_dry_run_top_action(script_env, monkeypatch, capsys):
    action = {
        "label": "Buy DOGE on nonkyc ~$23",
        "type": "external_market_buy",
        "venue_id": "nonkyc",
        "symbol": "DOGE",
        "side": "buy",
        "amount_usd": 23.0,
        "priority": "high",
    }
    exec_result = {"success": True, "dry_run": True, "mode": "paper", "baseline_id": None}

    from scripts import prefund_arb_legs as pf

    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.suggest_swap_actions",
        lambda **kw: {"actions": [action], "funding_skip_count": 5},
    )
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.execute_rotation",
        lambda act, dry_run=True: exec_result,
    )
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.rotation_live_enabled",
        lambda: False,
    )

    import sys

    monkeypatch.setattr(sys, "argv", ["prefund_arb_legs.py"])
    assert pf.main() == 0
    out = capsys.readouterr().out
    assert "Buy DOGE" in out
    assert "dry-run" in out
    assert "external_market_buy" in out


def test_prefund_symbol_filter_skips_sell(script_env, monkeypatch, capsys):
    """--symbol DOGE --leg buy must not execute external_market_sell (sell-leg inventory)."""
    buy = {
        "label": "Buy DOGE on nonkyc (DOGE/USDT) ~$23",
        "type": "external_market_buy",
        "venue_id": "nonkyc",
        "symbol": "DOGE",
        "side": "buy",
        "amount_usd": 23.0,
        "priority": "critical",
    }
    sell = {
        "label": "Sell DOGE on nonkyc (DOGE/USDT) for USDT ~$6",
        "type": "external_market_sell",
        "venue_id": "nonkyc",
        "symbol": "DOGE",
        "side": "sell",
        "amount_usd": 5.78,
        "priority": "high",
    }
    captured = {}

    def _exec(act, dry_run=True):
        captured["type"] = act.get("type")
        captured["side"] = act.get("side")
        return {"success": True, "dry_run": dry_run, "mode": "live"}

    from scripts import prefund_arb_legs as pf

    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.suggest_swap_actions",
        lambda **kw: {"actions": [sell, buy], "funding_skip_count": 3},
    )
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.execute_rotation",
        _exec,
    )
    monkeypatch.setattr(
        "backend.services.exchange_swap_rotation_service.rotation_live_enabled",
        lambda: True,
    )

    import sys

    monkeypatch.setattr(sys, "argv", ["prefund_arb_legs.py", "--symbol", "DOGE", "--leg", "buy"])
    assert pf.main() == 0
    assert captured["type"] == "external_market_buy"
    assert captured["side"] == "buy"
    out = capsys.readouterr().out
    assert "Will execute action [0]" in out
    assert "external_market_buy" in out
    assert "filtered from 2" in out


def test_filter_prefund_actions_unit():
    from scripts.prefund_arb_legs import filter_prefund_actions

    actions = [
        {"type": "external_market_sell", "venue_id": "nonkyc", "symbol": "DOGE", "side": "sell"},
        {"type": "external_market_buy", "venue_id": "nonkyc", "symbol": "DOGE", "side": "buy"},
        {"type": "external_market_buy", "venue_id": "binance", "symbol": "DOGE", "side": "buy"},
    ]
    out = filter_prefund_actions(actions, symbol="DOGE", leg="buy")
    assert len(out) == 1
    assert out[0]["type"] == "external_market_buy"
    assert out[0]["venue_id"] == "nonkyc"


def test_payout_sweep_status_collect(script_env, monkeypatch):
    fake_status = {
        "success": True,
        "destination": "paypal",
        "mode": "paper",
        "ready_to_sweep": False,
        "auto_sweep": False,
        "min_sweep_usd": 500.0,
        "net_unswept_usd": 572.0,
        "paypal_sweepable_usd": 286.0,
        "realized_total_usd": 1000.0,
        "swept_total_usd": 428.0,
        "treasury_stashed_usd": 0.0,
        "paypal": {"connected": True, "live_enabled": False},
    }
    monkeypatch.setattr(
        "backend.services.exchange_payout_service.payout_status",
        lambda: fake_status,
    )
    from scripts import payout_sweep_status as ps

    out = ps._collect()
    assert out["destination"] == "paypal"
    assert out["ready_to_sweep"] is False
    assert out["min_sweep_usd"] == 500.0
    assert out["usd_to_threshold"] == 214.0
    assert "auto-sweep" in out["auto_sweep_hint"]


def test_payout_sweep_status_json(script_env, monkeypatch, capsys):
    monkeypatch.setattr(
        "backend.services.exchange_payout_service.payout_status",
        lambda: {
            "success": True,
            "destination": "paypal",
            "mode": "paper",
            "ready_to_sweep": True,
            "auto_sweep": False,
            "min_sweep_usd": 500.0,
            "net_unswept_usd": 600.0,
            "paypal_sweepable_usd": 300.0,
            "realized_total_usd": 1200.0,
            "swept_total_usd": 600.0,
            "treasury_stashed_usd": 0.0,
            "paypal": {"connected": True, "live_enabled": False},
        },
    )
    from scripts import payout_sweep_status as ps

    import sys

    monkeypatch.setattr(sys, "argv", ["payout_sweep_status.py", "--json"])
    assert ps.main() == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ready_to_sweep"] is True
    assert data["paypal_sweepable_usd"] == 300.0
