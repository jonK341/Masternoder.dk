"""Paper vs live payout ledger split for profit monitor."""
from __future__ import annotations


def test_payout_ledger_split_returns_paper_and_live(monkeypatch):
    from backend.services import exchange_payout_service as pay

    monkeypatch.setattr(pay, "_treasury_stashed_usd_by_mode", lambda mode: 1000.0 if mode == "paper" else 12.5)
    monkeypatch.setattr(pay, "_swept_total_for_mode", lambda cfg, mode: 50.0 if mode == "paper" else 1.0)
    monkeypatch.setattr(pay, "_paypal_live_enabled", lambda: False)
    monkeypatch.setattr(pay, "_sweep_ledger_mode", lambda: "paper")
    monkeypatch.setattr(pay, "_owner_paypal_email", lambda cfg=None: "owner@test.com")
    monkeypatch.setattr(pay, "_paypal_share_pct", lambda cfg: 1.0)
    monkeypatch.setattr(pay, "_min_sweep_usd", lambda cfg=None: 5.0)
    monkeypatch.setattr(pay, "_load", lambda: {"auto_sweep": True, "min_sweep_usd": 5})

    out = pay.payout_ledger_split()
    assert out.get("success") is True
    assert out["paper"]["stash_usd"] == 1000.0
    assert out["live"]["stash_usd"] == 12.5
    assert "paper" in out["banner"].lower() or "PAPER" in out["banner"]


def test_maybe_alert_paypal_capture_batch_skips_zero(monkeypatch):
    from backend.services.profit_daemon_ops_service import maybe_alert_paypal_capture_batch

    out = maybe_alert_paypal_capture_batch({"counts": {"captured": 0}})
    assert out.get("skipped") is True
