"""P0 round 2: PoR external coverage + float gate + collateral helpers."""

from __future__ import annotations

import backend.services.mn2_float_gate as fg
import backend.services.mn2_proof_of_reserves_service as por
from backend.services import mn2_masternode_service as mn


def test_internal_ledger_user_classification():
    assert por._is_internal_ledger_user("agent_treasury") is True
    assert por._is_internal_ledger_user("exchange_agent_casino_liquidity") is True
    assert por._is_internal_ledger_user("trader_agent_6") is True
    assert por._is_internal_ledger_user("platform_treasury") is True
    assert por._is_internal_ledger_user("user_jon_ulrik") is False
    assert por._is_internal_ledger_user("Sander Sahk") is False


def test_float_gate_uses_passed_hot_balance(monkeypatch):
    monkeypatch.setattr(fg, "_p95_daily_outflow_mn2", lambda: 0.0)
    monkeypatch.setattr(fg, "_external_liabilities_total", lambda: 1000.0)
    monkeypatch.setattr(fg, "_hot_wallet_balance", lambda: (_ for _ in ()).throw(AssertionError("should not call")))
    out = fg.assess(10, hot_mn2=5000.0)
    assert out["allowed"] is True
    assert out["hot_mn2"] == 5000.0
    assert out["external_coverage_ratio"] == 5.0
    assert out["verdict"] == "green"


def test_float_gate_blocks_large_when_under_external_coverage(monkeypatch):
    monkeypatch.setattr(fg, "_p95_daily_outflow_mn2", lambda: 0.0)
    monkeypatch.setattr(fg, "_external_liabilities_total", lambda: 10_000_000.0)
    out = fg.assess(60_000, hot_mn2=1000.0)
    assert out["allowed"] is False
    assert out["code"] == "external_coverage_insufficient"


def test_float_gate_fails_closed_for_large_when_oracle_down(monkeypatch):
    monkeypatch.setattr(fg, "_p95_daily_outflow_mn2", lambda: 0.0)
    monkeypatch.setattr(fg, "_hot_wallet_balance", lambda: None)
    monkeypatch.setattr(fg, "_external_liabilities_total", lambda: None)
    out = fg.assess(60_000, hot_mn2=None)
    assert out["allowed"] is False
    assert out["code"] == "float_oracle_unavailable"


def test_list_collateral_excludes_conf_and_registry(monkeypatch, tmp_path):
    # local setup
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    conf_dir = tmp_path / "config"
    conf_dir.mkdir()
    (conf_dir / "masternode.conf").write_text(
        "platformmn2 127.0.0.1:17646 KEYAAA usedtxid0000000000000000000000000000000000000000000000000001 0\n",
        encoding="utf-8",
    )
    (data_dir / "mn2_masternode_config.json").write_text(
        '{"collateral_mn2": 5000, "max_hosted_nodes": 50, "ops": {"datadir": "%s"}}'
        % str(conf_dir).replace("\\", "\\\\"),
        encoding="utf-8",
    )
    (data_dir / "mn2_masternode_hosts.json").write_text(
        '{"hosts":[{"id":"h1","status":"active","collateral_txid":"hosttxid0000000000000000000000000000000000000000000000000002","collateral_vout":1}]}',
        encoding="utf-8",
    )

    def _data_path(name: str) -> str:
        return str(data_dir / name)

    monkeypatch.setattr(mn, "_data_path", _data_path)
    monkeypatch.setattr(mn, "_masternode_conf_path", lambda: str(conf_dir / "masternode.conf"))

    class Rpc:
        @staticmethod
        def listunspent(a, b):
            return {
                "result": [
                    {"txid": "usedtxid0000000000000000000000000000000000000000000000000001", "vout": 0, "amount": 5000},
                    {"txid": "hosttxid0000000000000000000000000000000000000000000000000002", "vout": 1, "amount": 5000},
                    {"txid": "freetxid0000000000000000000000000000000000000000000000000003", "vout": 0, "amount": 5000},
                    {"txid": "other", "vout": 0, "amount": 1.5},
                ],
                "error": None,
            }

        @staticmethod
        def listlockunspent():
            return {"result": [], "error": None}

    monkeypatch.setattr("backend.services.mn2_rpc_client.listunspent", Rpc.listunspent)
    monkeypatch.setattr("backend.services.mn2_rpc_client.listlockunspent", Rpc.listlockunspent)

    out = mn.list_collateral_outputs()
    assert out["success"] is True
    assert out["count"] == 1
    assert out["outputs"][0]["txid"].startswith("freetxid")
