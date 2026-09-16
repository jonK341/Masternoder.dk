"""MN2 / USDT / USDC swoop API and mapping."""
import pytest

pytest_plugins = ["tests.unit.test_exchange_mn2_pool"]

from backend.services import exchange_swoop_service as swoop


def test_resolve_swoop_mappings():
    cases = [
        ("MN2", "USDT", ("MN2", "sell", "USDT")),
        ("MN2", "USDC", ("MN2", "sell", "USDC")),
        ("USDT", "MN2", ("USDT", "sell", "MN2")),
        ("USDC", "MN2", ("USDC", "sell", "MN2")),
        ("USDT", "USDC", ("USDC", "buy", "USDT")),
        ("USDC", "USDT", ("USDT", "buy", "USDC")),
    ]
    for src, dst, expected in cases:
        res = swoop.resolve_swoop(src, dst, 10.0)
        assert res["success"] is True
        assert (res["symbol"], res["side"], res["quote"]) == expected


def test_resolve_swoop_errors():
    assert swoop.resolve_swoop("MN2", "MN2", 1.0)["error"] == "same_asset"
    assert swoop.resolve_swoop("BTC", "MN2", 1.0)["error"] == "invalid_swoop_asset"
    assert swoop.resolve_swoop("USDT", "MN2", 0)["error"] == "invalid_amount"


def test_swoop_quote_and_execute(pool_env, points_db):
    ex = pool_env["ex"]
    pool = pool_env["pool"]
    client = pool_env["client"]

    points_db.add_points("swoop_user", "mn2_balance", 500.0, source="seed", metadata={"reference": "seed"})

    r = client.post("/api/exchange/swoop/quote", json={
        "user_id": "swoop_user",
        "from_asset": "MN2",
        "to_asset": "USDT",
        "amount": 20.0,
    })
    q = r.get_json()
    assert q["success"] is True
    assert q["swoop"] is True
    assert q["from_asset"] == "MN2"
    assert q["to_asset"] == "USDT"
    assert q["pool_backed"] is True
    assert float(q["pool_reserve_quote"] or 0) > 0

    res = client.post("/api/exchange/swoop", json={
        "user_id": "swoop_user",
        "from_asset": "MN2",
        "to_asset": "USDT",
        "amount": 20.0,
        "quote_id": q["quote_id"],
    })
    body = res.get_json()
    assert body["success"] is True
    assert body["swoop"] is True
    assert float(body["to_amount"] or 0) > 0

    w = ex.get_wallet("swoop_user")
    assert float(w.get("mn2_balance") or 0) < 500.0
    assert float(w["assets"].get("USDT") or 0) > 0


def test_swoop_usdt_to_mn2(pool_env):
    ex = pool_env["ex"]
    client = pool_env["client"]
    ex._adjust_balance("stable_swoop", "USDT", 50.0)

    q = client.post("/api/exchange/swoop/quote", json={
        "user_id": "stable_swoop",
        "from_asset": "USDT",
        "to_asset": "MN2",
        "amount": 10.0,
    }).get_json()
    assert q["success"] is True
    assert q["to_amount"] > 0

    res = client.post("/api/exchange/swoop", json={
        "user_id": "stable_swoop",
        "from_asset": "USDT",
        "to_asset": "MN2",
        "amount": 10.0,
        "quote_id": q["quote_id"],
    }).get_json()
    assert res["success"] is True
    w = ex.get_wallet("stable_swoop")
    assert float(w.get("mn2_balance") or 0) > 0


def test_swoop_usdt_to_usdc(pool_env):
    ex = pool_env["ex"]
    client = pool_env["client"]
    ex._adjust_balance("stable_cross", "USDT", 30.0)

    q = client.post("/api/exchange/swoop/quote", json={
        "user_id": "stable_cross",
        "from_asset": "USDT",
        "to_asset": "USDC",
        "amount": 5.0,
    }).get_json()
    assert q["success"] is True
    assert q.get("pool_backed") is not True

    res = client.post("/api/exchange/swoop", json={
        "user_id": "stable_cross",
        "from_asset": "USDT",
        "to_asset": "USDC",
        "amount": 5.0,
        "quote_id": q["quote_id"],
    }).get_json()
    assert res["success"] is True
    w = ex.get_wallet("stable_cross")
    assert float(w["assets"].get("USDC") or 0) == pytest.approx(5.0, rel=1e-6)


def test_swoop_assets_route(pool_env):
    client = pool_env["client"]
    r = client.get("/api/exchange/swoop/assets")
    body = r.get_json()
    assert body["success"] is True
    assert set(body["assets"]) == {"MN2", "USDC", "USDT"}
    assert body["pool_swap_reserve_bps"] == 200


def test_wallet_hub_route(pool_env):
    client = pool_env["client"]
    r = client.get("/api/exchange/wallet-hub?user_id=hub_user")
    body = r.get_json()
    assert body["success"] is True
    assert set(body["balances"].keys()) == {"MN2", "USDC", "USDT"}
    assert body["pool"]["success"] is True
    assert "/exchange?swoop=USDT,MN2" in body["swoop_urls"]["usdt_mn2"]
