"""
MasterNoder2 spork helpers — mirrors external/MasterNoder2/src/spork.h semantics.

Sporks are signed, network-wide feature flags (Dash/PIVX style). A spork is
*active* when its value is less than the current unix time (see IsSporkActive in
spork.cpp). Value 4070908800 (~2099) means OFF for enforcement sporks.

Python services read spork state via RPC (``spork show`` / ``spork active``) with
a short TTL cache. Set ``MN2_SPORK_GATES=0`` to bypass gates in dev/test, or
``MN2_SPORK_OVERRIDE_JSON='{"SPORK_112_EXCHANGE_LIVE_TRADING":1703122560}'`` to
inject values without a daemon.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional, Tuple

from backend.services import mn2_rpc_client as rpc

# Sentinel used throughout MasterNoder2 for "spork disabled"
SPORK_OFF = 4070908800

SPORK_IDS: Dict[str, int] = {
    "SPORK_2_SWIFTTX": 10001,
    "SPORK_3_SWIFTTX_BLOCK_FILTERING": 10002,
    "SPORK_5_MAX_VALUE": 10004,
    "SPORK_6_ENABLE_DIP0001": 10005,
    "SPORK_7_MASTERNODE_SCANNING": 10006,
    "SPORK_8_MASTERNODE_PAYMENT_ENFORCEMENT": 10007,
    "SPORK_9_MASTERNODE_BUDGET_ENFORCEMENT": 10008,
    "SPORK_10_MASTERNODE_PAY_UPDATED_NODES": 10009,
    "SPORK_13_ENABLE_SUPERBLOCKS": 10012,
    "SPORK_14_NEW_PROTOCOL_ENFORCEMENT": 10013,
    "SPORK_15_NEW_PROTOCOL_ENFORCEMENT_2": 10014,
    "SPORK_16_ZEROCOIN_MAINTENANCE_MODE": 10015,
    "SPORK_17_QUORUM_DKG_ENABLED": 10016,
    "SPORK_18_ENABLE_VOTING_SYSTEM": 10017,
    "SPORK_19_CHAINLOCKS_ENABLED": 10018,
    "SPORK_20_DEVELOPER_PAYMENT_ENFORCEMENT": 10019,
    "SPORK_21_QUORUM_ALL_CONNECTED": 10021,
    "SPORK_22_ENABLE_TX_COMPRESSION": 10022,
    "SPORK_23_QUORUM_POSE": 10023,
    "SPORK_24_ENABLE_SIPHASH": 10024,
    "SPORK_25_ENABLE_MASTERNODER2_SERVER": 10025,
    "SPORK_28_ENABLE_TIMELOCK": 10028,
    "SPORK_29_ENABLE_ANONYMITY": 10029,
    "SPORK_101_SERVICES_ENFORCEMENT": 10101,
    "SPORK_104_MAX_BLOCK_TIME": 10104,
    "SPORK_106_STAKING_SKIP_MN_SYNC": 10106,
    "SPORK_109_FORCE_ENABLED_VOTED_MASTERNODE": 10109,
    "SPORK_110_FORCE_ENABLED_MASTERNODE_PAYMENT": 10110,
    "SPORK_111_ALLOW_DUPLICATE_MN_IPS": 10111,
    "SPORK_112_EXCHANGE_LIVE_TRADING": 10112,
    "SPORK_113_CASINO_REAL_MONEY": 10113,
    "SPORK_114_PAYOUT_LIVE": 10114,
    "SPORK_115_MAINTENANCE_MODE": 10115,
}

SPORK_DEFAULTS: Dict[str, int] = {
    "SPORK_2_SWIFTTX": 978307200,
    "SPORK_3_SWIFTTX_BLOCK_FILTERING": 1424217600,
    "SPORK_5_MAX_VALUE": 1000,
    "SPORK_6_ENABLE_DIP0001": 1703122560,
    "SPORK_7_MASTERNODE_SCANNING": 978307200,
    "SPORK_8_MASTERNODE_PAYMENT_ENFORCEMENT": SPORK_OFF,
    "SPORK_9_MASTERNODE_BUDGET_ENFORCEMENT": SPORK_OFF,
    "SPORK_10_MASTERNODE_PAY_UPDATED_NODES": SPORK_OFF,
    "SPORK_13_ENABLE_SUPERBLOCKS": SPORK_OFF,
    "SPORK_14_NEW_PROTOCOL_ENFORCEMENT": SPORK_OFF,
    "SPORK_15_NEW_PROTOCOL_ENFORCEMENT_2": SPORK_OFF,
    "SPORK_16_ZEROCOIN_MAINTENANCE_MODE": SPORK_OFF,
    "SPORK_17_QUORUM_DKG_ENABLED": 1703122560,
    "SPORK_18_ENABLE_VOTING_SYSTEM": 1703122560,
    "SPORK_19_CHAINLOCKS_ENABLED": 1703122560,
    "SPORK_20_DEVELOPER_PAYMENT_ENFORCEMENT": 1703122560,
    "SPORK_21_QUORUM_ALL_CONNECTED": 1703122560,
    "SPORK_22_ENABLE_TX_COMPRESSION": 1703122560,
    "SPORK_23_QUORUM_POSE": 1703122560,
    "SPORK_24_ENABLE_SIPHASH": 1703122560,
    "SPORK_25_ENABLE_MASTERNODER2_SERVER": SPORK_OFF,
    "SPORK_28_ENABLE_TIMELOCK": 1734658560,
    "SPORK_29_ENABLE_ANONYMITY": 1734658560,
    "SPORK_101_SERVICES_ENFORCEMENT": 1703122560,
    "SPORK_104_MAX_BLOCK_TIME": 600,
    "SPORK_106_STAKING_SKIP_MN_SYNC": 1703122560,
    "SPORK_109_FORCE_ENABLED_VOTED_MASTERNODE": 1703122560,
    "SPORK_110_FORCE_ENABLED_MASTERNODE_PAYMENT": SPORK_OFF,
    "SPORK_111_ALLOW_DUPLICATE_MN_IPS": 1703122560,
    "SPORK_112_EXCHANGE_LIVE_TRADING": SPORK_OFF,
    "SPORK_113_CASINO_REAL_MONEY": 1703122560,
    "SPORK_114_PAYOUT_LIVE": SPORK_OFF,
    "SPORK_115_MAINTENANCE_MODE": SPORK_OFF,
}

_ID_TO_NAME = {v: k for k, v in SPORK_IDS.items()}

_CACHE_TTL_SEC = 30.0
_cache: Dict[str, Any] = {"at": 0.0, "values": {}, "active": {}}


def spork_id_by_name(name: str) -> Optional[int]:
    return SPORK_IDS.get(name)


def spork_name_by_id(spork_id: int) -> Optional[str]:
    return _ID_TO_NAME.get(spork_id)


def is_spork_active(value: int, *, now: Optional[int] = None) -> bool:
    """Match C++ IsSporkActive: active when value < current unix time."""
    if value < 0:
        return False
    ts = int(now if now is not None else time.time())
    return value < ts


def is_spork_off(value: int) -> bool:
    return value >= SPORK_OFF


def gates_enabled() -> bool:
    return os.environ.get("MN2_SPORK_GATES", "1").strip().lower() not in ("0", "false", "no", "off")


def _override_values() -> Dict[str, int]:
    raw = (os.environ.get("MN2_SPORK_OVERRIDE_JSON") or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        out: Dict[str, int] = {}
        for k, v in data.items():
            if k in SPORK_IDS:
                out[k] = int(v)
        return out
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _default_value(name: str) -> int:
    return int(SPORK_DEFAULTS.get(name, SPORK_OFF))


def spork_value(name: str, *, now: Optional[int] = None) -> int:
    """Current spork value (override → RPC cache → default)."""
    if name not in SPORK_IDS:
        return SPORK_OFF
    overrides = _override_values()
    if name in overrides:
        return int(overrides[name])
    _refresh_cache(now=now)
    val = _cache["values"].get(name)
    if val is None:
        return _default_value(name)
    return int(val)


def spork_is_active(name: str, *, now: Optional[int] = None, default: Optional[bool] = None) -> bool:
    """Whether spork *name* is active, using RPC/override/default."""
    if name not in SPORK_IDS:
        return bool(default) if default is not None else False
    overrides = _override_values()
    if name in overrides:
        return is_spork_active(int(overrides[name]), now=now)
    if not gates_enabled() and default is not None:
        return default
    _refresh_cache(now=now)
    cached = _cache["active"].get(name)
    if cached is not None:
        return bool(cached)
    val = spork_value(name, now=now)
    if default is not None and val == _default_value(name) and not _cache["values"]:
        return default
    return is_spork_active(val, now=now)


def _refresh_cache(*, now: Optional[int] = None, force: bool = False) -> None:
    ts = float(now if now is not None else time.time())
    if not force and (ts - float(_cache.get("at") or 0)) < _CACHE_TTL_SEC:
        return
    if _override_values():
        _cache["at"] = ts
        return
    try:
        show = show_sporks(timeout_sec=2.0)
        active = active_sporks(timeout_sec=2.0)
        values = show.get("result") if isinstance(show, dict) else None
        act = active.get("result") if isinstance(active, dict) else None
        if isinstance(values, dict):
            _cache["values"] = {k: int(v) for k, v in values.items() if k in SPORK_IDS}
        if isinstance(act, dict):
            _cache["active"] = {k: bool(v) for k, v in act.items() if k in SPORK_IDS}
        _cache["at"] = ts
    except Exception:
        _cache["at"] = ts


def invalidate_cache() -> None:
    _cache["at"] = 0.0
    _cache["values"] = {}
    _cache["active"] = {}


def require_spork(name: str, *, feature: str = "") -> Optional[str]:
    """Return an error string when *name* is not active; None if allowed."""
    if not gates_enabled():
        return None
    if spork_is_active(name):
        return None
    label = feature or name
    return f"{label} blocked by inactive spork {name}"


def maintenance_mode(*, now: Optional[int] = None) -> bool:
    return spork_is_active("SPORK_115_MAINTENANCE_MODE", now=now)


def exchange_live_spork_ok(*, now: Optional[int] = None) -> Tuple[bool, str]:
    if not gates_enabled():
        return True, ""
    if maintenance_mode(now=now):
        return False, "maintenance_mode"
    if not spork_is_active("SPORK_112_EXCHANGE_LIVE_TRADING", now=now, default=False):
        return False, "spork_exchange_live_off"
    return True, ""


def casino_real_money_spork_ok(*, now: Optional[int] = None) -> Tuple[bool, str]:
    if not gates_enabled():
        return True, ""
    if maintenance_mode(now=now):
        return False, "maintenance_mode"
    if not spork_is_active("SPORK_113_CASINO_REAL_MONEY", now=now, default=True):
        return False, "spork_casino_real_money_off"
    return True, ""


def payout_live_spork_ok(*, now: Optional[int] = None) -> Tuple[bool, str]:
    if not gates_enabled():
        return True, ""
    if maintenance_mode(now=now):
        return False, "maintenance_mode"
    if not spork_is_active("SPORK_114_PAYOUT_LIVE", now=now, default=False):
        return False, "spork_payout_live_off"
    return True, ""


def show_sporks(*, timeout_sec: Optional[float] = None) -> Dict[str, Any]:
    """RPC spork show — current values for all known sporks."""
    if timeout_sec is not None:
        return rpc._call("spork", ["show"], timeout_sec=timeout_sec)
    return rpc._call("spork", ["show"])


def active_sporks(*, timeout_sec: Optional[float] = None) -> Dict[str, Any]:
    """RPC spork active — boolean active state per spork."""
    if timeout_sec is not None:
        return rpc._call("spork", ["active"], timeout_sec=timeout_sec)
    return rpc._call("spork", ["active"])


def update_spork(name: str, value: int, *, timeout_sec: Optional[float] = None) -> Dict[str, Any]:
    """
    RPC spork <name> <value> — requires daemon started with -sporkkey (chain owner).
    Returns daemon result string ('success' / 'failure') on success.
    """
    if spork_id_by_name(name) is None:
        return {"error": f"unknown spork name: {name}", "result": None}
    if timeout_sec is not None:
        return rpc._call("spork", [name, int(value)], timeout_sec=timeout_sec)
    return rpc._call("spork", [name, int(value)])


def interpret_spork(name: str, value: int, *, now: Optional[int] = None) -> Dict[str, Any]:
    """Human-readable summary for ops scripts and dashboards."""
    active = is_spork_active(value, now=now)
    off = is_spork_off(value)
    return {
        "name": name,
        "value": value,
        "active": active,
        "off": off,
        "default": SPORK_DEFAULTS.get(name),
    }


def gate_status(*, now: Optional[int] = None) -> Dict[str, Any]:
    """Ops snapshot for exchange/casino/payout spork gates."""
    ex_ok, ex_reason = exchange_live_spork_ok(now=now)
    cas_ok, cas_reason = casino_real_money_spork_ok(now=now)
    pay_ok, pay_reason = payout_live_spork_ok(now=now)
    return {
        "gates_enabled": gates_enabled(),
        "maintenance_mode": maintenance_mode(now=now),
        "exchange_live": {"allowed": ex_ok, "reason": ex_reason or None},
        "casino_real_money": {"allowed": cas_ok, "reason": cas_reason or None},
        "payout_live": {"allowed": pay_ok, "reason": pay_reason or None},
        "sporks": {
            "SPORK_112_EXCHANGE_LIVE_TRADING": spork_is_active("SPORK_112_EXCHANGE_LIVE_TRADING", now=now, default=False),
            "SPORK_113_CASINO_REAL_MONEY": spork_is_active("SPORK_113_CASINO_REAL_MONEY", now=now, default=True),
            "SPORK_114_PAYOUT_LIVE": spork_is_active("SPORK_114_PAYOUT_LIVE", now=now, default=False),
            "SPORK_115_MAINTENANCE_MODE": maintenance_mode(now=now),
        },
    }
