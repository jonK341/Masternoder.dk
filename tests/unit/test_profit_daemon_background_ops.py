"""Profit daemon background ops and payout env sync."""
from __future__ import annotations

import json
import os


def test_sync_auto_sweep_from_env_updates_config(monkeypatch, tmp_path):
    from backend.services import exchange_payout_service as pay

    data_dir = tmp_path / "crypto_exchange"
    data_dir.mkdir(parents=True)
    cfg_path = data_dir / "payout_config.json"
    cfg_path.write_text(
        json.dumps(
            {
                "destination": "paypal",
                "paypal": {"email": "", "share_pct": 1.0},
                "min_sweep_usd": 500.0,
                "auto_sweep": False,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(pay, "_PAYOUT_PATH", str(cfg_path))
    monkeypatch.setenv("EXCHANGE_AUTO_PAYPAL_SWEEP", "1")
    monkeypatch.setenv("EXCHANGE_AUTO_SWEEP_MIN_USD", "25")
    monkeypatch.setenv("EXCHANGE_PAYOUT_PAYPAL_EMAIL", "owner@example.com")

    out = pay.sync_auto_sweep_from_env()
    assert out.get("changed") is True
    assert out.get("auto_sweep") is True
    saved = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert saved["auto_sweep"] is True
    assert saved["min_sweep_usd"] == 25.0
    assert saved["paypal"]["email"] == "owner@example.com"


def test_profit_daemon_health_probe_fresh_heartbeat(monkeypatch, tmp_path):
    from backend.services import profit_daemon_background_ops_service as bg

    hb = tmp_path / "hb.json"
    hb.write_text(
        json.dumps({"updated_at": "2099-01-01T00:00:00Z", "profile": "max"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(bg, "heartbeat_path", lambda: str(hb))
    out = bg.profit_daemon_health_probe()
    assert out.get("status") == "healthy"
    assert out.get("success") is True


def test_maybe_paypal_auto_sweep_executes_when_ready(monkeypatch):
    from backend.services.profit_daemon_ops_service import maybe_paypal_auto_sweep

    monkeypatch.setenv("EXCHANGE_AUTO_PAYPAL_SWEEP", "1")
    monkeypatch.setattr(
        "backend.services.exchange_payout_service.sync_auto_sweep_from_env",
        lambda: {"success": True, "changed": False},
    )
    monkeypatch.setattr(
        "backend.services.exchange_payout_service.plan_sweep",
        lambda: {"success": True, "actionable": True, "amount_usd": 50.0, "destination": "paypal"},
    )
    monkeypatch.setattr(
        "backend.services.exchange_payout_service.payout_status",
        lambda: {"ready_to_sweep": True},
    )
    monkeypatch.setattr(
        "backend.services.exchange_payout_service.execute_sweep",
        lambda: {"success": True, "swept": {"amount_usd": 50.0, "mode": "paper"}},
    )
    monkeypatch.setattr(
        "backend.services.profit_daemon_ops_service.profit_kill_active",
        lambda: False,
    )

    out = maybe_paypal_auto_sweep({})
    assert out.get("success") is True
    assert out.get("via") == "ops_auto_sweep"
