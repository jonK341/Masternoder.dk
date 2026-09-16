"""MN2 pool ops intelligence tests."""
import pytest

pytest_plugins = ["tests.unit.test_exchange_mn2_pool"]

from backend.services import exchange_ops_service as ops
from backend.services import exchange_ops_sell_service as sell_ops


def test_pool_health_score(pool_env):
    result = ops.pool_health_score()
    assert "score" in result
    assert 0 <= result["score"] <= 100
    assert result["band"] in ("green", "yellow", "red")


def test_liquidity_runway(pool_env):
    result = ops.liquidity_runway("USDT", "MN2")
    assert result["success"] is True
    assert len(result["runways"]) >= 1
    assert result["runways"][0]["from"] == "USDT"


def test_circuit_breaker_status(pool_env):
    cb = ops.circuit_breaker_status()
    assert "level" in cb
    assert cb["level"] in ("green", "yellow", "red", "off")


def test_treasury_waterfall(pool_env):
    wf = ops.treasury_waterfall()
    assert wf["success"] is True
    assert "priorities" in wf
    assert "recommendation" in wf


def test_unified_action_feed(pool_env):
    feed = ops.unified_action_feed(limit=10)
    assert feed["success"] is True
    assert "items" in feed


def test_ops_dashboard(pool_env):
    dash = ops.ops_dashboard()
    assert dash["success"] is True
    assert "health" in dash
    assert "waterfall" in dash


def test_sell_plan_dry_run(pool_env):
    plan = sell_ops.build_sell_plan()
    assert plan["success"] is True
    assert "actions" in plan
    assert plan.get("tax_aware_order") is True


def test_sell_plan_execute_dry_run_flag(pool_env):
    result = sell_ops.execute_sell_plan(dry_run=True)
    assert result.get("dry_run") is True
    assert "actions" in result


def test_ops_health_route(pool_env):
    client = pool_env["client"]
    r = client.get("/api/exchange/ops/health")
    body = r.get_json()
    assert body["success"] is True
    assert "health" in body
    assert "runway" in body


def test_ops_depth_chart(pool_env):
    client = pool_env["client"]
    r = client.get("/api/exchange/ops/depth-chart?hours=24")
    body = r.get_json()
    assert body["success"] is True
    assert "points" in body
