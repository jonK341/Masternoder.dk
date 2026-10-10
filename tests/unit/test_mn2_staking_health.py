"""staking_health prefers getstakingstatus / getinfo over misleading getstakinginfo."""

from __future__ import annotations

import backend.services.mn2_rpc_client as rpc


def test_staking_health_prefers_status_object(monkeypatch):
    monkeypatch.setattr(
        rpc,
        "getstakinginfo",
        lambda timeout_sec=None: {"result": {"enabled": False, "staking": False}, "error": None},
    )
    monkeypatch.setattr(
        rpc,
        "getstakingstatus",
        lambda timeout_sec=None: {
            "result": {
                "validtime": True,
                "haveconnections": True,
                "walletunlocked": True,
                "mintablecoins": True,
                "enoughcoins": True,
                "mnsync": True,
                "staking status": True,
            },
            "error": None,
        },
    )
    monkeypatch.setattr(rpc, "getwalletinfo", lambda timeout_sec=None: {"result": {"balance": 1}, "error": None})
    monkeypatch.setattr(rpc, "getinfo", lambda timeout_sec=None: {"result": {}, "error": None})
    rpc._STAKING_HEALTH_CACHE["value"] = None
    rpc._STAKING_HEALTH_CACHE["ts"] = 0.0
    out = rpc.staking_health()
    assert out["staking_active"] is True
    assert out["status"] == "active"


def test_staking_health_getinfo_string_fallback(monkeypatch):
    monkeypatch.setattr(
        rpc,
        "getstakinginfo",
        lambda timeout_sec=None: {"error": "Method not found", "result": None},
    )
    monkeypatch.setattr(
        rpc,
        "getstakingstatus",
        lambda timeout_sec=None: {"error": "Method not found", "result": None},
    )
    monkeypatch.setattr(
        rpc,
        "getinfo",
        lambda timeout_sec=None: {"result": {"staking status": "Staking Active"}, "error": None},
    )
    monkeypatch.setattr(rpc, "getwalletinfo", lambda timeout_sec=None: {"result": {}, "error": None})
    rpc._STAKING_HEALTH_CACHE["value"] = None
    rpc._STAKING_HEALTH_CACHE["ts"] = 0.0
    out = rpc.staking_health()
    assert out["staking_active"] is True
    assert out["status"] == "active"


def test_staking_health_pivx_shape_from_getstakinginfo(monkeypatch):
    monkeypatch.setattr(
        rpc,
        "getstakinginfo",
        lambda timeout_sec=None: {
            "result": {
                "walletunlocked": True,
                "mintablecoins": True,
                "enoughcoins": True,
                "mnsync": True,
                "haveconnections": True,
                "staking status": True,
            },
            "error": None,
        },
    )
    monkeypatch.setattr(
        rpc,
        "getstakingstatus",
        lambda timeout_sec=None: {"error": "duplicate", "result": None},
    )
    monkeypatch.setattr(rpc, "getwalletinfo", lambda timeout_sec=None: {"result": {}, "error": None})
    monkeypatch.setattr(rpc, "getinfo", lambda timeout_sec=None: {"result": {}, "error": None})
    rpc._STAKING_HEALTH_CACHE["value"] = None
    rpc._STAKING_HEALTH_CACHE["ts"] = 0.0
    out = rpc.staking_health()
    assert out["staking_active"] is True
