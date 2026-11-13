"""Profit daemon head — limb control, learning ledger, kill-shot."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def head_env(tmp_path, monkeypatch):
    data = tmp_path / "crypto_exchange"
    data.mkdir()
    (tmp_path / "logs").mkdir()
    monkeypatch.setenv("LITE_APP", "1")

    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_profit_head_service as head

    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_BASE", str(tmp_path))
    monkeypatch.setattr(head, "_CONTROL_PATH", str(data / "profit_head_control.json"))
    monkeypatch.setattr(head, "_STATE_PATH", str(data / "profit_head_state.json"))
    monkeypatch.setattr(head, "_LEDGER_PATH", str(data / "profit_head_ledger.jsonl"))
    monkeypatch.setattr(
        head,
        "_HEARTBEAT_CANDIDATES",
        [str(tmp_path / "logs" / "daemon_all_profit_heartbeat.json")],
    )
    # Fake quote snapshot — thin by default
    monkeypatch.setattr(
        head,
        "_venue_quote_snapshot",
        lambda: {
            "binance": {"ok": True, "quote": "USDC", "free": 4.0},
            "nonkyc": {"ok": True, "quote": "USDT", "free": 0.0},
        },
    )
    monkeypatch.setattr(head, "_pbook_top", lambda: None)
    monkeypatch.setattr(head, "_search_hot_symbols", lambda: ["ADA", "LINK"])
    monkeypatch.setattr(head, "_read_heartbeat", lambda: {"loops": {}})
    return head, data


def test_head_gates_grid_when_thin(head_env):
    head, data = head_env
    res = head.run_head_tick(force=True)
    assert res["success"] is True
    assert res["limbs"]["grid"]["enabled"] is False
    assert res["limbs"]["pbook"]["enabled"] is True
    assert any(d.startswith("quote_gate:grid_quiet") for d in res["decisions"])
    ctrl = json.loads((data / "profit_head_control.json").read_text())
    assert ctrl["limbs"]["grid"]["enabled"] is False
    assert head.limb_allowed("grid") is False
    assert head.limb_allowed("pbook") is True
    ledger = (data / "profit_head_ledger.jsonl").read_text().strip().splitlines()
    assert ledger
    assert json.loads(ledger[-1])["kind"] == "head_tick"


def test_head_kill_shot_from_funded_pbook(head_env, monkeypatch):
    head, data = head_env
    monkeypatch.setattr(
        head,
        "_venue_quote_snapshot",
        lambda: {
            "binance": {"ok": True, "quote": "USDC", "free": 40.0},
            "nonkyc": {"ok": True, "quote": "USDT", "free": 40.0},
        },
    )
    monkeypatch.setattr(
        head,
        "_pbook_top",
        lambda: {
            "symbol": "CRV",
            "route": "CRV:binance→nonkyc",
            "net_bps": 80.0,
            "est_profit_usd": 0.12,
            "funded": True,
            "best_technique": "prefund_buy_quote",
        },
    )
    res = head.run_head_tick(force=True)
    assert res["limbs"]["grid"]["enabled"] is True
    assert res["kill_shot"]["symbol"] == "CRV"
    assert res["kill_shot"]["arm"] == "hunter"
    assert head.get_kill_shot()["symbol"] == "CRV"


def test_manual_body_pause_kill_switch(head_env):
    head, _data = head_env
    head.set_manual_body_pause(True)
    assert head.limb_allowed("hunter") is False
    assert head.limb_allowed("pbook") is True
    res = head.run_head_tick(force=True)
    assert res["manual_body_pause"] is True
    assert any("kill_switch" in d for d in res["decisions"])
    head.set_manual_body_pause(False)
