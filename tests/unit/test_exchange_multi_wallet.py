"""Multi-wallet deposit/withdraw + one daemon for all coins."""
import pytest


@pytest.fixture
def env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_multi_wallet_service as mw
    from backend.services import exchange_binance_withdraw_service as bwd

    data = tmp_path / "crypto_exchange"
    wallets = data / "wallets"
    wallets.mkdir(parents=True)

    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_WALLETS_DIR", str(wallets))
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(mw, "_INTENTS_PATH", str(data / "intents.json"))
    monkeypatch.setattr(mw, "_CREDITED_PATH", str(data / "credited.json"))
    monkeypatch.setattr(mw, "_DEPOSIT_LEDGER", str(data / "deposits.jsonl"))
    monkeypatch.setattr(mw, "_WITHDRAW_LEDGER", str(data / "withdrawals.jsonl"))
    monkeypatch.setattr(mw, "_STATE_PATH", str(data / "daemon_state.json"))
    monkeypatch.setattr(ex, "_get_quote_balance", lambda uid, quote: 0.0)
    monkeypatch.setattr(
        ex,
        "load_config",
        lambda: {
            "enabled": True,
            "platform_fees": {"withdrawal_fee_bps": 15},
            "multi_wallet": {"enabled": True, "min_withdraw": {"BTC": 0.0001}},
            "assets": [
                {"symbol": "MN2", "name": "MN2", "base_price_usd": 0.05, "min_trade": 0.001},
                {"symbol": "BTC", "name": "Bitcoin", "base_price_usd": 100000, "min_trade": 0.00001},
                {"symbol": "USDT", "name": "Tether", "base_price_usd": 1, "min_trade": 1},
                {"symbol": "ETH", "name": "Ethereum", "base_price_usd": 3000, "min_trade": 0.0001},
            ],
            "quote_currencies": ["MN2", "USDT"],
            "agent_trading": {"agents": [{"id": "exchange_agent_test", "enabled": True}]},
        },
    )
    monkeypatch.setattr(
        "backend.services.mn2_earn_auth.require_earn_user",
        lambda uid: (True, str(uid)),
    )
    monkeypatch.setattr(bwd, "binance_credentials", lambda: {"api_key": "k", "api_secret": "s"})
    return {"ex": ex, "mw": mw, "bwd": bwd}


def test_deposit_address_for_any_coin(env, monkeypatch):
    mw, bwd = env["mw"], env["bwd"]
    monkeypatch.setattr(
        bwd,
        "get_deposit_address",
        lambda coin, network, dry_run=None, skip_live_gate=True: {
            "success": True, "address": "bc1qtestbtcaddressxxxxxx", "tag": "",
            "mode": "paper", "simulated": True, "network": network, "coin": coin,
        },
    )
    # Call through multi-wallet which imports get_deposit_address at module level
    monkeypatch.setattr(
        mw,
        "get_deposit_address",
        lambda coin, network, dry_run=None, skip_live_gate=True: {
            "success": True, "address": "bc1qtestbtcaddressxxxxxx", "tag": "",
            "mode": "paper", "simulated": True, "network": network, "coin": coin,
        },
    )
    res = mw.get_deposit_instructions("u1", "BTC", amount=0.01)
    assert res["success"] is True
    assert res["asset"] == "BTC"
    assert res["address"].startswith("bc1q")
    assert res["intent"]["amount"] == 0.01


def test_confirm_deposit_credits_wallet(env, monkeypatch):
    ex, mw = env["ex"], env["mw"]
    monkeypatch.setattr(
        mw,
        "list_deposit_history",
        lambda coin=None, status=None, start_ms=None, end_ms=None, limit=100,
               dry_run=None, skip_live_gate=True: {
            "success": True,
            "deposits": [{"txId": "txid-btc-1", "amount": 0.02, "status": 1, "coin": "BTC"}],
        },
    )
    res = mw.confirm_deposit_txid("u1", "BTC", "txid-btc-1")
    assert res["success"] is True
    assert float(ex.get_wallet("u1")["assets"]["BTC"]) == pytest.approx(0.02)
    again = mw.confirm_deposit_txid("u1", "BTC", "txid-btc-1")
    assert again["success"] is False
    assert again["error"] == "already_credited"


def test_withdraw_any_coin_requires_live(env, monkeypatch):
    ex, mw = env["ex"], env["mw"]
    monkeypatch.setattr(mw, "venue_credentials_ok", lambda: True)
    monkeypatch.setattr(mw, "binance_withdraw_live_enabled", lambda: False)
    ex._adjust_balance("u1", "ETH", 1.0)
    res = mw.withdraw_user_asset("u1", "ETH", 0.1, "0xabc1234567890def")
    assert res["success"] is False
    assert res["error"] == "live_gates_required"


def test_multi_wallet_tick_one_daemon(env, monkeypatch):
    mw = env["mw"]
    monkeypatch.setattr(mw, "sync_platform_deposit_addresses", lambda dry_run=False: {"success": True, "count": 3, "synced": []})
    monkeypatch.setattr(mw, "scan_open_intents", lambda force=False: {"success": True, "credited": 0, "checked": 0})
    monkeypatch.setattr(mw, "refresh_venue_balances", lambda: {"success": True, "balances": {"BTC": {"free": 0}}})
    monkeypatch.setattr(mw, "venue_credentials_ok", lambda: True)
    res = mw.run_multi_wallet_tick()
    assert res["success"] is True
    assert res["one_daemon"] is True
    assert res["tick_count"] >= 1
    st = mw.daemon_status()
    assert st["one_daemon"] is True
    assert "exchange_multi_wallet_daemon.py" in st["daemon_script"]


def test_get_deposit_address_helper(env):
    from backend.services.exchange_binance_withdraw_service import (
        deposit_network_for_asset,
        get_deposit_address,
        stable_deposit_network,
    )
    assert deposit_network_for_asset("USDT") == "TRC20"
    assert stable_deposit_network("USDC") == "ETH"
    assert deposit_network_for_asset("BTC") == "BTC"
    res = get_deposit_address("BTC", "BTC", dry_run=True, skip_live_gate=True)
    assert res["success"] is True
    assert res["simulated"] is True
    assert res["address"]
