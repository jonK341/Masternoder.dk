"""Wave C — tournament fairness chain, RG, copy trading, context cache."""
from __future__ import annotations

import hashlib
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def test_tournament_fairness_chain_derivation():
    from backend.services import casino_tournaments as ct

    state = {
        "prev-cup": {
            "id": "prev-cup",
            "template_id": "daily-coins",
            "status": "ended",
            "ended_at": "2026-06-01T00:00:00+00:00",
            "fairness_revealed": {"server_seed": "abc123", "server_seed_hash": "x"},
        }
    }
    fair = ct._fairness_seed(state, "daily-coins")
    expected = hashlib.sha256(b"abc123|daily-coins|chain-v1").hexdigest()
    assert fair["server_seed"] == expected
    assert fair["chain"]["prev_tournament_id"] == "prev-cup"
    assert hashlib.sha256(fair["server_seed"].encode()).hexdigest() == fair["server_seed_hash"]


def test_tournament_verify_genesis():
    from backend.services import casino_tournaments as ct

    tid = "genesis-test-cup"
    state = {
        tid: {
            "id": tid,
            "template_id": "t1",
            "status": "ended",
            "fairness_revealed": ct._fairness_seed({}, "t1"),
        }
    }
    old_load = ct._load_state
    ct._load_state = lambda: state
    try:
        r = ct.verify_fairness(tid)
        assert r.get("success") is True
        assert r.get("hash_ok") is True
    finally:
        ct._load_state = old_load


def test_rg_status_for_user():
    from backend.services.casino_responsible_gaming import status_for_user

    r = status_for_user("test_rg_user", "coins")
    assert r.get("success") is True
    assert "session_loss" in r


def test_copy_trading_follow_unfollow():
    from backend.services import mn2_copy_trading as ct

    path = os.path.join(_ROOT, "data", "_test_copy_trading.json")
    old = ct._FOLLOWS
    ct._FOLLOWS = path
    try:
        if os.path.isfile(path):
            os.remove(path)
        r = ct.upsert_follower("follower_x", "agent_beta", scale=0.1)
        assert r.get("success")
        st = ct.get_follower("follower_x")
        assert st.get("following") is True
        ct.unfollow("follower_x")
        st2 = ct.get_follower("follower_x")
        assert st2.get("following") is False
    finally:
        ct._FOLLOWS = old
        if os.path.isfile(path):
            os.remove(path)


def test_context_cache_invalidate_user(monkeypatch):
    from backend.services import generator_context_cache as gcc

    cache_dir = os.path.join(_ROOT, "data", "_test_ctx_cache")
    monkeypatch.setattr(gcc, "_CACHE_DIR", cache_dir)
    os.makedirs(cache_dir, exist_ok=True)
    try:
        gcc.put("u99", {"a": 1}, {"segments": []})
        assert gcc.get("u99", {"a": 1}) is not None
        n = gcc.invalidate_user("u99")
        assert n >= 1
        assert gcc.get("u99", {"a": 1}) is None
    finally:
        for name in os.listdir(cache_dir):
            try:
                os.remove(os.path.join(cache_dir, name))
            except OSError:
                pass
        try:
            os.rmdir(cache_dir)
        except OSError:
            pass
