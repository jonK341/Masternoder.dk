"""Camgirls daemon payout address provisioning."""
import json
import os

import pytest

from tests.unit.test_camgirls_service import CamgirlsTestBase


def test_get_or_create_uses_existing(monkeypatch):
    t = CamgirlsTestBase()
    t.setUp()
    try:
        from backend.services import camgirls_payout_service as cgp

        r = cgp.get_or_create_payout_address("p1")
        assert r.get("success") is True
        assert r.get("payout_address") == "JTestDaemon"
        assert r.get("created") is False
        monkeypatch.setattr(cgp, "_generate_daemon_address", lambda: {"success": True, "deposit_address": "JNew"})
        r2 = cgp.get_or_create_payout_address("p1")
        assert r2.get("payout_address") == "JTestDaemon"
    finally:
        t.tearDown()


def test_get_or_create_calls_daemon(monkeypatch):
    t = CamgirlsTestBase()
    t.setUp()
    try:
        from backend.services import camgirls_payout_service as cgp

        with open(t._payout, "w", encoding="utf-8") as f:
            json.dump({"performers": {}}, f)
        monkeypatch.setattr(
            cgp,
            "_generate_daemon_address",
            lambda: {"success": True, "deposit_address": "JFromDaemon123"},
        )
        r = cgp.get_or_create_payout_address("p1")
        assert r.get("success") is True
        assert r.get("payout_address") == "JFromDaemon123"
        assert r.get("created") is True
        store = json.load(open(t._payout, encoding="utf-8"))
        assert store["performers"]["p1"]["address"] == "JFromDaemon123"
    finally:
        t.tearDown()


def test_upsert_strips_manual_payout_address(monkeypatch):
    t = CamgirlsTestBase()
    t.setUp()
    try:
        from backend.services.camgirls_service import upsert_performer

        monkeypatch.setattr(
            "backend.services.camgirls_payout_service.get_or_create_payout_address",
            lambda pid: {"success": True, "payout_address": "JDaemon", "created": True},
        )
        upsert_performer({
            "id": "p2",
            "display_name": "Two",
            "unlock_price_mn2": 5,
            "payout_address": "JManualShouldBeIgnored",
            "active": True,
        })
        data = json.load(open(t._perf, encoding="utf-8"))
        row = next(r for r in data["performers"] if r["id"] == "p2")
        assert "payout_address" not in row
    finally:
        t.tearDown()
