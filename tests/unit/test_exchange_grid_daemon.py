"""Agent grid daemon — multi-fleet mesh matching on the internal exchange."""
import json
from pathlib import Path

import pytest


@pytest.fixture
def grid_env(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import exchange_arbitrage_service as arb
    from backend.services import exchange_daemon_matcher_service as grid
    from backend.services import external_exchange_connector_service as conn
    from backend.services import unified_points_database as upd
    from contextlib import contextmanager

    @contextmanager
    def _noop_ctx():
        yield

    monkeypatch.setattr(upd, "_unified_points_db_context", _noop_ctx)
    db = upd.UnifiedPointsDatabase(base_dir=str(tmp_path / "points"))
    monkeypatch.setattr(upd, "unified_points_db", db)

    def _file_only_get(user_id: str):
        return {"success": True, "points": db._points_payload_from_file(user_id)}

    monkeypatch.setattr(db, "get_all_points", _file_only_get)

    data = tmp_path / "crypto_exchange"
    (data / "agent_accounts").mkdir(parents=True)
    (data / "wallets").mkdir(parents=True)

    treasury_cfg = tmp_path / "exchange_treasury_config.json"
    treasury_cfg.write_text(
        json.dumps({
            "enabled": True,
            "treasury_user_id": "platform_treasury",
            "daemon_mesh_enabled": True,
            "grid_max_matches": 10,
            "grid_rounds_per_tick": 2,
            "grid_trade_mn2": 25.0,
            "grid_intents_per_agent": 2,
            "grid_include_arb_agents": True,
            "grid_include_extended_agents": False,
            "grid_include_marketplace_agents": False,
            "grid_include_treasury_liquidity": False,
            "mesh_symbols": ["USDC", "ETH"],
        }),
        encoding="utf-8",
    )

    cfg = tmp_path / "crypto_exchange_config.json"
    src = Path(__file__).resolve().parents[2] / "data" / "crypto_exchange_config.json"
    cfg.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(ex, "_BASE", str(tmp_path))
    monkeypatch.setattr(ex, "_CONFIG_PATH", str(cfg))
    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_AUDIT_PATH", str(data / "audit_log.jsonl"))
    monkeypatch.setattr(ex, "_TRADES_PATH", str(data / "trades.jsonl"))
    monkeypatch.setattr(ex, "_WALLETS_DIR", str(data / "wallets"))
    monkeypatch.setattr(arb, "_ACCOUNTS_DIR", str(data / "agent_accounts"))
    monkeypatch.setattr(grid, "load_grid_config", lambda: {
        "enabled": True,
        "mesh_symbols": ["USDC", "ETH"],
        "max_matches": 10,
        "rounds_per_tick": 2,
        "trade_mn2": 25.0,
        "include_arb_agents": True,
        "include_extended_agents": False,
        "include_marketplace_agents": False,
        "include_treasury_liquidity": False,
        "intents_per_agent": 2,
    })

    ex._adjust_quote_balance("buyer_bot", "MN2", 500.0, "test_seed", {"reference": "buyer-seed"})
    ex._adjust_quote_balance("seller_bot", "MN2", 50.0, "test_seed", {"reference": "seller-seed"})
    seller_wallet = ex.get_wallet("seller_bot")
    seller_wallet.setdefault("assets", {})["USDC"] = 25.0
    ex._save_wallet("seller_bot", seller_wallet)

    return {"ex": ex, "grid": grid, "conn": conn}


def test_collect_intents_includes_cross_trade_and_arb(grid_env, monkeypatch):
    grid = grid_env["grid"]

    monkeypatch.setattr(
        "backend.services.crypto_exchange_agent_service.list_agents",
        lambda: {
            "agents": [
                {"id": "buyer_bot", "enabled": True, "assets": ["USDC"]},
                {"id": "seller_bot", "enabled": True, "assets": ["USDC"]},
            ]
        },
    )
    monkeypatch.setattr(grid, "_tick_parity", lambda: 0)

    intents = grid._collect_intents()
    kinds = {i.get("kind") for i in intents}
    agent_ids = {i.get("agent_id") for i in intents}
    assert "cross_trade" in kinds
    assert "arb" in kinds
    assert "buyer_bot" in agent_ids
    assert len(intents) >= 4


def test_run_grid_tick_executes_internal_matches(grid_env, monkeypatch):
    grid = grid_env["grid"]

    def fake_collect(*, grid_cfg=None):
        return [
            {"agent_id": "buyer_bot", "symbol": "USDC", "side": "buy", "kind": "cross_trade"},
            {"agent_id": "seller_bot", "symbol": "USDC", "side": "sell", "kind": "cross_trade"},
        ]

    def fake_match(buyer, seller, sym, *, trade_mn2, treasury):
        return {
            "symbol": sym,
            "quantity": 1.0,
            "buyer": buyer["agent_id"],
            "seller": seller["agent_id"],
            "buyer_kind": buyer.get("kind"),
            "seller_kind": seller.get("kind"),
            "spread_usd": 0.01,
        }

    monkeypatch.setattr(grid, "_collect_intents", fake_collect)
    monkeypatch.setattr(grid, "_execute_match", fake_match)

    out = grid.run_grid_tick(max_matches=5)
    assert out["success"] is True
    assert out["match_count"] >= 1
    assert out["agents_involved"] >= 2
    assert out["mesh_profit_usd"] >= 0.01


def test_run_mesh_tick_delegates_to_grid(grid_env, monkeypatch):
    grid = grid_env["grid"]
    monkeypatch.setattr(grid, "run_grid_tick", lambda **kw: {"success": True, "match_count": 3, "delegated": True})
    out = grid.run_mesh_tick(max_matches=5)
    assert out.get("delegated") is True
    assert out["match_count"] == 3
