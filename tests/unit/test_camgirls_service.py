"""Camgirls Phase 1 — catalog, unlock, tip, age gate."""
import json
import os
import pytest

from tests.unit.test_mn2_staking import StakingTestBase


class CamgirlsTestBase(StakingTestBase):
    def setUp(self):
        super().setUp()
        self._perf = os.path.join(self.tmp, "camgirls_performers.json")
        self._unlock = os.path.join(self.tmp, "camgirls_unlocks.json")
        self._age = os.path.join(self.tmp, "camgirls_age_verified.json")
        self._tips = os.path.join(self.tmp, "camgirls_tips.jsonl")
        self._chat = os.path.join(self.tmp, "camgirls_chat.jsonl")
        self._payout = os.path.join(self.tmp, "camgirls_payout_addresses.json")
        with open(self._perf, "w", encoding="utf-8") as f:
            json.dump({
                "performers": [{
                    "id": "p1",
                    "display_name": "Test",
                    "bio": "Test persona bio",
                    "unlock_price_mn2": 10,
                    "chat_price_mn2": 2,
                    "tip_min_mn2": 5,
                    "active": True,
                }],
            }, f)
        with open(self._payout, "w", encoding="utf-8") as f:
            json.dump({"performers": {"p1": {"address": "JTestDaemon", "created_at": "2026-01-01T00:00:00Z"}}}, f)
        import backend.services.camgirls_service as cg
        import backend.services.camgirls_payout_service as cgp
        self._orig = (cg._PERFORMERS_FILE, cg._UNLOCKS_FILE, cg._AGE_FILE, cg._TIPS_FILE, cg._CHAT_FILE)
        self._orig_payout = cgp._PAYOUT_FILE
        cg._PERFORMERS_FILE = self._perf
        cg._UNLOCKS_FILE = self._unlock
        cg._AGE_FILE = self._age
        cg._TIPS_FILE = self._tips
        cg._CHAT_FILE = self._chat
        cgp._PAYOUT_FILE = self._payout
        import backend.services.unified_points_database as upd
        self._orig_upd = upd.unified_points_db
        upd.unified_points_db = self.fake

    def tearDown(self):
        import backend.services.camgirls_service as cg
        import backend.services.camgirls_payout_service as cgp
        import backend.services.unified_points_database as upd
        cg._PERFORMERS_FILE, cg._UNLOCKS_FILE, cg._AGE_FILE, cg._TIPS_FILE, cg._CHAT_FILE = self._orig
        cgp._PAYOUT_FILE = self._orig_payout
        upd.unified_points_db = self._orig_upd
        super().tearDown()


def test_list_performers():
    t = CamgirlsTestBase()
    t.setUp()
    try:
        from backend.services.camgirls_service import list_performers_catalog
        r = list_performers_catalog(user_id="u1")
        assert r["success"] is True
        assert len(r["performers"]) == 1
    finally:
        t.tearDown()


def test_unlock_requires_age_then_succeeds():
    t = CamgirlsTestBase()
    t.setUp()
    try:
        from backend.services.camgirls_service import unlock_performer, record_age_verification
        t._credit("buyer", 100.0)
        blocked = unlock_performer("buyer", "p1")
        assert blocked.get("code") == "age_verification_required"
        record_age_verification("buyer", birth_year=1990)
        ok = unlock_performer("buyer", "p1")
        assert ok.get("success") is True
        assert ok.get("amount_mn2") == 10
    finally:
        t.tearDown()


def test_tip_performer():
    t = CamgirlsTestBase()
    t.setUp()
    try:
        from backend.services.camgirls_service import tip_performer, record_age_verification
        t._credit("buyer", 50.0)
        record_age_verification("buyer", birth_year=1990)
        ok = tip_performer("buyer", "p1", 10)
        assert ok.get("success") is True
        assert ok.get("amount_mn2") == 10
        assert ok.get("payout_address") == "JTestDaemon"
    finally:
        t.tearDown()


def test_chat_requires_unlock_then_debits(monkeypatch):
    t = CamgirlsTestBase()
    t.setUp()
    try:
        from backend.services import agent_ai_router
        from backend.services.camgirls_service import chat_with_performer, record_age_verification, unlock_performer

        class _MockResp:
            success = True
            content = "Hey there!"

        monkeypatch.setattr(
            agent_ai_router,
            "routed_chat",
            lambda messages, task_kind, user_id, **kwargs: (_MockResp(), {"trace_id": "t1"}),
        )
        t._credit("buyer", 50.0)
        record_age_verification("buyer", birth_year=1990)
        blocked = chat_with_performer("buyer", "p1", "Hello")
        assert blocked.get("code") == "unlock_required"
        unlock_performer("buyer", "p1")
        ok = chat_with_performer("buyer", "p1", "Hello")
        assert ok.get("success") is True
        assert ok.get("reply") == "Hey there!"
        assert ok.get("amount_mn2") == 2
        assert os.path.isfile(t._chat)
    finally:
        t.tearDown()


def test_deactivate_demo_performers():
    t = CamgirlsTestBase()
    t.setUp()
    try:
        from backend.services.camgirls_service import deactivate_demo_performers, list_performers_catalog
        with open(t._perf, "w", encoding="utf-8") as f:
            json.dump({
                "performers": [
                    {"id": "performer_demo_x", "display_name": "Demo", "active": True},
                    {"id": "performer_real_1", "display_name": "Real", "active": True},
                ],
            }, f)
        result = deactivate_demo_performers()
        assert result.get("count") == 1
        catalog = list_performers_catalog(user_id="u1")
        ids = [p["id"] for p in catalog.get("performers") or []]
        assert "performer_demo_x" not in ids
        assert "performer_real_1" in ids
    finally:
        t.tearDown()
