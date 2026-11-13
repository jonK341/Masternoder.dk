"""Aggregator hub v2 HTTP routes."""
from backend.services.aggregator_catalog_service import list_catalog


def test_catalog_service_matches_route_contract():
    r = list_catalog(limit=5)
    assert r["success"] is True
    assert r["count"] == 5
    assert "categories" in r


def test_assign_import_chain_helper():
    from backend.services.agent_peer_transactions_service import fire_aggregator_assignment_transfers

    out = fire_aggregator_assignment_transfers(
        "route_test_user",
        "analytics_agent",
        "agent_ops_01",
        aggregator_id="agg_001",
        burst=1,
        dry_run=True,
    )
    assert out.get("burst_requested") == 1
    assert out.get("attempted", 0) >= 0
