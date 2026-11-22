"""Exchange catalog agents route to Binance when live gates are on."""
from __future__ import annotations

import json
from pathlib import Path


def _write_cfg(path: Path, **extra) -> None:
    cfg = {
        "enabled": True,
        "agent_trading": {
            "enabled": True,
            "live_venue_trading": True,
            "venue_id": "binance",
            "max_trade_usd_per_tick": 8,
            "max_agents_per_tick": 1,
            "min_venue_quote_reserve_usd": 20,
            "min_tick_gap_sec": 0,
            "agents": [
                {
                    "id": "exchange_agent_meme_hunter",
                    "name": "Meme Hunter",
                    "strategy": "meme_momentum",
                    "assets": ["DOGE", "SHIB"],
                    "enabled": True,
                }
            ],
        },
        "assets": [
            {"symbol": "DOGE", "name": "Dogecoin", "base_price_usd": 0.1, "min_trade": 1},
            {"symbol": "SHIB", "name": "Shiba", "base_price_usd": 0.00001, "min_trade": 100},
            {"symbol": "USDC", "name": "USD Coin", "base_price_usd": 1.0, "min_trade": 1},
        ],
        "quote_currencies": ["MN2", "USDC", "USDT"],
    }
    cfg["agent_trading"].update(extra)
    path.write_text(json.dumps(cfg), encoding="utf-8")


def test_agents_for_tick_rotation():
    from backend.services import crypto_exchange_agent_service as ag

    agents = [{"id": f"a{i}"} for i in range(4)]
    assert [a["id"] for a in ag._agents_for_tick(agents, 1, 2)] == ["a0", "a1"]
    assert [a["id"] for a in ag._agents_for_tick(agents, 2, 2)] == ["a1", "a2"]
    assert [a["id"] for a in ag._agents_for_tick(agents, 5, 2)] == ["a0", "a1"]


def test_live_agent_tick_places_binance_order(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import crypto_exchange_agent_service as ag
    from backend.services import exchange_user_venue_execution_service as uve

    data = tmp_path / "crypto_exchange"
    data.mkdir()
    (data / "wallets").mkdir()
    cfg_path = tmp_path / "crypto_exchange_config.json"
    _write_cfg(cfg_path)

    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_WALLETS_DIR", str(data / "wallets"))
    monkeypatch.setattr(ex, "_BASE", str(tmp_path))
    monkeypatch.setattr(ag, "_STATE_PATH", str(data / "agent_state.json"))
    monkeypatch.setattr(ex, "load_config", lambda: json.loads(cfg_path.read_text(encoding="utf-8")))
    monkeypatch.setattr(ag, "_venue_live_ready", lambda venue_id="binance": True)

    # Seed sales pool with venue-backed USDC.
    ex._set_balance("exchange_sales_pool", "USDC", 73.0)

    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.parse_spot_balances",
        lambda *a, **k: {"USDC": 73.0},
    )
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.refresh_venue_balances",
        lambda *a, **k: {"success": True},
    )
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.invalidate_venue_balance_cache",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.venue_quote_asset",
        lambda venue_id: "USDC",
    )
    monkeypatch.setattr(
        "backend.services.exchange_venue_api_service.market_order_for_leg",
        lambda *a, **k: {
            "ok": True,
            "venue_id": "binance",
            "base": "DOGE",
            "quote": "USDC",
            "market": "DOGEUSDC",
            "side": "buy",
            "quantity": 80.0,
            "notional_usd": 8.0,
            "price_usd": 0.1,
        },
    )

    calls = {}

    def fake_execute(user_id, venue_id, quote_id, symbol, side, amount, quote=None):
        calls["args"] = {
            "user_id": user_id,
            "venue_id": venue_id,
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "quote": quote,
        }
        return {
            "success": True,
            "mode": "live",
            "trade": {
                "trade_id": "t1",
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "usd_value": 8.0,
            },
            "order": {"order_id": "o1", "success": True},
        }

    monkeypatch.setattr(uve, "execute_venue_swap", fake_execute)
    monkeypatch.setattr(uve, "quote_venue_swap", lambda *a, **k: {
        "success": True, "quote_cost": 8.2, "symbol": "DOGE", "side": "buy", "amount": 80.0,
    })
    # Import path used inside _trade_agent_live
    monkeypatch.setattr(
        "backend.services.exchange_user_venue_execution_service.execute_venue_swap",
        fake_execute,
    )
    monkeypatch.setattr(
        "backend.services.exchange_user_venue_execution_service.quote_venue_swap",
        lambda *a, **k: {
            "success": True, "quote_cost": 8.2, "symbol": "DOGE", "side": "buy", "amount": 80.0,
        },
    )

    res = ag.tick(force=True)
    assert res["success"] is True
    assert res["mode"] == "live"
    assert res["agents_traded"] == 1
    action = next(a for a in res["actions"] if a.get("agent_id") == "exchange_agent_meme_hunter")
    assert action["success"] is True
    assert action["mode"] == "live"
    assert action["venue_id"] == "binance"
    assert action["symbol"] in ("DOGE", "SHIB")
    assert calls["args"]["venue_id"] == "binance"
    assert calls["args"]["side"] == "buy"
    assert calls["args"]["symbol"] == action["symbol"]


def test_internal_fallback_when_not_live(tmp_path, monkeypatch):
    from backend.services import crypto_exchange_service as ex
    from backend.services import crypto_exchange_agent_service as ag

    data = tmp_path / "crypto_exchange"
    data.mkdir()
    (data / "wallets").mkdir()
    cfg_path = tmp_path / "crypto_exchange_config.json"
    _write_cfg(cfg_path)

    monkeypatch.setattr(ex, "_DATA_DIR", str(data))
    monkeypatch.setattr(ex, "_WALLETS_DIR", str(data / "wallets"))
    monkeypatch.setattr(ex, "_BASE", str(tmp_path))
    monkeypatch.setattr(ag, "_STATE_PATH", str(data / "agent_state.json"))
    monkeypatch.setattr(ex, "load_config", lambda: json.loads(cfg_path.read_text(encoding="utf-8")))
    monkeypatch.setattr(ag, "_venue_live_ready", lambda venue_id="binance": False)
    monkeypatch.setattr(ag, "_seed_agent_mn2", lambda *a, **k: None)

    def fake_swap(*a, **k):
        return {"success": True, "trade": {"trade_id": "i1", "usd_value": 1.0}}

    monkeypatch.setattr(ex, "execute_swap", fake_swap)

    res = ag.tick(force=True)
    assert res["mode"] == "internal"
    action = next(a for a in res["actions"] if a.get("agent_id") == "exchange_agent_meme_hunter")
    assert action["success"] is True
    assert action.get("mode") == "internal"
