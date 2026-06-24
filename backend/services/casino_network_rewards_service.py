"""MN2 network rewards — bonuses tied to real-currency casino play and optional on-chain anchors."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_UBER_PATH = os.path.join(_BASE, "data", "casino_uber_games.json")
_STATE_PATH = os.path.join(_BASE, "logs", "casino_network_rewards", "users.json")
_LEDGER_PATH = os.path.join(_BASE, "logs", "casino_network_anchors.jsonl")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> str:
    return _utcnow().strftime("%Y-%m-%d")


def _bonus_cfg() -> Dict[str, Any]:
    if not os.path.isfile(_UBER_PATH):
        return {}
    try:
        with open(_UBER_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("network_bonus") if isinstance(data.get("network_bonus"), dict) else {}
    except Exception:
        return {}


def _load_state() -> Dict[str, Any]:
    if not os.path.isfile(_STATE_PATH):
        return {"users": {}}
    try:
        with open(_STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"users": {}}
    except Exception:
        return {"users": {}}


def _save_state(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    tmp = _STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _STATE_PATH)


def _user_row(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    data = _load_state()
    row = data.setdefault("users", {}).setdefault(uid, {})
    if row.get("bonus_date") != _today():
        row["bonus_date"] = _today()
        row["bonus_mn2_today"] = 0.0
    _save_state(data)
    return row


def apply_uber_win_bonus(
    user_id: str,
    *,
    currency: str,
    net: float,
    mult: float = 1.0,
) -> Dict[str, Any]:
    cfg = _bonus_cfg()
    cap = float(cfg.get("daily_cap_mn2") or 0.5)
    row = _user_row(user_id)
    used = float(row.get("bonus_mn2_today") or 0)
    if used >= cap:
        return {"success": True, "capped": True, "mn2_bonus": 0.0}
    mn2 = 0.0
    cur = (currency or "").lower()
    if cur == "usd" and net >= float(cfg.get("min_bet_usd") or 1):
        mn2 = float(cfg.get("mn2_per_usd_win") or 0.002) * net * mult
    elif cur == "mn2" and net >= float(cfg.get("min_bet_mn2") or 0.05):
        mn2 = net * float(cfg.get("mn2_per_mn2_win_pct") or 0.01) * mult
    mn2 = min(mn2, cap - used)
    if mn2 <= 0:
        return {"success": True, "mn2_bonus": 0.0}
    try:
        from backend.services.unified_points_database import unified_points_db
        unified_points_db.add_points(
            user_id, "mn2_balance", mn2,
            source="casino_network_bonus",
            metadata={"currency": cur, "net": net},
        )
    except Exception:
        return {"success": False, "mn2_bonus": 0.0}
    row["bonus_mn2_today"] = used + mn2
    row["lifetime_bonus_mn2"] = float(row.get("lifetime_bonus_mn2") or 0) + mn2
    data = _load_state()
    data.setdefault("users", {})[user_id] = row
    _save_state(data)
    _append_anchor(user_id, {"type": "win_bonus", "mn2": mn2, "currency": cur, "net": net})
    return {"success": True, "mn2_bonus": round(mn2, 8)}


def _append_anchor(user_id: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_LEDGER_PATH), exist_ok=True)
    row = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "at": _utcnow().isoformat(),
        **payload,
    }
    with open(_LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def get_network_status(user_id: str) -> Dict[str, Any]:
    cfg = _bonus_cfg()
    row = _user_row(user_id)
    anchors = 0
    if os.path.isfile(_LEDGER_PATH):
        try:
            with open(_LEDGER_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    if user_id in line:
                        anchors += 1
        except Exception:
            pass
    wallet_hint = None
    try:
        from backend.services.mn2_wallet_service import get_deposit_address
        wallet_hint = get_deposit_address(user_id)
    except Exception:
        pass
    return {
        "success": True,
        "user_id": user_id,
        "bonus_mn2_today": float(row.get("bonus_mn2_today") or 0),
        "daily_cap_mn2": float(cfg.get("daily_cap_mn2") or 0.5),
        "lifetime_bonus_mn2": float(row.get("lifetime_bonus_mn2") or 0),
        "anchor_events": min(anchors, 9999),
        "deposit_address": wallet_hint.get("address") if isinstance(wallet_hint, dict) else None,
        "config": cfg,
    }


def register_network_intent(user_id: str, *, bet_id: str, amount_mn2: float) -> Dict[str, Any]:
    """Optional paid anchor — records intent for future on-chain settlement pipeline."""
    fee = 0.01
    try:
        from backend.services.unified_points_database import unified_points_db
        pts = unified_points_db.get_all_points(user_id)
        bal = float((pts or {}).get("points", {}).get("mn2_balance") or 0)
        if bal < fee:
            return {"success": False, "error": "insufficient_mn2_for_anchor"}
        unified_points_db.add_points(
            user_id, "mn2_balance", -fee,
            source="casino_network_anchor_fee",
            metadata={"bet_id": bet_id},
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    anchor_id = str(uuid.uuid4())
    _append_anchor(user_id, {
        "type": "settlement_intent",
        "anchor_id": anchor_id,
        "bet_id": bet_id,
        "amount_mn2": amount_mn2,
        "fee_mn2": fee,
        "status": "pending_chain",
    })
    return {"success": True, "anchor_id": anchor_id, "fee_mn2": fee, "status": "pending_chain"}
