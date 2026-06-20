"""Tier D — LiveKit voice + mobile IAP."""
from __future__ import annotations

import os
import shutil
import tempfile

import pytest


def test_livekit_stub_when_unconfigured(monkeypatch):
    monkeypatch.delenv("LIVEKIT_URL", raising=False)
    monkeypatch.delenv("LIVEKIT_API_KEY", raising=False)
    monkeypatch.delenv("LIVEKIT_API_SECRET", raising=False)

    from backend.services.camgirls_livekit_service import issue_voice_token, public_status

    status = public_status()
    assert status["configured"] is False
    assert status["mode"] == "stub"

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("backend.services.camgirls_service.user_has_unlock", lambda u, p: True)
        out = issue_voice_token("fan1", "nova", require_unlock=True)
    assert out["success"] is True
    assert out["mode"] == "stub"
    assert out["token"] is None


def test_livekit_token_when_configured(monkeypatch):
    monkeypatch.setenv("LIVEKIT_URL", "wss://test.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "APIKEY")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "secret")

    jwt = pytest.importorskip("jwt")
    if not hasattr(jwt, "encode"):
        pytest.skip("PyJWT not installed")

    from backend.services.camgirls_livekit_service import issue_voice_token

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("backend.services.camgirls_service.user_has_unlock", lambda u, p: True)
        out = issue_voice_token("fan1", "nova")
    assert out["success"] is True
    assert out["mode"] == "live"
    assert out["token"]


def test_mobile_iap_catalog():
    from backend.services.monetization_config_service import reload_monetization_config
    from backend.services.mobile_iap_service import public_catalog

    reload_monetization_config()
    cat = public_catalog()
    assert cat["success"] is True
    assert any(p["id"] == "com.masternoder.coins500" for p in cat["products"])


def test_mobile_iap_stub_fulfill(monkeypatch):
    from backend.services.monetization_config_service import reload_monetization_config
    from backend.services.mobile_iap_service import fulfill_purchase

    reload_monetization_config()
    tmp_dir = tempfile.mkdtemp(prefix="iap_")
    log_path = os.path.join(tmp_dir, "mobile_iap_receipts.jsonl")
    monkeypatch.setattr("backend.services.mobile_iap_service._RECEIPTS_PATH", log_path)

    db_calls = []

    class FakeDB:
        def add_points(self, **kwargs):
            db_calls.append(kwargs)
            return {"success": True}

    monkeypatch.setattr("backend.services.unified_points_database.unified_points_db", FakeDB())

    out = fulfill_purchase(
        "mobile_user",
        platform="apple",
        store_product_id="com.masternoder.coins100",
        receipt_data="stub_ok",
    )
    assert out["success"] is True
    assert out["coins_granted"] == 100
    assert db_calls and db_calls[0]["amount"] == 100
    shutil.rmtree(tmp_dir, ignore_errors=True)
