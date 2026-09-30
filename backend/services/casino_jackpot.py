"""
Progressive jackpot pools for the casino.

Each currency rail (coins / mn2 / usd) has its own **separate** pool, seeded by
the house and grown by a small contribution from every eligible bet. A pool
drops when a slot jackpot symbol lands or on a rare per-bet "must-drop" roll;
the whole pool is awarded to the player and the house re-seeds it.

Conservation discipline (mirrors MN2_STAKING_PLAN.md §8): every contribution,
award, and seed is an explicit entry in `logs/casino_jackpot_ledger.jsonl`, and
each pool satisfies the invariant

    pool == total_seeded + total_contributed - total_awarded   (± rounding)

which `reconcile()` verifies. Money is credited through casino_service's single
balance path, so jackpot wins respect the same per-rail accounting as bets.

This never reads or touches staked MN2 — only the liquid casino balances.
"""
from __future__ import annotations

import json
import os
import random
import threading
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()

_RAIL_KEYS = ("coins", "mn2", "usd")


def _cs():
    # Lazy import avoids a top-level cycle (casino_service imports this module).
    from backend.services import casino_service
    return casino_service


def _log_dir() -> str:
    return _cs()._log_dir()


def _iso() -> str:
    return _cs()._iso()


def _state_path() -> str:
    d = _log_dir()
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "casino_jackpots.json")


def _ledger_path() -> str:
    d = _log_dir()
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "casino_jackpot_ledger.jsonl")


def _config() -> Dict[str, Any]:
    cfg = _cs()._load_config()
    jp = cfg.get("jackpot") if isinstance(cfg.get("jackpot"), dict) else {}
    rails_cfg = jp.get("rails") if isinstance(jp.get("rails"), dict) else {}
    rails: Dict[str, Dict[str, float]] = {}
    for key in _RAIL_KEYS:
        r = rails_cfg.get(key)
        if isinstance(r, dict):
            rails[key] = {
                "seed": float(r.get("seed") or 0),
                "contribution_rate": float(r.get("contribution_rate") or 0),
                "win_chance": float(r.get("win_chance") or 0),
                "reseed": float(r.get("reseed") if r.get("reseed") is not None else r.get("seed") or 0),
            }
    return {
        "enabled": bool(jp.get("enabled")),
        "rails": rails,
        "slot_jackpot_symbol_awards": bool(jp.get("slot_jackpot_symbol_awards", True)),
    }


def _load_state() -> Dict[str, Any]:
    path = _state_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(state: Dict[str, Any]) -> None:
    try:
        with open(_state_path(), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _append_jledger(row: Dict[str, Any]) -> None:
    try:
        with open(_ledger_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _round_for_credit(amount: float, currency: str) -> float:
    if currency == "mn2":
        return round(amount, 8)
    if currency == "usd":
        return round(amount, 2)
    return float(int(amount))  # coins floor to whole


def _ensure_rail(state: Dict[str, Any], currency: str, rail: Dict[str, float]) -> Dict[str, Any]:
    cur = state.get(currency)
    if not isinstance(cur, dict):
        seed = float(rail.get("seed") or 0)
        cur = {
            "pool": seed,
            "total_seeded": seed,
            "total_contributed": 0.0,
            "total_awarded": 0.0,
            "win_count": 0,
            "last_win": None,
        }
        state[currency] = cur
        _append_jledger({
            "type": "seed", "currency": currency, "amount": seed,
            "pool_after": cur["pool"], "reason": "initial", "at": _iso(),
        })
    return cur


def on_bet(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Process one settled bet: contribute to its rail's pool and maybe award it.

    Returns an award dict {currency, amount, reseed, pool} when the jackpot drops,
    otherwise None. Never raises (callers treat failures as "no jackpot").
    """
    if not isinstance(row, dict) or row.get("exclude_leaderboard"):
        return None
    try:
        bet = float(row.get("bet") or 0)
    except (TypeError, ValueError):
        return None
    if bet <= 0:
        return None

    currency = (row.get("currency") or "coins").lower()
    conf = _config()
    if not conf.get("enabled"):
        return None
    rail = conf["rails"].get(currency)
    if not rail or rail.get("contribution_rate", 0) <= 0:
        return None

    with _LOCK:
        state = _load_state()
        cur = _ensure_rail(state, currency, rail)

        contribution = bet * float(rail["contribution_rate"])
        cur["pool"] = float(cur["pool"]) + contribution
        cur["total_contributed"] = float(cur["total_contributed"]) + contribution
        _append_jledger({
            "type": "contribution", "currency": currency, "amount": contribution,
            "bet": bet, "game": row.get("game"), "user_id": row.get("user_id"),
            "pool_after": cur["pool"], "at": _iso(),
        })

        game = str(row.get("game") or "")
        details = row.get("details") if isinstance(row.get("details"), dict) else {}
        trigger = False
        reason = None
        if conf.get("slot_jackpot_symbol_awards") and game.startswith("slot_") and details.get("match") == "jackpot":
            trigger = True
            reason = "slot_symbol"
        elif random.random() < float(rail["win_chance"]):
            trigger = True
            reason = "must_drop"

        award = None
        if trigger and cur["pool"] > 0:
            amount = _round_for_credit(cur["pool"], currency)
            if amount > 0:
                try:
                    _cs()._apply_balance_delta(
                        row.get("user_id"), amount, currency, "jackpot",
                        {"phase": "jackpot_award", "reason": reason},
                    )
                except Exception:
                    return None  # do not record an award we failed to pay out
                cur["total_awarded"] = float(cur["total_awarded"]) + amount
                cur["pool"] = float(cur["pool"]) - amount
                cur["win_count"] = int(cur.get("win_count") or 0) + 1
                cur["last_win"] = {"user_id": row.get("user_id"), "amount": amount, "reason": reason, "at": _iso()}
                _append_jledger({
                    "type": "award", "currency": currency, "amount": amount,
                    "user_id": row.get("user_id"), "reason": reason,
                    "pool_after": cur["pool"], "at": _iso(),
                })
                reseed = float(rail["reseed"])
                cur["pool"] = float(cur["pool"]) + reseed
                cur["total_seeded"] = float(cur["total_seeded"]) + reseed
                _append_jledger({
                    "type": "seed", "currency": currency, "amount": reseed,
                    "pool_after": cur["pool"], "reason": "reseed", "at": _iso(),
                })
                award = {"currency": currency, "amount": amount, "reseed": reseed, "pool": cur["pool"]}

        _save_state(state)
        return award


def _available_rails() -> List[str]:
    """coins is always available; mn2/usd only when the real-money rail is on."""
    conf = _config()
    rails = list(conf["rails"].keys())
    try:
        pay = _cs()._payment_config()
    except Exception:
        pay = {"enabled": False, "rails": []}
    out = []
    for r in rails:
        if r == "coins":
            out.append(r)
        elif r == "mn2" and pay.get("enabled") and "mn2" in pay.get("rails", []):
            out.append(r)
        elif r == "usd" and pay.get("enabled") and "paypal" in pay.get("rails", []):
            out.append(r)
    return out


def seed_bonus(currency: str, amount: float, *, reason: str = "bonus") -> Dict[str, Any]:
    """Add house bonus to a jackpot pool (e.g. wheel raid boss)."""
    currency = (currency or "coins").lower()
    conf = _config()
    if not conf.get("enabled") or amount <= 0:
        return {"success": False, "error": "Jackpot disabled or invalid amount"}
    rail = conf["rails"].get(currency)
    if not rail:
        return {"success": False, "error": f"No jackpot rail for {currency}"}
    with _LOCK:
        state = _load_state()
        cur = _ensure_rail(state, currency, rail)
        cur["pool"] = float(cur["pool"]) + amount
        cur["total_seeded"] = float(cur["total_seeded"]) + amount
        _append_jledger({
            "type": "seed", "currency": currency, "amount": amount,
            "pool_after": cur["pool"], "reason": reason, "at": _iso(),
        })
        _save_state(state)
    return {"success": True, "currency": currency, "amount": amount, "pool": cur["pool"]}


def public_pools() -> Dict[str, Any]:
    """Current pool sizes per available rail, for the live jackpot meter."""
    conf = _config()
    if not conf.get("enabled"):
        return {"success": True, "enabled": False, "pools": {}}
    with _LOCK:
        state = _load_state()
        pools: Dict[str, Any] = {}
        for currency in _available_rails():
            rail = conf["rails"].get(currency)
            if not rail:
                continue
            cur = _ensure_rail(state, currency, rail)
            pools[currency] = {
                "pool": round(float(cur["pool"]), 8 if currency == "mn2" else 2),
                "win_count": int(cur.get("win_count") or 0),
                "last_win": cur.get("last_win"),
            }
        _save_state(state)
    return {"success": True, "enabled": True, "pools": pools}


def reconcile() -> Dict[str, Any]:
    """Verify pool == seeded + contributed - awarded for every rail."""
    with _LOCK:
        state = _load_state()
    report: Dict[str, Any] = {"success": True, "ok": True, "rails": {}}
    for currency, cur in state.items():
        if not isinstance(cur, dict):
            continue
        expected = float(cur.get("total_seeded") or 0) + float(cur.get("total_contributed") or 0) - float(cur.get("total_awarded") or 0)
        pool = float(cur.get("pool") or 0)
        tolerance = 1.0 if currency == "coins" else 1e-6  # coins floor on credit
        ok = abs(expected - pool) <= tolerance
        report["rails"][currency] = {
            "pool": pool,
            "expected": round(expected, 8),
            "diff": round(pool - expected, 8),
            "ok": ok,
        }
        if not ok:
            report["ok"] = False
    return report
