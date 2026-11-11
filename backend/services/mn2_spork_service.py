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
    # Exchange-wallet mega gates (v32.6.6.0) — daemon patch mn2-daemon-v1.3.2-wallet-exchange-sporks.patch
    "SPORK_116_WALLET_ONCHAIN_WITHDRAW": 10116,
    "SPORK_117_EXCHANGE_VENUE_FAILOVER": 10117,
    "SPORK_118_ANOMALY_HARD_ENFORCE": 10118,
    "SPORK_119_POR_PUBLIC_EXPORT": 10119,
    "SPORK_120_GUIDED_TRADE_EXECUTE": 10120,
    "SPORK_121_WITHDRAW_WHITELIST_REQUIRED": 10121,
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
    "SPORK_116_WALLET_ONCHAIN_WITHDRAW": SPORK_OFF,  # OFF until ops enables on-chain withdraw broadcast
    "SPORK_117_EXCHANGE_VENUE_FAILOVER": SPORK_OFF,  # OFF until ops trusts auto promote
    "SPORK_118_ANOMALY_HARD_ENFORCE": 1703122560,  # ON — fail closed on high anomaly
    "SPORK_119_POR_PUBLIC_EXPORT": SPORK_OFF,  # OFF — public PoR export gated
    "SPORK_120_GUIDED_TRADE_EXECUTE": SPORK_OFF,  # OFF — guided trade execute gated
    "SPORK_121_WITHDRAW_WHITELIST_REQUIRED": SPORK_OFF,  # OFF — whitelist fence optional
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


def wallet_onchain_withdraw_spork_ok(*, now: Optional[int] = None) -> Tuple[bool, str]:
    """SPORK_116 — site on-chain MN2 withdraw broadcast (X-40 execute)."""
    if not gates_enabled():
        return True, ""
    if maintenance_mode(now=now):
        return False, "maintenance_mode"
    if not spork_is_active("SPORK_116_WALLET_ONCHAIN_WITHDRAW", now=now, default=False):
        return False, "spork_wallet_onchain_withdraw_off"
    return True, ""


def exchange_venue_failover_spork_ok(*, now: Optional[int] = None) -> Tuple[bool, str]:
    """SPORK_117 — auto venue/RPC promote (X-08). Ranking always allowed."""
    if not gates_enabled():
        return True, ""
    if maintenance_mode(now=now):
        return False, "maintenance_mode"
    if not spork_is_active("SPORK_117_EXCHANGE_VENUE_FAILOVER", now=now, default=False):
        return False, "spork_exchange_venue_failover_off"
    return True, ""


def anomaly_hard_enforce_spork_ok(*, now: Optional[int] = None) -> Tuple[bool, str]:
    """SPORK_118 — when active, high anomaly hard-blocks (default ON)."""
    if not gates_enabled():
        return True, ""
    if not spork_is_active("SPORK_118_ANOMALY_HARD_ENFORCE", now=now, default=True):
        return False, "spork_anomaly_hard_enforce_off"
    return True, ""


def por_public_export_spork_ok(*, now: Optional[int] = None) -> Tuple[bool, str]:
    """SPORK_119 — public PoR/ledger export (X-03)."""
    if not gates_enabled():
        return True, ""
    if maintenance_mode(now=now):
        return False, "maintenance_mode"
    if not spork_is_active("SPORK_119_POR_PUBLIC_EXPORT", now=now, default=False):
        return False, "spork_por_public_export_off"
    return True, ""


def guided_trade_execute_spork_ok(*, now: Optional[int] = None) -> Tuple[bool, str]:
    """SPORK_120 — guided custodial trade execute (X-40). Quote/status always ok."""
    if not gates_enabled():
        return True, ""
    if maintenance_mode(now=now):
        return False, "maintenance_mode"
    if not spork_is_active("SPORK_120_GUIDED_TRADE_EXECUTE", now=now, default=False):
        return False, "spork_guided_trade_execute_off"
    return True, ""


def withdraw_whitelist_required(*, now: Optional[int] = None) -> bool:
    """True when SPORK_121 is active — withdrawals must use the address whitelist."""
    if not gates_enabled():
        return False
    return spork_is_active("SPORK_121_WITHDRAW_WHITELIST_REQUIRED", now=now, default=False)


def withdraw_whitelist_required_spork_ok(*, now: Optional[int] = None) -> Tuple[bool, str]:
    """SPORK_121 fence status: (enforced, reason). Not an allow/deny money gate."""
    if not gates_enabled():
        return False, "gates_disabled"
    if not spork_is_active("SPORK_121_WITHDRAW_WHITELIST_REQUIRED", now=now, default=False):
        return False, "spork_withdraw_whitelist_required_off"
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
    """Ops snapshot for exchange/casino/payout + wallet-mega spork gates."""
    ex_ok, ex_reason = exchange_live_spork_ok(now=now)
    cas_ok, cas_reason = casino_real_money_spork_ok(now=now)
    pay_ok, pay_reason = payout_live_spork_ok(now=now)
    w_ok, w_reason = wallet_onchain_withdraw_spork_ok(now=now)
    f_ok, f_reason = exchange_venue_failover_spork_ok(now=now)
    a_ok, a_reason = anomaly_hard_enforce_spork_ok(now=now)
    p_ok, p_reason = por_public_export_spork_ok(now=now)
    g_ok, g_reason = guided_trade_execute_spork_ok(now=now)
    wl_ok, wl_reason = withdraw_whitelist_required_spork_ok(now=now)
    return {
        "gates_enabled": gates_enabled(),
        "maintenance_mode": maintenance_mode(now=now),
        "exchange_live": {"allowed": ex_ok, "reason": ex_reason or None},
        "casino_real_money": {"allowed": cas_ok, "reason": cas_reason or None},
        "payout_live": {"allowed": pay_ok, "reason": pay_reason or None},
        "wallet_onchain_withdraw": {"allowed": w_ok, "reason": w_reason or None},
        "exchange_venue_failover": {"allowed": f_ok, "reason": f_reason or None},
        "anomaly_hard_enforce": {"allowed": a_ok, "reason": a_reason or None},
        "por_public_export": {"allowed": p_ok, "reason": p_reason or None},
        "guided_trade_execute": {"allowed": g_ok, "reason": g_reason or None},
        "withdraw_whitelist_required": {"enforced": wl_ok, "reason": wl_reason or None},
        "sporks": {
            "SPORK_112_EXCHANGE_LIVE_TRADING": spork_is_active("SPORK_112_EXCHANGE_LIVE_TRADING", now=now, default=False),
            "SPORK_113_CASINO_REAL_MONEY": spork_is_active("SPORK_113_CASINO_REAL_MONEY", now=now, default=True),
            "SPORK_114_PAYOUT_LIVE": spork_is_active("SPORK_114_PAYOUT_LIVE", now=now, default=False),
            "SPORK_115_MAINTENANCE_MODE": maintenance_mode(now=now),
            "SPORK_116_WALLET_ONCHAIN_WITHDRAW": spork_is_active("SPORK_116_WALLET_ONCHAIN_WITHDRAW", now=now, default=False),
            "SPORK_117_EXCHANGE_VENUE_FAILOVER": spork_is_active("SPORK_117_EXCHANGE_VENUE_FAILOVER", now=now, default=False),
            "SPORK_118_ANOMALY_HARD_ENFORCE": spork_is_active("SPORK_118_ANOMALY_HARD_ENFORCE", now=now, default=True),
            "SPORK_119_POR_PUBLIC_EXPORT": spork_is_active("SPORK_119_POR_PUBLIC_EXPORT", now=now, default=False),
            "SPORK_120_GUIDED_TRADE_EXECUTE": spork_is_active("SPORK_120_GUIDED_TRADE_EXECUTE", now=now, default=False),
            "SPORK_121_WITHDRAW_WHITELIST_REQUIRED": spork_is_active(
                "SPORK_121_WITHDRAW_WHITELIST_REQUIRED", now=now, default=False
            ),
        },
        "unused_app_sporks_note": (
            "Most SPORK_2–111 flags are daemon/consensus only; site gates start at 112+."
        ),
        "new_wallet_gates": [
            "SPORK_116_WALLET_ONCHAIN_WITHDRAW",
            "SPORK_117_EXCHANGE_VENUE_FAILOVER",
            "SPORK_118_ANOMALY_HARD_ENFORCE",
            "SPORK_119_POR_PUBLIC_EXPORT",
            "SPORK_120_GUIDED_TRADE_EXECUTE",
            "SPORK_121_WITHDRAW_WHITELIST_REQUIRED",
        ],
    }


def services_enforcement_active(*, now: Optional[int] = None) -> bool:
    """SPORK_101 — advisory for ops mesh (X-09): services enforcement expected on."""
    if not gates_enabled():
        return False
    return spork_is_active("SPORK_101_SERVICES_ENFORCEMENT", now=now, default=True)


def unused_and_new_spork_recap() -> Dict[str, Any]:
    """Inventory for ops: unused-by-app, fixed holds, gaps, and new wallet gates."""
    app_gated = {
        "SPORK_112_EXCHANGE_LIVE_TRADING",
        "SPORK_113_CASINO_REAL_MONEY",
        "SPORK_114_PAYOUT_LIVE",
        "SPORK_115_MAINTENANCE_MODE",
        "SPORK_116_WALLET_ONCHAIN_WITHDRAW",
        "SPORK_117_EXCHANGE_VENUE_FAILOVER",
        "SPORK_118_ANOMALY_HARD_ENFORCE",
        "SPORK_119_POR_PUBLIC_EXPORT",
        "SPORK_120_GUIDED_TRADE_EXECUTE",
        "SPORK_121_WITHDRAW_WHITELIST_REQUIRED",
    }
    # Fixed: previously unused-by-app but now advisory on the exchange wallet surface.
    fixed_advisory = {
        "SPORK_101_SERVICES_ENFORCEMENT": {
            "role": "advisory_ops_mesh",
            "maps_to": "X-09",
            "note": "Surfaced on mesh health; does not move money.",
        },
    }
    intentional_hold = {
        "SPORK_112_EXCHANGE_LIVE_TRADING": "default_off_until_ops",
        "SPORK_114_PAYOUT_LIVE": "default_off_until_ops",
    }
    unused = sorted(
        name for name in SPORK_IDS if name not in app_gated and name not in fixed_advisory
    )
    default_off = sorted(name for name, val in SPORK_DEFAULTS.items() if val >= SPORK_OFF)
    gaps = [i for i in range(10101, 10116) if i not in SPORK_IDS.values()]
    return {
        "success": True,
        "defined_count": len(SPORK_IDS),
        "app_gated": sorted(app_gated),
        "fixed_advisory": fixed_advisory,
        "intentional_hold": intentional_hold,
        "unused_by_app": unused,
        "unused_by_app_count": len(unused),
        "default_off": default_off,
        "id_gaps_10101_10115": gaps,
        "new_wallet_gates": [
            {
                "name": "SPORK_116_WALLET_ONCHAIN_WITHDRAW",
                "id": 10116,
                "default": "OFF",
                "maps_to": "X-40 / X-38",
            },
            {
                "name": "SPORK_117_EXCHANGE_VENUE_FAILOVER",
                "id": 10117,
                "default": "OFF",
                "maps_to": "X-08",
            },
            {
                "name": "SPORK_118_ANOMALY_HARD_ENFORCE",
                "id": 10118,
                "default": "ON",
                "maps_to": "X-46",
            },
            {
                "name": "SPORK_119_POR_PUBLIC_EXPORT",
                "id": 10119,
                "default": "OFF",
                "maps_to": "X-03",
            },
            {
                "name": "SPORK_120_GUIDED_TRADE_EXECUTE",
                "id": 10120,
                "default": "OFF",
                "maps_to": "X-40",
            },
            {
                "name": "SPORK_121_WITHDRAW_WHITELIST_REQUIRED",
                "id": 10121,
                "default": "OFF",
                "maps_to": "X-38",
            },
        ],
        "doc": "docs/plans/2026-11-11-mn2-sporks-recap-and-new-gates.md",
    }
