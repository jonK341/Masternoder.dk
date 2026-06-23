"""Wave B — SSE, webhooks, casino tiers, house income, sybil, float, swap."""
from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_webhook_outbox_enqueue_idempotent():
    from backend.services import webhook_outbox as wo

    path = os.path.join(_ROOT, "data", "_test_webhook_outbox.jsonl")
    old = wo._OUTBOX
    wo._OUTBOX = path
    try:
        if os.path.isfile(path):
            os.remove(path)
        a = wo.enqueue("test", "evt1", {"x": 1}, handler="p2p_paypal")
        b = wo.enqueue("test", "evt1", {"x": 1}, handler="p2p_paypal")
        assert a.get("success")
        assert b.get("duplicate")
    finally:
        wo._OUTBOX = old
        if os.path.isfile(path):
            os.remove(path)


def test_video_stage_cache_roundtrip():
    from backend.services import video_stage_cache as sc

    sc.put("unit", "hello", {"a": 1})
    got = sc.get("unit", "hello")
    assert got == {"a": 1}


def test_float_gate_assess(monkeypatch):
    from backend.services.mn2_float_gate import assess

    monkeypatch.setattr(
        "backend.services.mn2_proof_of_reserves_service.proof_of_reserves",
        lambda force=False: {"assets": {"onchain": {"total": 1000000}}},
    )
    r = assess(0)
    assert "allowed" in r
    assert r.get("verdict") == "green"


def test_internal_amm_quote_disabled_when_not_green(monkeypatch):
    from backend.services import mn2_internal_amm as amm

    monkeypatch.setattr(amm, "_swap_enabled", lambda: False)
    r = amm.quote("sell", 1.0)
    assert r.get("success") is False


def test_sybil_score_user():
    from backend.services.mn2_sybil_graph import score_user
    r = score_user("solo_user_xyz")
    assert r.get("cluster_size") >= 1


def test_house_income_summarize():
    from backend.services.house_income_aggregator import summarize
    r = summarize(since_hours=24)
    assert r.get("success") is True


def test_responsible_gaming_tier():
    from backend.services.casino_responsible_gaming import _tier_for_user
    t = _tier_for_user("test_user")
    assert isinstance(t, dict)


def test_trophy_rebate_rate():
    from backend.services.casino_trophy_rake_rebate import rebate_rate
    assert rebate_rate("solo_user") >= 0


def test_context_cache_roundtrip():
    from backend.services.generator_context_cache import put, get
    ctx = {"profile": {"display_name": "u1"}}
    put("u1", ctx, {"segments": [{"title": "a"}]})
    got = get("u1", ctx)
    assert got and got.get("segments")


def test_copy_trading_upsert():
    from backend.services import mn2_copy_trading as ct
    r = ct.upsert_follower("follower1", "agent_alpha", scale=0.1)
    assert r.get("success")
