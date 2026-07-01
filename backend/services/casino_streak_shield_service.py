"""Weekly streak shield — one loss-forgiving token (Wave 3)."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.services import casino_service as cs


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _week_key() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"


def _config() -> Dict[str, Any]:
    cfg = cs._load_config()
    block = cfg.get("streak_shield") if isinstance(cfg.get("streak_shield"), dict) else {}
    return {
        "enabled": bool(block.get("enabled", True)),
        "shields_per_week": int(block.get("shields_per_week") or 1),
        "refund_pct": float(block.get("refund_pct") or 50),
        "currency": str(block.get("currency") or "coins"),
    }


def _path() -> str:
    log_dir = cs._log_dir()
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "casino_streak_shields.json")


def _load() -> Dict[str, Any]:
    path = _path()
    if not os.path.isfile(path):
        return {}
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(data: Dict[str, Any]) -> None:
    import json
    path = _path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def status(user_id: str) -> Dict[str, Any]:
    conf = _config()
    user_id = (user_id or "").strip()
    wk = _week_key()
    data = _load()
    row = data.get(user_id) if isinstance(data.get(user_id), dict) else {}
    used = int(row.get(wk, 0) or 0)
    remaining = max(0, conf["shields_per_week"] - used)
    return {
        "success": True,
        "enabled": conf["enabled"],
        "week_key": wk,
        "shields_remaining": remaining,
        "refund_pct": conf["refund_pct"],
        "currency": conf["currency"],
    }


def apply_shield(user_id: str, *, bet: float, currency: Optional[str] = None) -> Dict[str, Any]:
    conf = _config()
    if not conf["enabled"]:
        return {"success": False, "error": "streak_shield_disabled"}
    user_id = (user_id or "").strip()
    st = status(user_id)
    if st.get("shields_remaining", 0) <= 0:
        return {**st, "success": False, "error": "no_shields_left"}
    cur = cs._normalize_currency(currency or conf["currency"])
    if cur != cs._normalize_currency(conf["currency"]):
        return {"success": False, "error": "shield_coins_only"}
    amount = cs._parse_bet_amount(bet, cur) or 0
    if amount <= 0:
        return {"success": False, "error": "invalid_bet"}
    refund = cs._round_payout(amount * conf["refund_pct"] / 100.0, cur)
    if refund > 0:
        cs._apply_balance_delta(user_id, refund, cur, "streak_shield", {"bet": amount, "week": _week_key()})
    data = _load()
    row = data.setdefault(user_id, {})
    wk = _week_key()
    row[wk] = int(row.get(wk, 0) or 0) + 1
    _save(data)
    return {
        "success": True,
        "refund": refund,
        "currency": cur,
        "balance": cs._user_balance(user_id, cur),
        **status(user_id),
    }
