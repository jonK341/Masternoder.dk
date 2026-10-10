"""Unit tests for MasterNoder2 spork helpers (mn2_spork_service)."""
from __future__ import annotations

import time

import pytest

from backend.services import mn2_rpc_client as rpc
from backend.services import mn2_spork_service as spork


@pytest.mark.unit
def test_spork_id_name_roundtrip():
    for name, spork_id in spork.SPORK_IDS.items():
        assert spork.spork_id_by_name(name) == spork_id
        assert spork.spork_name_by_id(spork_id) == name


@pytest.mark.unit
def test_is_spork_active_matches_cpp_semantics():
    now = 1_700_000_000  # fixed reference
    assert spork.is_spork_active(1_699_999_999, now=now) is True
    assert spork.is_spork_active(1_700_000_000, now=now) is False
    assert spork.is_spork_active(spork.SPORK_OFF, now=now) is False
    assert spork.is_spork_active(-1, now=now) is False


@pytest.mark.unit
def test_default_spork_8_payment_enforcement_is_off():
    val = spork.SPORK_DEFAULTS["SPORK_8_MASTERNODE_PAYMENT_ENFORCEMENT"]
    assert val == spork.SPORK_OFF
    assert spork.is_spork_off(val) is True
    assert spork.is_spork_active(val) is False


@pytest.mark.unit
def test_default_spork_106_staking_skip_is_active_in_2026():
    val = spork.SPORK_DEFAULTS["SPORK_106_STAKING_SKIP_MN_SYNC"]
    assert val == 1_703_122_560
    assert spork.is_spork_active(val, now=int(time.time())) is True


@pytest.mark.unit
def test_interpret_spork_summary():
    out = spork.interpret_spork(
        "SPORK_8_MASTERNODE_PAYMENT_ENFORCEMENT",
        spork.SPORK_OFF,
        now=1_700_000_000,
    )
    assert out["active"] is False
    assert out["off"] is True
    assert out["default"] == spork.SPORK_OFF


@pytest.mark.unit
def test_show_sporks_rpc_wrapper(monkeypatch):
    monkeypatch.setattr(
        rpc,
        "_call",
        lambda method, params, timeout_sec=None: {
            "result": {
                "SPORK_8_MASTERNODE_PAYMENT_ENFORCEMENT": spork.SPORK_OFF,
            },
            "error": None,
        },
    )
    res = spork.show_sporks()
    assert res["error"] is None
    assert res["result"]["SPORK_8_MASTERNODE_PAYMENT_ENFORCEMENT"] == spork.SPORK_OFF


@pytest.mark.unit
def test_active_sporks_rpc_wrapper(monkeypatch):
    monkeypatch.setattr(
        rpc,
        "_call",
        lambda method, params, timeout_sec=None: {
            "result": {
                "SPORK_8_MASTERNODE_PAYMENT_ENFORCEMENT": False,
                "SPORK_106_STAKING_SKIP_MN_SYNC": True,
            },
            "error": None,
        },
    )
    res = spork.active_sporks()
    assert res["error"] is None
    assert res["result"]["SPORK_8_MASTERNODE_PAYMENT_ENFORCEMENT"] is False


@pytest.mark.unit
def test_update_spork_rejects_unknown_name():
    res = spork.update_spork("SPORK_999_NOT_REAL", 123)
    assert res["result"] is None
    assert "unknown spork" in (res.get("error") or "")


@pytest.mark.unit
def test_spork_ids_include_ops_gates():
    for name in (
        "SPORK_112_EXCHANGE_LIVE_TRADING",
        "SPORK_113_CASINO_REAL_MONEY",
        "SPORK_114_PAYOUT_LIVE",
        "SPORK_115_MAINTENANCE_MODE",
    ):
        assert name in spork.SPORK_IDS
        assert name in spork.SPORK_DEFAULTS


@pytest.mark.unit
def test_exchange_live_spork_gate(monkeypatch):
    monkeypatch.setenv("MN2_SPORK_GATES", "1")
    monkeypatch.setenv(
        "MN2_SPORK_OVERRIDE_JSON",
        '{"SPORK_112_EXCHANGE_LIVE_TRADING": %d}' % spork.SPORK_OFF,
    )
    spork.invalidate_cache()
    ok, reason = spork.exchange_live_spork_ok()
    assert ok is False
    assert reason == "spork_exchange_live_off"


@pytest.mark.unit
def test_maintenance_mode_blocks_exchange(monkeypatch):
    monkeypatch.setenv("MN2_SPORK_GATES", "1")
    past = int(time.time()) - 3600
    monkeypatch.setenv(
        "MN2_SPORK_OVERRIDE_JSON",
        '{"SPORK_115_MAINTENANCE_MODE": %d, "SPORK_112_EXCHANGE_LIVE_TRADING": %d}'
        % (past, past),
    )
    spork.invalidate_cache()
    ok, reason = spork.exchange_live_spork_ok()
    assert ok is False
    assert reason == "maintenance_mode"


@pytest.mark.unit
def test_casino_real_money_default_active(monkeypatch):
    monkeypatch.delenv("MN2_SPORK_OVERRIDE_JSON", raising=False)
    spork.invalidate_cache()
    val = spork.SPORK_DEFAULTS["SPORK_113_CASINO_REAL_MONEY"]
    assert spork.is_spork_active(val, now=int(time.time())) is True
    monkeypatch.setenv("MN2_SPORK_GATES", "1")
    monkeypatch.setenv(
        "MN2_SPORK_OVERRIDE_JSON",
        '{"SPORK_113_CASINO_REAL_MONEY": %d}' % spork.SPORK_OFF,
    )
    spork.invalidate_cache()
    ok, reason = spork.casino_real_money_spork_ok()
    assert ok is False
    assert reason == "spork_casino_real_money_off"


@pytest.mark.unit
def test_payout_live_spork_off_by_default(monkeypatch):
    monkeypatch.setenv("MN2_SPORK_GATES", "1")
    monkeypatch.setenv(
        "MN2_SPORK_OVERRIDE_JSON",
        '{"SPORK_114_PAYOUT_LIVE": %d}' % spork.SPORK_OFF,
    )
    spork.invalidate_cache()
    ok, reason = spork.payout_live_spork_ok()
    assert ok is False
    assert reason == "spork_payout_live_off"


@pytest.mark.unit
def test_gate_status_snapshot(monkeypatch):
    monkeypatch.setenv("MN2_SPORK_GATES", "1")
    past = int(time.time()) - 3600
    monkeypatch.setenv(
        "MN2_SPORK_OVERRIDE_JSON",
        '{"SPORK_112_EXCHANGE_LIVE_TRADING": %d, "SPORK_114_PAYOUT_LIVE": %d}'
        % (past, past),
    )
    spork.invalidate_cache()
    status = spork.gate_status()
    assert status["exchange_live"]["allowed"] is True
    assert status["payout_live"]["allowed"] is True


@pytest.mark.unit
def test_spork_gates_bypass_env(monkeypatch):
    monkeypatch.setenv("MN2_SPORK_GATES", "0")
    monkeypatch.setenv(
        "MN2_SPORK_OVERRIDE_JSON",
        '{"SPORK_112_EXCHANGE_LIVE_TRADING": %d}' % spork.SPORK_OFF,
    )
    spork.invalidate_cache()
    ok, _ = spork.exchange_live_spork_ok()
    assert ok is True


@pytest.mark.unit
def test_update_spork_calls_rpc(monkeypatch):
    seen = {}

    def fake_call(method, params, timeout_sec=None):
        seen["method"] = method
        seen["params"] = params
        return {"result": "success", "error": None}

    monkeypatch.setattr(rpc, "_call", fake_call)
    res = spork.update_spork("SPORK_8_MASTERNODE_PAYMENT_ENFORCEMENT", spork.SPORK_OFF)
    assert res["result"] == "success"
    assert seen == {
        "method": "spork",
        "params": ["SPORK_8_MASTERNODE_PAYMENT_ENFORCEMENT", spork.SPORK_OFF],
    }
