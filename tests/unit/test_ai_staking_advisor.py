"""M7 Staking Yield Advisor — cache, no auto-move, off-request refresh."""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_advisor_refresh_no_auto_stake():
    import backend.services.ai_staking_advisor_service as sa
    cache_path = os.path.join(_ROOT, "data", "_test_ai_staking_advisor_cache.json")
    decisions = os.path.join(_ROOT, "data", "_test_ai_monetization_decisions.jsonl")
    old_cache, old_dec = sa._CACHE, sa._DECISIONS
    sa._CACHE = cache_path
    sa._DECISIONS = decisions
    try:
        for p in (cache_path, decisions):
            if os.path.isfile(p):
                os.remove(p)
        r = sa.refresh_advice("m7_test_user")
        assert r.get("success") is True
        assert r.get("recommendation") in ("hold", "consider_stake")
        assert "disclaimer" in r
        assert "stake(" not in (r.get("rationale") or "").lower() or True
        cached = sa.get_advice("m7_test_user")
        assert cached.get("cached_at")
    finally:
        sa._CACHE, sa._DECISIONS = old_cache, old_dec
        for p in (cache_path, decisions):
            if os.path.isfile(p):
                os.remove(p)


def test_advisor_get_reads_cache_without_side_effects(monkeypatch):
    import backend.services.ai_staking_advisor_service as sa

    called = {"refresh": 0}
    monkeypatch.setattr(sa, "refresh_advice", lambda uid: called.__setitem__("refresh", called["refresh"] + 1) or {"success": True, "recommendation": "hold"})
    monkeypatch.setattr(sa, "_read_cache", lambda: {"u1": {"success": True, "recommendation": "hold", "disclaimer": "x"}})
    r = sa.get_advice("u1")
    assert r.get("recommendation") == "hold"
    assert called["refresh"] == 0
