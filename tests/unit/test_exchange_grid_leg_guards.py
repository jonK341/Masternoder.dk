"""Grid leg guards — thin-quote quiet/resume, per-asset quarantine, universe shrink."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone


def test_quarantine_asset_isolates_pair(tmp_path, monkeypatch):
    data = tmp_path / "crypto_exchange"
    data.mkdir()
    monkeypatch.setenv("LITE_APP", "1")
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_grid_bot_service as g

    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(g, "_STATE_PATH", str(data / "grid_bot_state.json"))
    monkeypatch.setattr(g, "_LEDGER_PATH", str(data / "grid_bot_ledger.jsonl"))
    monkeypatch.setattr(g, "_learn_grid_signal", lambda *a, **k: None)

    st = {
        "BINANCE:XRP": {
            "open_orders": [{"order_id": "1", "side": "buy", "price": 1.0, "size_base": 1}],
            "realized_pnl_usd": -6.5,
            "inventory_base": 0,
            "halted": False,
        }
    }
    (data / "grid_bot_state.json").write_text(json.dumps(st))
    out = g.quarantine_asset("binance", "XRP", reason="hard_loss", realized_usd=-6.5)
    assert out["quarantined"] is True
    qa = g.quarantined_assets()
    assert "BINANCE:XRP" in qa
    loaded = json.loads((data / "grid_bot_state.json").read_text())
    assert loaded["BINANCE:XRP"]["halted"] is True
    assert loaded["BINANCE:XRP"]["open_orders"] == []
    ledger = (data / "grid_bot_ledger.jsonl").read_text()
    assert "asset_quarantine" in ledger


def test_thin_quote_resume_clears_non_manual_pause(tmp_path, monkeypatch):
    data = tmp_path / "crypto_exchange"
    data.mkdir()
    monkeypatch.setenv("LITE_APP", "1")
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_grid_bot_service as g

    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(g, "_STATE_PATH", str(data / "grid_bot_state.json"))
    monkeypatch.setattr(g, "_LEDGER_PATH", str(data / "grid_bot_ledger.jsonl"))
    monkeypatch.setattr(g, "_CFG_PATH", str(data / "exchange_grid_bot_config.json"))
    monkeypatch.setattr(g, "_learn_grid_signal", lambda *a, **k: None)
    monkeypatch.setattr(g, "grid_targets", lambda cfg=None: [("binance", "ADA")])
    monkeypatch.setattr(g, "grid_profit", lambda: {"assets": {}, "realized_pnl_usd": 0.0})
    monkeypatch.setattr(g, "reset_open_orders", lambda venue=None: {"cleared_orders": 0})

    (data / "exchange_grid_bot_config.json").write_text(json.dumps({
        "enabled": True, "order_size_usd": 6.0, "hard_loss_cap_usd": 5.0,
        "assets": ["ADA"], "venue": "binance",
    }))
    (data / "grid_bot_state.json").write_text(json.dumps({
        "paused_venues": {
            "binance": {
                "reason": "thin_quote",
                "manual": False,
                "paused_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
            }
        }
    }))

    import backend.services.exchange_venue_api_service as vapi_mod

    monkeypatch.setattr(vapi_mod, "venue_quote_asset", lambda venue: "USDC")
    monkeypatch.setattr(
        vapi_mod,
        "parse_spot_balances",
        lambda venue, dry_run=False, force_refresh=False: {"USDC": 50.0},
    )

    res = g.apply_quote_and_loss_guards(g.load_config())
    assert res["success"] is True
    assert "binance" in (res.get("reseed_venues") or [])
    assert "binance" not in g.paused_venues()
