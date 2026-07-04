"""Sales pool sweep tests — agent wallets → exchange_sales_pool user."""
import json
import pytest


@pytest.fixture
def sales_pool_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_sales_pool_service as sp

    data = tmp_path / "crypto_exchange"
    wallets = data / "wallets"
    wallets.mkdir(parents=True)

    cfg_path = tmp_path / "exchange_sales_pool_config.json"
    cfg_path.write_text(
        json.dumps({
            "enabled": True,
            "sales_pool_user_id": "exchange_sales_pool",
            "source_agent_ids": ["agent_a", "agent_b"],
            "min_transfer_by_asset": {"USDC": 10, "BTC": 0.001},
            "reserve_by_agent": {
                "default": {"USDC": 20, "BTC": 0.0005},
                "agent_a": {"USDC": 50},
            },
            "min_pool_by_asset": {"USDC": 100},
            "tick_cooldown_seconds": 3600,
        }),
        encoding="utf-8",
    )

    (wallets / "agent_a.json").write_text(
        json.dumps({"assets": {"USDC": 200, "BTC": 0.01}, "staking": {}, "bonus": {}, "volume_usd_30d": 0}),
        encoding="utf-8",
    )
    (wallets / "agent_b.json").write_text(
        json.dumps({"assets": {"USDC": 25}, "staking": {}, "bonus": {}, "volume_usd_30d": 0}),
        encoding="utf-8",
    )
    (wallets / "exchange_sales_pool.json").write_text(
        json.dumps({"assets": {}, "staking": {}, "bonus": {}, "volume_usd_30d": 0}),
        encoding="utf-8",
    )

    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_WALLETS_DIR", str(wallets))
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(sp, "_CFG_PATH", str(cfg_path))
    monkeypatch.setattr(sp, "_STATE_PATH", str(data / "sales_pool_state.json"))
    monkeypatch.setattr(sp, "_LEDGER_PATH", str(data / "sales_pool_ledger.jsonl"))

    return {"ex": ex, "sp": sp, "wallets": wallets}


def test_list_agent_wallet_balances(sales_pool_env):
    sp = sales_pool_env["sp"]
    bal = sp.list_agent_wallet_balances()
    assert bal["success"] is True
    by_id = {a["agent_id"]: a for a in bal["agents"]}
    assert by_id["agent_a"]["transferable"]["USDC"] == 150  # 200 - 50 reserve
    assert "USDC" not in by_id["agent_b"]["transferable"]  # 5 below min 10


def test_transfer_to_sales_pool(sales_pool_env):
    sp = sales_pool_env["sp"]
    ex = sales_pool_env["ex"]

    r = sp.transfer_to_sales_pool(force=True)
    assert r["success"] is True
    assert r["transfer_count"] >= 2

    pool = ex.get_wallet("exchange_sales_pool")["assets"]
    assert pool["USDC"] == 150  # only agent_a (agent_b below min)
    assert pool["BTC"] == pytest.approx(0.0095)  # 0.01 - 0.0005 reserve

    agent_a = ex.get_wallet("agent_a")["assets"]
    assert agent_a["USDC"] == 50
    assert agent_a["BTC"] == pytest.approx(0.0005)


def test_cooldown_skips_second_transfer(sales_pool_env):
    sp = sales_pool_env["sp"]
    ex = sales_pool_env["ex"]

    sp.transfer_to_sales_pool(force=True)
    (sales_pool_env["wallets"] / "agent_a.json").write_text(
        json.dumps({"assets": {"USDC": 200}, "staking": {}, "bonus": {}, "volume_usd_30d": 0}),
        encoding="utf-8",
    )

    r = sp.transfer_to_sales_pool(force=False)
    assert r.get("skipped") is True
    assert r.get("reason") == "cooldown"
    assert ex.get_wallet("exchange_sales_pool")["assets"].get("USDC") == 150


def test_sales_pool_status(sales_pool_env):
    sp = sales_pool_env["sp"]
    sp.transfer_to_sales_pool(force=True)
    st = sp.sales_pool_status()
    assert st["success"] is True
    assert st["pool_assets"]["USDC"] == 150
    assert st["transfer_count"] >= 1
    assert "USDC" not in st["pool_gaps"]  # 150 >= min 100


def test_rebalance_triggers_when_pool_low(sales_pool_env):
    sp = sales_pool_env["sp"]
    st = sp.sales_pool_status()
    assert st["pool_gaps"]["USDC"] == 100

    r = sp.rebalance_sales_pool(force=True)
    assert r["success"] is True
    assert r["transfer_count"] >= 1


def test_auto_tune_reduces_min_transfer_after_gap_streak(sales_pool_env):
    sp = sales_pool_env["sp"]
    cfg_path = sales_pool_env["sp"]._CFG_PATH
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    cfg["auto_tune"] = True
    cfg["auto_tune_ticks_threshold"] = 2
    cfg["auto_tune_reduce_pct"] = 0.2
    cfg["auto_tune_min_transfer_floor"] = {"USDC": 5}
    cfg["min_transfer_by_asset"] = {"USDC": 10}
    with open(cfg_path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh)

    state_path = sales_pool_env["sp"]._STATE_PATH
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump({"auto_tune_gap_streak": {"USDC": 2}}, fh)
    with open(state_path, encoding="utf-8") as fh:
        state = json.load(fh)

    mins = sp._auto_tune_mins(cfg, state)
    assert mins["USDC"] == pytest.approx(8.0)  # 10 * 0.8
