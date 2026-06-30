"""Extended profit strategy tests."""
import pytest


@pytest.fixture
def ext_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_arbitrage_service as arb
    from backend.services import external_exchange_connector_service as conn
    from backend.services import exchange_extended_profit_service as ext

    data = tmp_path / "crypto_exchange"
    (data / "agent_accounts").mkdir(parents=True)
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_BASE", str(tmp_path))
    monkeypatch.setattr(conn, "_PRICE_CACHE_PATH", str(data / "external_prices.json"))
    monkeypatch.setattr(arb, "_ACCOUNTS_DIR", str(data / "agent_accounts"))
    monkeypatch.setattr(ext, "_CFG_PATH", str(tmp_path / "exchange_extended_profit_config.json"))
    (tmp_path / "exchange_extended_profit_config.json").write_text(
        '{"enabled":true,"profiles":{"standard":{"strategies":["stablecoin_peg","triangular_paper"]}},'
        '"strategies":{"stablecoin_peg":{"enabled":true,"min_deviation_bps":1,"notional_usd":100,"agent_id":"t1"},'
        '"triangular_paper":{"enabled":true,"venues":["binance"],"loops":[["BTC","ETH","SOL"]],'
        '"min_edge_bps":1,"notional_usd":50,"agent_id":"t2"}}}',
        encoding="utf-8",
    )
    return ext


def test_run_extended_profit_tick_runs_strategies(ext_env):
    ext = ext_env
    res = ext.run_extended_profit_tick(profile="standard")
    assert res["success"] is True
    assert res["strategy_count"] == 2
    assert "stablecoin_peg" in res["results"]
    assert "triangular_paper" in res["results"]


def test_stablecoin_peg_books_on_deviation(ext_env, monkeypatch):
    ext = ext_env
    from backend.services import crypto_exchange_service as ex

    monkeypatch.setattr(ex, "_price_usd", lambda sym: 0.995 if sym == "USDT" else 1.005)
    res = ext.tick_stablecoin_peg({"min_deviation_bps": 5, "notional_usd": 100, "agent_id": "peg_test"})
    assert res["executed"] is True
    assert res["est_profit_usd"] > 0
