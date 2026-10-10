"""Camgirls social features — favorites, fan club, goals, offline."""
import json
import os

import pytest

from tests.unit.test_camgirls_service import CamgirlsTestBase


class SocialTestBase(CamgirlsTestBase):
    def setUp(self):
        super().setUp()
        self._fav = os.path.join(self.tmp, "camgirls_favorites.json")
        self._fc = os.path.join(self.tmp, "camgirls_fanclub.json")
        self._offline = os.path.join(self.tmp, "camgirls_offline.jsonl")
        self._private = os.path.join(self.tmp, "camgirls_private.json")
        import backend.services.camgirls_social_service as soc

        self._orig_soc = (soc._FAVORITES_FILE, soc._FANCLUB_FILE, soc._OFFLINE_FILE, soc._PRIVATE_FILE, soc._TIPS_FILE)
        soc._FAVORITES_FILE = self._fav
        soc._FANCLUB_FILE = self._fc
        soc._OFFLINE_FILE = self._offline
        soc._PRIVATE_FILE = self._private
        soc._TIPS_FILE = self._tips

    def tearDown(self):
        import backend.services.camgirls_social_service as soc

        soc._FAVORITES_FILE, soc._FANCLUB_FILE, soc._OFFLINE_FILE, soc._PRIVATE_FILE, soc._TIPS_FILE = self._orig_soc
        super().tearDown()


def test_toggle_favorite():
    t = SocialTestBase()
    t.setUp()
    try:
        from backend.services.camgirls_social_service import is_favorite, toggle_favorite

        r = toggle_favorite("u1", "p1")
        assert r.get("success") is True
        assert r.get("favorite") is True
        assert is_favorite("u1", "p1")
        r2 = toggle_favorite("u1", "p1")
        assert r2.get("favorite") is False
    finally:
        t.tearDown()


def test_fan_club_requires_unlock():
    t = SocialTestBase()
    t.setUp()
    try:
        from backend.services.camgirls_social_service import join_fan_club
        from backend.services.camgirls_service import record_age_verification

        record_age_verification("buyer", birth_year=1990)
        blocked = join_fan_club("buyer", "p1")
        assert blocked.get("code") == "unlock_required"
    finally:
        t.tearDown()


def test_goal_status_from_tips():
    t = SocialTestBase()
    t.setUp()
    try:
        from backend.services.camgirls_social_service import get_goal_status

        with open(t._tips, "w", encoding="utf-8") as f:
            f.write(json.dumps({"performer_id": "p1", "amount_mn2": 50, "user_id": "a"}) + "\n")
        g = get_goal_status("p1")
        assert g.get("raised_mn2") == 50
        assert g.get("percent") >= 0
    finally:
        t.tearDown()


def test_chat_history_route():
    from flask import Flask

    from backend.routes.camgirls_routes import camgirls_bp

    app = Flask(__name__)
    app.register_blueprint(camgirls_bp)
    client = app.test_client()
    r = client.get("/api/camgirls/performers/p1/chat/history?user_id=u1")
    assert r.status_code in (200, 400, 403)
