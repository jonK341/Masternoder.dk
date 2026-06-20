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


def purchase_battle_pass_premium(user_id: str, *, source: str = "shop") -> Dict[str, Any]:
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
    price_paid = 0
    if src != "paypal":
        try:
            from backend.services.shop_monetization_service import (
                _accrue_loyalty_for_spend,
                _apply_vip_discount,
                _charge,
            )
        except Exception:
            return {"success": False, "error": "shop_billing_unavailable"}
        base_price = int(cfg.get("price_coins") or 0)
        if base_price <= 0:
            return {"success": False, "error": "battle_pass_not_for_sale_coins"}
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
