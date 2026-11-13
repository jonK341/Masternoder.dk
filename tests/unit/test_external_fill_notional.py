"""External fill blockers: micro notional recovery + live prepare floor bump."""
from __future__ import annotations

import json
import os


def test_maybe_scale_paper_trade_recovers_micro_without_caps(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import profit_daemon_ops_service as ops

    cfg_path = tmp_path / "exchange_connectors_config.json"
    cfg_path.write_text(json.dumps({"paper_trade_usd": 0.01}), encoding="utf-8")
    monkeypatch.setattr(ops, "_CONNECTORS_PATH", str(cfg_path))
    monkeypatch.setattr(ex, "_write_json", lambda path, data: cfg_path.write_text(json.dumps(data), encoding="utf-8"))
    monkeypatch.setattr(ex, "_read_json", lambda path, default=None: json.loads(cfg_path.read_text(encoding="utf-8")))
    monkeypatch.delenv("EXCHANGE_AUTO_SCALE_NOTIONAL", raising=False)
    monkeypatch.setenv("EXCHANGE_PAPER_TRADE_FLOOR_USD", "10")

    out = ops.maybe_scale_paper_trade_usd({"platform": {"results": {"arbitrage": {}}}})
    assert out.get("success") is True
    assert out.get("paper_trade_usd") == 10.0
    assert out.get("previous") == 0.01
    assert out.get("source") == "floor_recover"
    saved = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert saved["paper_trade_usd"] == 10.0


def test_maybe_scale_paper_trade_scales_down_to_funding(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import profit_daemon_ops_service as ops

    cfg_path = tmp_path / "exchange_connectors_config.json"
    cfg_path.write_text(json.dumps({"paper_trade_usd": 75.0}), encoding="utf-8")
    monkeypatch.setattr(ops, "_CONNECTORS_PATH", str(cfg_path))
    monkeypatch.setattr(ex, "_write_json", lambda path, data: cfg_path.write_text(json.dumps(data), encoding="utf-8"))
    monkeypatch.setattr(ex, "_read_json", lambda path, default=None: json.loads(cfg_path.read_text(encoding="utf-8")))
    monkeypatch.delenv("EXCHANGE_AUTO_SCALE_NOTIONAL", raising=False)
    monkeypatch.setenv("EXCHANGE_PAPER_TRADE_FLOOR_USD", "10")

    exchange_res = {
        "platform": {
            "results": {
                "arbitrage": {
                    "actions": [{"max_funded_usd": 22.0}],
                }
            }
        }
    }
    out = ops.maybe_scale_paper_trade_usd(exchange_res)
    assert out.get("success") is True
    assert out.get("paper_trade_usd") == 20.9
    assert out.get("source") == "max_funded_usd"


def test_prepare_live_opportunity_bumps_micro_configured(monkeypatch):
    """$0.01 configured should still attempt at min_live when funding allows."""
    from backend.services import exchange_arbitrage_service as arb

    opp = {
        "symbol": "LINK",
        "buy_venue": "binance",
        "buy_ask": 10.0,
        "sell_venue": "nonkyc",
        "sell_bid": 10.05,
        "net_bps": 40.0,
        "notional_usd": 0.01,
        "est_profit_usd": 0.01,
    }
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.max_funded_notional_usd",
        lambda *a, **kw: 50.0,
    )
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.opportunity_funded",
        lambda opp, **kw: {"ok": True},
    )
    prepared = arb.prepare_live_opportunity(opp, configured_usd=0.01, min_live_usd=10.0)
    assert prepared["ok"] is True
    assert prepared["opportunity"]["notional_usd"] == 10.0
    assert prepared["max_funded_usd"] == 50.0
