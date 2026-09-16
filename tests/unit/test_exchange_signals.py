"""Cross-trade signal feed + balances aggregator."""
import pytest


def test_get_signals_filters_and_marks_actionable(monkeypatch):
    from backend.services import exchange_arbitrage_service as arb
    from backend.services import exchange_signals_service as sig

    def fake_scan():
        return {"success": True, "opportunities": [
            {"symbol": "ATOM", "buy_venue": "binance", "sell_venue": "internal", "net_bps": 600, "notional_usd": 10},
            {"symbol": "DOGE", "buy_venue": "binance", "sell_venue": "nonkyc", "net_bps": 22, "notional_usd": 15},
            {"symbol": "ETH", "buy_venue": "binance", "sell_venue": "nonkyc", "net_bps": 3, "notional_usd": 10},
        ]}
    monkeypatch.setattr(arb, "scan_opportunities", fake_scan)
    # grid signals: force empty (no network) to isolate arb
    monkeypatch.setattr(sig, "_grid_signals", lambda limit: [])

    out = sig.get_signals(min_net_bps=10, limit=25)
    assert out["success"] is True
    syms = [s["symbol"] for s in out["signals"]]
    assert "ETH" not in syms  # 3 bps below min 10
    atom = next(s for s in out["signals"] if s["symbol"] == "ATOM")
    assert atom["actionable"] is False  # internal sell leg
    doge = next(s for s in out["signals"] if s["symbol"] == "DOGE")
    assert doge["actionable"] is True
    assert doge["action"]["kind"] == "spatial_arb"
    assert out["counts"]["actionable"] == 1


def test_account_balances(monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_venue_api_service as vapi
    from backend.services import exchange_signals_service as sig

    monkeypatch.setattr(vapi, "venue_has_credentials", lambda v: True)
    monkeypatch.setattr(vapi, "parse_spot_balances",
                        lambda v, dry_run=None: {"BTC": 0.01, "USDC": 50.0} if v == "binance" else {"USDT": 26.0})
    prices = {"BTC": 60000.0, "USDC": 1.0, "USDT": 1.0}
    monkeypatch.setattr(ex, "_price_usd", lambda s, cfg=None: prices.get(str(s).upper(), 0.0))

    out = sig.account_balances(["binance", "nonkyc"])
    assert out["success"] is True
    assert out["venues"]["binance"]["usd_total"] == pytest.approx(650.0)  # 0.01*60000 + 50
    assert out["venues"]["nonkyc"]["usd_total"] == pytest.approx(26.0)
    assert out["total_usd"] == pytest.approx(676.0)
