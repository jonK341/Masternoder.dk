"""M8 #52 — shop-wide Discord promo codes (coins / MN2 bonus on redeem)."""
from __future__ import annotations

import json
import os
import secrets
import threading
from datetime import datetime, timezone
from typing import Any, Dict

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROMOS_PATH = os.path.join(_BASE, "data", "discord_promo_codes.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load() -> Dict[str, Any]:
    if not os.path.isfile(_PROMOS_PATH):
        return {"codes": []}
    try:
        with open(_PROMOS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"codes": []}


def _save(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_PROMOS_PATH), exist_ok=True)
    with _LOCK:
        tmp = _PROMOS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, _PROMOS_PATH)


def _emit(event_type: str, *, user_id: str | None, payload: Dict[str, Any]) -> None:
    try:
        from backend.services.activity_events_service import emit
        emit(event_type, user_id=user_id, channel="game", text=payload.get("code") or event_type, payload=payload)
    except Exception:
        pass


def create_promo(
    *,
    reward_coins: int = 75,
    reward_mn2: float = 0,
    max_redemptions: int = 200,
    ttl_hours: int = 72,
) -> Dict[str, Any]:
    code = "SHOP-" + secrets.token_hex(3).upper()
    expires = datetime.now(timezone.utc).timestamp() + ttl_hours * 3600
    row = {
        "code": code,
        "scope": "shop",
        "reward_coins": int(reward_coins),
        "reward_mn2": float(reward_mn2 or 0),
        "max_redemptions": int(max_redemptions),
        "redeemed_by": [],
        "expires_at": datetime.fromtimestamp(expires, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "created_at": _iso(),
    }
    data = _load()
    codes = data.get("codes") if isinstance(data.get("codes"), list) else []
    codes.append(row)
    data["codes"] = codes[-200:]
    _save(data)
    label = f"{reward_coins} coins" if reward_mn2 <= 0 else f"{reward_mn2} MN2 + {reward_coins} coins"
    _emit("shop_discord_promo_created", user_id=None, payload={"code": code, "reward_label": label, "reward_coins": reward_coins})
    return {"success": True, "promo": row}


def redeem(user_id: str, code: str) -> Dict[str, Any]:
    from backend.services.mn2_earn_auth import require_earn_user

    ok, uid_or_err = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid_or_err}
    user_id = uid_or_err

    code = (code or "").strip().upper()
    if not code:
        return {"success": False, "error": "code required"}

    data = _load()
    codes = data.get("codes") if isinstance(data.get("codes"), list) else []
    target = None
    for row in codes:
        if (row.get("code") or "").upper() == code:
            target = row
            break
    if not target:
        return {"success": False, "error": "invalid_code"}

    try:
        exp = datetime.fromisoformat((target.get("expires_at") or "").replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > exp:
            return {"success": False, "error": "expired"}
    except Exception:
        pass

    redeemed = target.get("redeemed_by") if isinstance(target.get("redeemed_by"), list) else []
    if user_id in redeemed:
        return {"success": False, "error": "already_redeemed"}
    if len(redeemed) >= int(target.get("max_redemptions") or 0):
        return {"success": False, "error": "exhausted"}

    reward_coins = int(target.get("reward_coins") or 0)
    reward_mn2 = float(target.get("reward_mn2") or 0)
    ref = f"shop-promo-{code}-{user_id}"

    try:
        from backend.services.unified_points_database import unified_points_db
        if reward_coins > 0:
            unified_points_db.add_points(
                user_id, "coins", float(reward_coins), source="shop_discord_promo",
                metadata={"reference": ref, "code": code},
            )
        if reward_mn2 > 0:
            from backend.services.game_mn2_rewards import credit_mn2
            cr = credit_mn2(user_id, reward_mn2, source="shop_discord_promo", reference=ref, metadata={"code": code})
            if not cr.get("success") and not cr.get("duplicate"):
                return cr
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    redeemed.append(user_id)
    target["redeemed_by"] = redeemed
    _save(data)
    return {
        "success": True,
        "code": code,
        "reward_coins": reward_coins,
        "reward_mn2": reward_mn2,
    }
