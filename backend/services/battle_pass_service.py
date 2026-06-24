"""
Season / Battle Pass — progression + premium lane (#7).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STATE = os.path.join(_BASE, "logs", "shop_monetization", "battle_pass.json")
BATTLE_PASS_PAYPAL_ITEM_ID = "battle-pass-premium"


def is_battle_pass_paypal_item(item_id: str) -> bool:
    return (item_id or "").strip() == BATTLE_PASS_PAYPAL_ITEM_ID


def _config() -> Dict[str, Any]:
    try:
        from backend.services.monetization_config_service import get_shop_monetization

        sm = get_shop_monetization()
        bp = sm.get("battle_pass")
        return dict(bp) if isinstance(bp, dict) else {}
    except Exception:
        return {}


def _load_state() -> Dict[str, Any]:
    if not os.path.isfile(_STATE):
        return {"users": {}}
    try:
        with open(_STATE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"users": {}}
    except Exception:
        return {"users": {}}


def _save_state(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_STATE), exist_ok=True)
    tmp = _STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _STATE)


def get_battle_pass_status(user_id: str) -> Dict[str, Any]:
    cfg = _config()
    if not cfg:
        return {"success": False, "error": "battle_pass_not_configured"}
    uid = (user_id or "").strip()
    data = _load_state()
    users = data.get("users") if isinstance(data.get("users"), dict) else {}
    row = users.get(uid) if uid else {}
    if not isinstance(row, dict):
        row = {}
    return {
        "success": True,
        "season_id": cfg.get("season_id"),
        "name": cfg.get("name"),
        "price_usd": cfg.get("price_usd"),
        "price_coins": cfg.get("price_coins"),
        "premium_owned": bool(row.get("premium_owned")),
        "tier_level": int(row.get("tier_level") or 0),
        "xp": int(row.get("xp") or 0),
        "rewards": cfg.get("rewards") or [],
    }


def fulfill_battle_pass_paypal_purchase(user_id: str) -> Dict[str, Any]:
    """Grant premium after verified PayPal capture — not callable from public coin purchase API."""
    return _grant_battle_pass_premium(user_id, source="paypal", price_paid=0)


def purchase_battle_pass_premium(user_id: str, *, source: str = "shop") -> Dict[str, Any]:
    """Coin (or shop) purchase — PayPal must go through PayPal capture fulfillment."""
    src = (source or "shop").strip().lower()
    if src == "paypal":
        return {
            "success": False,
            "error": "PayPal battle pass must be purchased through checkout",
            "code": "PAYPAL_CHECKOUT_REQUIRED",
        }
    cfg = _config()
    if not cfg:
        return {"success": False, "error": "battle_pass_not_configured"}
    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return {"success": False, "error": "account_required"}

    data = _load_state()
    users = data.get("users") if isinstance(data.get("users"), dict) else {}
    row = users.get(uid) if uid else {}
    if isinstance(row, dict) and row.get("premium_owned"):
        return {"success": True, "already_owned": True}

    base_price = int(cfg.get("price_coins") or 0)
    if base_price <= 0:
        return {"success": False, "error": "battle_pass_not_for_sale_coins"}
    price_paid = 0
    try:
        from backend.services.shop_monetization_service import (
            _accrue_loyalty_for_spend,
            _apply_vip_discount,
            _charge,
        )
    except Exception:
        return {"success": False, "error": "shop_billing_unavailable"}
    price_paid = _apply_vip_discount(uid, base_price)
    ok, err = _charge(
        uid,
        price_paid,
        payment_method="coins",
        source="battle_pass",
        metadata={"season": cfg.get("season_id"), "purchase_source": src},
    )
    if not ok:
        return {"success": False, "error": err or "insufficient_coins"}
    try:
        _accrue_loyalty_for_spend(uid, price_paid)
    except Exception:
        pass
    return _grant_battle_pass_premium(uid, source=src, price_paid=price_paid)


def _grant_battle_pass_premium(user_id: str, *, source: str, price_paid: int = 0) -> Dict[str, Any]:
    cfg = _config()
    if not cfg:
        return {"success": False, "error": "battle_pass_not_configured"}
    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return {"success": False, "error": "account_required"}
    data = _load_state()
    users = data.setdefault("users", {})
    row = users.setdefault(uid, {})
    if row.get("premium_owned"):
        return {"success": True, "already_owned": True}

    src = (source or "shop").strip().lower()
    row["premium_owned"] = True
    row["purchased_at"] = datetime.now(timezone.utc).isoformat()
    row["source"] = src
    if price_paid > 0:
        row["price_paid_coins"] = price_paid
    _save_state(data)

    bonus = cfg.get("premium_instant_grant") or {}
    granted_coins = 0
    granted_credits = 0.0
    try:
        from backend.services.shop_monetization_service import _points_db

        db = _points_db()
        coins = int(bonus.get("coins") or 0)
        if coins > 0 and db:
            db.add_points(
                uid,
                "coins",
                float(coins),
                source="battle_pass",
                metadata={"season": cfg.get("season_id"), "grant": "premium_instant"},
            )
            granted_coins = coins
        try:
            granted_credits = float(bonus.get("generation_credits") or 0)
        except (TypeError, ValueError):
            granted_credits = 0.0
        if granted_credits > 0 and db:
            db.add_points(
                uid,
                "generation_credits",
                granted_credits,
                source="battle_pass",
                metadata={"season": cfg.get("season_id"), "grant": "premium_instant"},
            )
    except Exception:
        pass
    return {
        "success": True,
        "premium_owned": True,
        "season_id": cfg.get("season_id"),
        "price_paid_coins": price_paid or None,
        "granted_coins": granted_coins or None,
        "granted_generation_credits": granted_credits or None,
    }


def record_battle_pass_action(user_id: str, action: str) -> Optional[Dict[str, Any]]:
    """Award quest XP once per matching quest for the current season."""
    cfg = _config()
    if not cfg:
        return None
    uid = (user_id or "").strip()
    action_key = (action or "").strip()
    if not uid or uid == "default_user" or not action_key:
        return None

    quests = cfg.get("quests") or []
    if not isinstance(quests, list):
        return None
    matching = [
        q for q in quests
        if isinstance(q, dict) and (q.get("action") or "").strip() == action_key
    ]
    if not matching:
        return None

    season_id = str(cfg.get("season_id") or "")
    try:
        xp_per_tier = max(1, int(cfg.get("xp_per_tier") or 100))
    except (TypeError, ValueError):
        xp_per_tier = 100

    data = _load_state()
    users = data.setdefault("users", {})
    row = users.setdefault(uid, {})
    completed = row.get("quests_completed")
    if not isinstance(completed, dict):
        completed = {}
        row["quests_completed"] = completed

    xp_gained = 0
    for quest in matching:
        qid = (quest.get("id") or "").strip()
        if not qid:
            continue
        comp_key = f"{season_id}:{qid}" if season_id else qid
        if completed.get(comp_key):
            continue
        try:
            xp = int(quest.get("xp") or 0)
        except (TypeError, ValueError):
            xp = 0
        if xp <= 0:
            continue
        completed[comp_key] = datetime.now(timezone.utc).isoformat()
        xp_gained += xp

    if xp_gained <= 0:
        return None

    new_xp = int(row.get("xp") or 0) + xp_gained
    row["xp"] = new_xp
    row["tier_level"] = new_xp // xp_per_tier
    _save_state(data)
    return {
        "success": True,
        "action": action_key,
        "xp_gained": xp_gained,
        "xp": new_xp,
        "tier_level": row["tier_level"],
    }
