"""Live transferable USDT/USDC markets — paper inventing off by default."""
import pytest


@pytest.fixture
def env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_mn2_pool_service as pool
    from backend.services import exchange_stable_markets_service as stables
    from backend.services import exchange_multi_wallet_service as mw

    data = tmp_path / "crypto_exchange"
    wallets = data / "wallets"
    wallets.mkdir(parents=True)

    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_WALLETS_DIR", str(wallets))
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(mw, "_WITHDRAW_LEDGER", str(data / "multi_wallet_withdrawals.jsonl"))
    monkeypatch.setattr(mw, "_INTENTS_PATH", str(data / "intents.json"))
    monkeypatch.setattr(mw, "_CREDITED_PATH", str(data / "credited.json"))
    monkeypatch.setattr(mw, "_DEPOSIT_LEDGER", str(data / "deposits.jsonl"))
    monkeypatch.setattr(mw, "_STATE_PATH", str(data / "daemon_state.json"))

    cfg_path = tmp_path / "exchange_mn2_pool_config.json"
    cfg_path.write_text(
        '{"enabled": true, "paper_seed_on_empty": false, "allow_non_withdrawable_seed": false, '
        '"pool_user_id": "exchange_sales_pool"}',
        encoding="utf-8",
    )
    monkeypatch.setattr(pool, "_cfg_path", lambda: str(cfg_path))

    monkeypatch.delenv("EXCHANGE_STABLE_PAPER", raising=False)
    monkeypatch.setenv("EXCHANGE_STABLE_MARKETS_LIVE", "1")
    for flag in ("EXCHANGE_PAYOUT_BINANCE_LIVE", "EXCHANGE_ARBITRAGE_LIVE"):
        monkeypatch.delenv(flag, raising=False)

    monkeypatch.setattr(
        ex,
        "load_config",
        lambda: {
            "enabled": True,
            "stable_markets": {
                "paper_mode": False,
                "transferable": True,
                "withdraw_enabled": True,
                "min_withdraw": {"USDT": 10, "USDC": 10},
                "default_networks": {"USDT": "TRC20", "USDC": "ETH"},
            },
            "platform_fees": {"withdrawal_fee_bps": 15},
            "assets": [
                {"symbol": "USDT", "name": "Tether", "base_price_usd": 1, "min_trade": 1},
                {"symbol": "USDC", "name": "USD Coin", "base_price_usd": 1, "min_trade": 1},
            ],
            "quote_currencies": ["MN2", "USDC", "USDT"],
        },
    )
    monkeypatch.setattr(ex, "_get_quote_balance", lambda uid, quote: 0.0)
    return {"ex": ex, "pool": pool, "stables": stables, "mw": mw}


def test_paper_mode_off_by_default(env):
    stables = env["stables"]
    assert stables.paper_mode_enabled() is False
    status = stables.stable_markets_status()
    assert status["paper_mode"] is False
    assert status["transferable"] is True


def test_paper_seed_skipped_when_live(env):
    pool = env["pool"]
    res = pool.ensure_paper_seed()
    assert res.get("skipped") is True
    assert res.get("reason") in ("paper_mode_disabled", "paper_seed_disabled")


def test_venue_backed_caps_ledger(env, monkeypatch):
    stables = env["stables"]
    monkeypatch.setattr(stables, "venue_free", lambda asset: 25.0)
    assert stables.venue_backed_available(100.0, "USDT") == 25.0
    monkeypatch.setattr(stables, "paper_mode_enabled", lambda: True)
    assert stables.venue_backed_available(100.0, "USDT") == 100.0


def test_withdraw_requires_live_gates(env, monkeypatch):
    ex, stables, mw = env["ex"], env["stables"], env["mw"]
    monkeypatch.setattr(
        "backend.services.mn2_earn_auth.require_earn_user",
        lambda uid: (True, str(uid)),
    )
    monkeypatch.setattr(mw, "venue_credentials_ok", lambda: True)
    monkeypatch.setattr(mw, "binance_withdraw_live_enabled", lambda: False)
    ex._adjust_balance("u1", "USDT", 50.0)
    res = stables.withdraw_user_stable("u1", "USDT", 20.0, "TExampleWithdrawAddress123")
    assert res["success"] is False
    assert res["error"] == "live_gates_required"
    assert float(ex.get_wallet("u1")["assets"]["USDT"]) == pytest.approx(50.0)


def test_withdraw_live_debits_and_calls_binance(env, monkeypatch):
    ex, stables, mw = env["ex"], env["stables"], env["mw"]
    monkeypatch.setattr(
        "backend.services.mn2_earn_auth.require_earn_user",
        lambda uid: (True, str(uid)),
    )
    monkeypatch.setattr(mw, "venue_credentials_ok", lambda: True)
    monkeypatch.setattr(mw, "binance_withdraw_live_enabled", lambda: True)
    monkeypatch.setattr(
        mw,
        "get_spot_asset_free",
        lambda asset, skip_live_gate=True: {"success": True, "free": 100.0},
    )
    monkeypatch.setattr(
        mw,
        "preflight_withdraw_asset",
        lambda *a, **k: {"ready": True},
    )
    monkeypatch.setattr(
        mw,
        "withdraw_asset",
        lambda coin, amount, address, network, dry_run=None, withdraw_order_id=None: {
            "success": True,
            "withdraw_id": "wd-1",
            "amount": amount,
        },
    )
    ex._adjust_balance("u1", "USDT", 50.0)
    res = stables.withdraw_user_stable("u1", "USDT", 20.0, "TExampleWithdrawAddress123", "TRC20")
    assert res["success"] is True
    assert res["live"] is True
    assert res["withdrawn"]["amount"] == 20.0
    assert float(ex.get_wallet("u1")["assets"]["USDT"]) == pytest.approx(30.0)
