"""
Frontpage film-monitor access: free-to-use by default.

Optional paid credits (MN2 / PayPal) remain available if FILM_MONITOR_ALWAYS_FREE=0
and the free window expires — otherwise every play is free.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

_LOCK = threading.RLock()

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA_FILE = os.path.join(_BASE, "data", "film_monitor_billing.json")
_MN2_CFG = os.path.join(_BASE, "data", "mn2_config.json")

ITEM_ID = "film-monitor-play"
FREE_HOURS = 24
DEFAULT_PRICE_MN2 = 0.5
DEFAULT_PRICE_USD = 1.99
DEFAULT_COINS_PER_MN2 = 100.0


def is_always_free() -> bool:
    """Film monitors are a free program unless explicitly opted into paid mode."""
    env = (os.environ.get("FILM_MONITOR_ALWAYS_FREE") or "").strip().lower()
    if env in ("0", "false", "no", "off"):
        return False
    if env in ("1", "true", "yes", "on"):
        return True
    root = _read_json(_MN2_CFG)
    film = root.get("film_monitor") if isinstance(root.get("film_monitor"), dict) else {}
    if "always_free" in film:
        return bool(film.get("always_free"))
    return True


def _iso(dt: Optional[datetime] = None) -> str:
    value = dt or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: str) -> Optional[datetime]:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _read_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    os.replace(tmp, path)


def _load() -> dict:
    with _LOCK:
        data = _read_json(_DATA_FILE)
        data.setdefault("credits", {})
        data.setdefault("payments", {})
        return data


def _save(data: dict) -> None:
    with _LOCK:
        _write_json(_DATA_FILE, data)


def _pricing() -> Dict[str, Any]:
    root = _read_json(_MN2_CFG)
    film = root.get("film_monitor") if isinstance(root.get("film_monitor"), dict) else {}
    gen = root.get("generator") if isinstance(root.get("generator"), dict) else {}
    price_mn2 = float(
        film.get("price_mn2")
        or gen.get("express_pack_mn2")
        or DEFAULT_PRICE_MN2
    )
    price_usd = float(film.get("price_usd") or DEFAULT_PRICE_USD)
    coins_per_mn2 = float(root.get("coins_per_mn2") or DEFAULT_COINS_PER_MN2)
    free_hours = int(film.get("free_hours") or os.environ.get("FILM_MONITOR_FREE_HOURS") or FREE_HOURS)
    return {
        "price_mn2": round(price_mn2, 8),
        "price_usd": round(price_usd, 2),
        "coins_per_mn2": coins_per_mn2,
        "price_coins": int(round(price_mn2 * coins_per_mn2)),
        "free_hours": max(1, free_hours),
        "item_id": ITEM_ID,
    }


def resolve_identity(user_id: Optional[str] = None, trial_id: Optional[str] = None) -> str:
    uid = (user_id or "").strip()
    if uid and uid.lower() not in ("default_user", "anonymous", "guest"):
        return "user:%s" % uid
    tid = (trial_id or "").strip()
    if tid:
        return "trial:%s" % tid
    return "trial:guest"


def is_film_monitor_item(item_id: Optional[str]) -> bool:
    return str(item_id or "").strip().lower() in (ITEM_ID, "film_monitor_play", "film-monitor")


def _ensure_promo(store: dict, free_hours: int) -> Tuple[bool, int, str, str]:
    env_started = (os.environ.get("FILM_MONITOR_PROMO_STARTED_AT") or "").strip()
    started_raw = env_started or str(store.get("promo_started_at") or "").strip()
    started = _parse_iso(started_raw)
    if not started:
        started = datetime.now(timezone.utc)
        store["promo_started_at"] = _iso(started)
    ends = started + timedelta(hours=max(1, free_hours))
    now = datetime.now(timezone.utc)
    remaining = int((ends - now).total_seconds())
    free_active = remaining > 0
    return free_active, max(0, remaining), _iso(started), _iso(ends)


def _pay_options(pricing: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "mn2": {
            "label": "Pay with MN2 coins",
            "price_mn2": pricing["price_mn2"],
            "price_coins": pricing["price_coins"],
            "coins_per_mn2": pricing["coins_per_mn2"],
            "endpoint": "POST /api/film-canvas/billing/pay-mn2",
            "grants": "1 film play credit",
        },
        "paypal": {
            "label": "Pay with PayPal",
            "price_usd": pricing["price_usd"],
            "item_id": pricing["item_id"],
            "endpoint": "POST /api/film-canvas/billing/paypal-order",
            "grants": "1 film play credit",
        },
    }


def get_status(
    user_id: Optional[str] = None,
    trial_id: Optional[str] = None,
    *,
    start_trial: bool = True,
) -> Dict[str, Any]:
    pricing = _pricing()
    identity = resolve_identity(user_id, trial_id)
    store = _load()
    always_free = is_always_free()
    free_active, remaining, started_at, ends_at = _ensure_promo(store, pricing["free_hours"])
    if start_trial:
        _save(store)

    credits = int((store.get("credits") or {}).get(identity) or 0)
    if always_free:
        free_active = True
        remaining = max(remaining, 365 * 24 * 3600)
        ends_at = None
        can_play = True
        message = "Free to use — write a scene and press Play Movie."
    else:
        can_play = free_active or credits > 0
        if free_active:
            if remaining >= 3600:
                left = "%sh %sm" % (remaining // 3600, (remaining % 3600) // 60)
            elif remaining >= 60:
                left = "%sm" % (remaining // 60)
            else:
                left = "%ss" % remaining
            message = (
                "Free for the first %s hours — %s left. After that pay with MN2 coins or PayPal."
                % (pricing["free_hours"], left)
            )
        elif credits > 0:
            message = "Free window ended — %s prepaid play credit(s) left." % credits
        else:
            message = "Free window ended — pay with MN2 coins or PayPal to play."

    return {
        "success": True,
        "identity": identity,
        "always_free": always_free,
        "free_program": always_free,
        "free_active": free_active,
        "free_remaining_sec": remaining if not always_free else None,
        "free_ends_at": ends_at,
        "promo_started_at": started_at,
        "trial_started": True,
        "credits": credits,
        "can_play": can_play,
        "pricing": pricing,
        "pay_options": _pay_options(pricing) if not always_free else {},
        "message": message,
    }


def assert_can_play(
    user_id: Optional[str] = None,
    trial_id: Optional[str] = None,
    *,
    consume_credit: bool = True,
) -> Dict[str, Any]:
    status = get_status(user_id, trial_id, start_trial=True)
    if status.get("always_free") or status.get("free_program"):
        status["charged"] = False
        status["reason"] = "free_program"
        status["can_play"] = True
        status["success"] = True
        return status

    if status.get("free_active"):
        status["charged"] = False
        status["reason"] = "free_window"
        return status

    credits = int(status.get("credits") or 0)
    if credits > 0:
        if consume_credit:
            identity = status["identity"]
            store = _load()
            current = int((store.get("credits") or {}).get(identity) or 0)
            if current < 1:
                return {
                    "success": False,
                    "can_play": False,
                    "error": "PAYMENT_REQUIRED",
                    "code": "PAYMENT_REQUIRED",
                    "message": status.get("message"),
                    "identity": identity,
                    "free_active": False,
                    "free_remaining_sec": 0,
                    "free_ends_at": status.get("free_ends_at"),
                    "credits": 0,
                    "pricing": status.get("pricing"),
                    "pay_options": status.get("pay_options"),
                }
            store.setdefault("credits", {})[identity] = current - 1
            _save(store)
            status["credits"] = current - 1
            status["charged"] = True
            status["reason"] = "credit"
        return status

    return {
        "success": False,
        "can_play": False,
        "error": "PAYMENT_REQUIRED",
        "code": "PAYMENT_REQUIRED",
        "message": status.get("message") or "Pay with MN2 coins or PayPal to continue.",
        "identity": status.get("identity"),
        "free_active": False,
        "free_remaining_sec": 0,
        "free_ends_at": status.get("free_ends_at"),
        "promo_started_at": status.get("promo_started_at"),
        "credits": 0,
        "pricing": status.get("pricing"),
        "pay_options": status.get("pay_options"),
    }


def grant_credit(
    user_id: Optional[str] = None,
    trial_id: Optional[str] = None,
    *,
    credits: int = 1,
    source: str = "manual",
    reference: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    identity = resolve_identity(user_id, trial_id)
    amount = max(1, int(credits or 1))
    store = _load()
    _ensure_promo(store, _pricing()["free_hours"])
    current = int((store.get("credits") or {}).get(identity) or 0)
    store.setdefault("credits", {})[identity] = current + amount
    payment_id = reference or ("pay_" + uuid.uuid4().hex[:12])
    store.setdefault("payments", {})[payment_id] = {
        "identity": identity,
        "credits": amount,
        "source": source,
        "at": _iso(),
        "metadata": metadata or {},
    }
    _save(store)
    return {
        "success": True,
        "identity": identity,
        "credits_granted": amount,
        "credits": current + amount,
        "payment_id": payment_id,
        "source": source,
    }


def pay_with_mn2(
    user_id: str,
    trial_id: Optional[str] = None,
) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid or uid.lower() in ("default_user", "anonymous", "guest"):
        return {
            "success": False,
            "error": "Log in or create an account to pay with MN2 coins.",
            "code": "ACCOUNT_REQUIRED",
        }
    pricing = _pricing()
    amount = float(pricing["price_mn2"])
    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry

    points_result = unified_points_db.get_all_points(uid)
    pts = points_result.get("points", {}) or {}
    balance = float(pts.get("mn2_balance", 0) or 0)
    if balance == 0 and isinstance(pts.get("systems"), dict):
        balance = float(pts["systems"].get("mn2_balance", 0) or 0)
    if balance < amount:
        return {
            "success": False,
            "error": "Insufficient MN2. Need %.8f, have %.8f" % (amount, balance),
            "code": "INSUFFICIENT_MN2",
            "price_mn2": amount,
            "mn2_balance": balance,
            "pay_options": _pay_options(pricing),
        }

    meta = {
        "product": "film_monitor",
        "item_id": ITEM_ID,
        "trial_id": (trial_id or "").strip() or None,
    }
    result = unified_points_db.add_points(
        uid, "mn2_balance", -amount, source="film_monitor_mn2_pay", metadata=meta,
    )
    if not result.get("success", True):
        return {"success": False, "error": "Failed to debit MN2 balance", "code": "DEBIT_FAILED"}

    try:
        append_entry(user_id=uid, entry_type="film_monitor_payment", amount=amount, metadata=meta)
    except Exception:
        pass

    grant = grant_credit(
        user_id=uid,
        trial_id=trial_id,
        credits=1,
        source="mn2",
        metadata={"amount_mn2": amount, **meta},
    )
    new_bal = unified_points_db.get_all_points(uid).get("points", {}) or {}
    return {
        "success": True,
        "paid_with": "mn2",
        "amount_mn2": amount,
        "mn2_balance": float(new_bal.get("mn2_balance", 0) or 0),
        "credits": grant.get("credits"),
        "credits_granted": grant.get("credits_granted"),
        "message": "Paid with MN2 coins — 1 film play credit added.",
        "status": get_status(uid, trial_id, start_trial=True),
    }


def create_paypal_order(
    user_id: str,
    trial_id: Optional[str] = None,
    *,
    return_base: Optional[str] = None,
) -> Dict[str, Any]:
    import urllib.parse

    uid = (user_id or "").strip()
    if not uid or uid.lower() in ("default_user", "anonymous", "guest"):
        return {
            "success": False,
            "error": "Log in or create an account before paying with PayPal.",
            "code": "ACCOUNT_REQUIRED",
        }
    pricing = _pricing()
    price = float(pricing["price_usd"])
    base = (return_base or os.environ.get("BASE_URL") or "").rstrip("/")
    if not base:
        base = "http://127.0.0.1:5000"
    tid = urllib.parse.quote((trial_id or "").strip())
    return_url = (
        "%s/?film_paypal=success&user_id=%s&trial_id=%s"
        % (base, urllib.parse.quote(uid), tid)
    )
    cancel_url = "%s/?film_paypal=cancel" % base
    try:
        from backend.services.paypal_service import create_order, remember_shop_order

        result = create_order(
            amount=price,
            currency="USD",
            item_name="Film monitor play credit",
            return_url=return_url,
            cancel_url=cancel_url,
            metadata={
                "item_id": ITEM_ID,
                "user_id": uid,
                "trial_id": (trial_id or "").strip() or None,
                "product": "film_monitor",
            },
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)[:300]}

    if not result.get("success"):
        return result

    try:
        remember_shop_order(result.get("order_id"), {
            "status": "pending",
            "item_id": ITEM_ID,
            "item_name": "Film monitor play credit",
            "user_id": uid,
            "trial_id": (trial_id or "").strip() or None,
            "amount": price,
            "currency": "USD",
            "product": "film_monitor",
        })
    except Exception:
        pass

    return {
        "success": True,
        "paid_with": "paypal",
        "order_id": result.get("order_id"),
        "approve_url": result.get("approve_url"),
        "price_usd": price,
        "item_id": ITEM_ID,
        "message": "Continue to PayPal to unlock 1 film play credit.",
    }


def fulfill_paypal_purchase(
    user_id: str,
    order_id: str,
    *,
    trial_id: Optional[str] = None,
    amount: Optional[float] = None,
) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid:
        return {"success": False, "error": "missing_user_id"}
    ref = "paypal_film_monitor:%s" % (order_id or uuid.uuid4().hex)
    store = _load()
    if ref in (store.get("payments") or {}):
        existing = store["payments"][ref]
        identity = existing.get("identity") or resolve_identity(uid, trial_id)
        return {
            "success": True,
            "already_fulfilled": True,
            "credits": int((store.get("credits") or {}).get(identity) or 0),
            "payment_id": ref,
        }
    grant = grant_credit(
        user_id=uid,
        trial_id=trial_id,
        credits=1,
        source="paypal",
        reference=ref,
        metadata={"order_id": order_id, "amount_usd": amount},
    )
    return {
        "success": True,
        "item_granted": ITEM_ID,
        "credits_granted": grant.get("credits_granted"),
        "credits": grant.get("credits"),
        "payment_id": grant.get("payment_id"),
        "message": "PayPal payment unlocked 1 film play credit.",
    }
