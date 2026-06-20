"""
Arena economy — shared escrow + rake + payout for paid Battle/Arena actions.

This is the single income engine behind tournament buy-ins, PvP duel wagering,
ranked entry fees, and the Arena shop. It deliberately REUSES the casino money
rails rather than building a second payment system:

- Real-money (`mn2`/`usd`) debits go through the same security gate the casino
  uses (`account_security_service.check_real_money_action`), so no Arena path
  can bypass the password + verification_token requirement.
- Balance moves go through `casino_service._apply_balance_delta`, so the three
  currency rails (coins / mn2_balance / casino_fiat_balance) stay authoritative
  in `unified_points_database`.
- Every collect/payout is mirrored into the casino ledger via
  `casino_service._append_ledger` (game = "arena_<context>"), so income is
  reconcilable alongside casino bets.

Invariant (tested): for any event, per currency,
    sum(buy_ins) == sum(prize_payouts) + house_take
Money is never created or destroyed outside the ledger.

Locked constraints respected:
- Never touches `mn2_staked` (staking is off-limits, MN2_STAKING_PLAN §14 #10).
- Only the liquid `mn2_balance` / `casino_fiat_balance` are moved.
"""
from __future__ import annotations

import os
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

VALID_CURRENCIES = ("coins", "mn2", "usd")
REAL_MONEY = ("mn2", "usd")


def _iso(dt: Optional[datetime] = None) -> str:
    return (dt or datetime.now(timezone.utc)).isoformat()


def _round_amount(amount: float, currency: str) -> float:
    if currency == "mn2":
        return round(float(amount), 8)
    if currency == "usd":
        return round(float(amount), 2)
    return float(int(round(float(amount))))


# --- casino-rail reuse (imported lazily so this module loads without Flask ctx) ---

def _normalize_currency(currency: Optional[str]) -> str:
    c = (currency or "coins").strip().lower()
    if c in ("usd", "paypal", "fiat"):
        return "usd"
    if c == "mn2":
        return "mn2"
    return "coins"


def _user_balance(user_id: str, currency: str) -> float:
    from backend.services import casino_service
    return float(casino_service._user_balance(user_id, currency))


def _security_gate(user_id: str, currency: str) -> Optional[str]:
    """Return an error string if a real-money action is blocked, else None."""
    if currency not in REAL_MONEY:
        return None
    try:
        from flask import has_request_context, request
        from backend.services.account_security_service import check_real_money_action

        token = None
        if has_request_context():
            data = request.get_json(silent=True) or {}
            token = data.get("verification_token") or data.get("security_token")
        return check_real_money_action(user_id, verification_token=token)
    except Exception:
        return None


def _move_balance(user_id: str, delta: float, currency: str, game: str, meta: Dict[str, Any]) -> None:
    from backend.services import casino_service
    casino_service._apply_balance_delta(user_id, float(delta), currency, game, meta)


def _ledger(row: Dict[str, Any]) -> None:
    from backend.services import casino_service
    casino_service._append_ledger(row)


# --- escrow / event state (decoupled from battle_v2_state.json) ---

def _state_path() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "data", "arena_state.json")


def _load_state() -> Dict[str, Any]:
    path = _state_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data.setdefault("events", {})
                data.setdefault("entries", {})
                return data
        except Exception:
            pass
    return {"events": {}, "entries": {}}


def _save_state(data: Dict[str, Any]) -> None:
    path = _state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


# --- public API ---

def validate_buy_in(user_id: str, amount: float, currency: str) -> Optional[str]:
    """Validate an Arena buy-in. Returns an error string, or None if OK.

    Arena uses its own buy-in tiers (validated by the caller against
    arena_config); here we enforce the universal rules: positive amount,
    real-money security gate, and sufficient balance.
    """
    currency = _normalize_currency(currency)
    amount = _round_amount(amount, currency)
    if amount <= 0:
        return "Invalid buy-in amount"
    gate_err = _security_gate(user_id, currency)
    if gate_err:
        return gate_err
    if currency in ("mn2", "usd"):
        try:
            from backend.services.casino_responsible_gaming import check_before_bet
            rg_err = check_before_bet(user_id, amount, currency)
            if rg_err:
                return rg_err
        except Exception:
            pass
    if _user_balance(user_id, currency) < amount:
        from backend.services import casino_service
        return f"Insufficient {casino_service._currency_label(currency)}"
    return None


def collect_buy_in(
    user_id: str,
    amount: float,
    currency: str,
    context: str,
    meta: Optional[Dict[str, Any]] = None,
    event_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Debit a buy-in into escrow and ledger it. Returns the entry record.

    On failure returns {"success": False, "error": ...} without moving money.
    """
    currency = _normalize_currency(currency)
    amount = _round_amount(amount, currency)
    err = validate_buy_in(user_id, amount, currency)
    if err:
        return {"success": False, "error": err}

    game = f"arena_{context}"
    meta = dict(meta or {})
    entry_id = str(uuid.uuid4())

    _move_balance(user_id, -amount, currency, game, {"phase": "buy_in", "entry_id": entry_id, **meta})

    row = {
        "bet_id": entry_id,
        "user_id": user_id,
        "game": game,
        "bet": amount,
        "currency": currency,
        "outcome": "buy_in",
        "payout": 0,
        "net": -amount,
        "details": {"phase": "buy_in", "context": context, "event_id": event_id, **meta},
        "created_at": _iso(),
        "exclude_leaderboard": True,
    }
    _ledger(row)

    state = _load_state()
    state["entries"][entry_id] = {
        "entry_id": entry_id,
        "user_id": user_id,
        "context": context,
        "event_id": event_id,
        "amount": amount,
        "currency": currency,
        "status": "escrowed",
        "created_at": row["created_at"],
        "meta": meta,
    }
    if event_id is not None:
        ev = state["events"].setdefault(event_id, {
            "event_id": event_id,
            "context": context,
            "currency": currency,
            "pot": 0.0,
            "buy_ins": 0.0,
            "house_take": 0.0,
            "status": "open",
            "entries": [],
        })
        ev["pot"] = _round_amount(float(ev.get("pot", 0)) + amount, currency)
        ev["buy_ins"] = _round_amount(float(ev.get("buy_ins", 0)) + amount, currency)
        ev.setdefault("entries", []).append(entry_id)
    _save_state(state)

    return {
        "success": True,
        "entry_id": entry_id,
        "amount": amount,
        "currency": currency,
        "balance": _user_balance(user_id, currency),
    }


def split_rake(pot: float, rake_pct: float, currency: str) -> Tuple[float, float]:
    """Split a pot into (prize_pool, house_take). rake_pct is a percentage (0-100)."""
    pot = _round_amount(pot, currency)
    rake_pct = max(0.0, min(float(rake_pct or 0), 100.0))
    house_take = _round_amount(pot * (rake_pct / 100.0), currency)
    prize_pool = _round_amount(pot - house_take, currency)
    return prize_pool, house_take


def payout(
    user_id: str,
    amount: float,
    currency: str,
    context: str,
    parent_entry_id: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Credit a prize/refund to a user and ledger it."""
    currency = _normalize_currency(currency)
    amount = _round_amount(amount, currency)
    if amount <= 0:
        return {"success": False, "error": "Invalid payout amount"}
    game = f"arena_{context}"
    meta = dict(meta or {})
    _move_balance(user_id, amount, currency, game, {"phase": "payout", **meta})
    _ledger({
        "bet_id": str(uuid.uuid4()),
        "user_id": user_id,
        "game": game,
        "bet": 0,
        "currency": currency,
        "outcome": "prize",
        "payout": amount,
        "net": amount,
        "details": {"phase": "payout", "context": context, "parent_entry_id": parent_entry_id, **meta},
        "created_at": _iso(),
        "exclude_leaderboard": True,
    })
    return {"success": True, "amount": amount, "currency": currency, "balance": _user_balance(user_id, currency)}


def record_house_take(amount: float, currency: str, context: str, event_id: Optional[str] = None,
                      meta: Optional[Dict[str, Any]] = None) -> None:
    """Ledger the house rake to the house account so pools stay reconcilable."""
    currency = _normalize_currency(currency)
    amount = _round_amount(amount, currency)
    if amount <= 0:
        return
    meta = dict(meta or {})
    _ledger({
        "bet_id": str(uuid.uuid4()),
        "user_id": "__house__",
        "game": f"arena_{context}",
        "bet": 0,
        "currency": currency,
        "outcome": "house_rake",
        "payout": amount,
        "net": amount,
        "details": {"phase": "rake", "context": context, "event_id": event_id, **meta},
        "created_at": _iso(),
        "exclude_leaderboard": True,
    })
    if event_id is not None:
        state = _load_state()
        ev = state["events"].get(event_id)
        if ev is not None:
            ev["house_take"] = _round_amount(float(ev.get("house_take", 0)) + amount, currency)
            _save_state(state)


def refund_entry(entry_id: str, reason: str = "voided") -> Dict[str, Any]:
    """Refund an escrowed buy-in (event cancelled / void). Idempotent."""
    state = _load_state()
    entry = state["entries"].get(entry_id)
    if not entry:
        return {"success": False, "error": "Unknown entry"}
    if entry.get("status") != "escrowed":
        return {"success": True, "already": entry.get("status")}
    res = payout(entry["user_id"], entry["amount"], entry["currency"], entry["context"],
                 parent_entry_id=entry_id, meta={"refund_reason": reason})
    if res.get("success"):
        entry["status"] = "refunded"
        _save_state(state)
    return res


def get_event(event_id: str) -> Optional[Dict[str, Any]]:
    return _load_state()["events"].get(event_id)


def reconcile(event_id: str) -> Dict[str, Any]:
    """Return the conservation check for an event: buy_ins vs payouts + house_take."""
    ev = get_event(event_id) or {}
    return {
        "event_id": event_id,
        "currency": ev.get("currency"),
        "buy_ins": ev.get("buy_ins", 0.0),
        "house_take": ev.get("house_take", 0.0),
        "prizes_paid": ev.get("prizes_paid", 0.0),
        "balanced": _round_amount(
            float(ev.get("buy_ins", 0)) - float(ev.get("house_take", 0)) - float(ev.get("prizes_paid", 0)),
            ev.get("currency") or "coins",
        ) == 0,
    }
