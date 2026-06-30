"""
Casino PayPal deposit packs — starter bundles, bonuses, availability filters.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set


def _config() -> Dict[str, Any]:
    try:
        from backend.services.casino_service import _load_config, _payment_config

        cfg = _load_config()
        block = cfg.get("deposit_packs") if isinstance(cfg.get("deposit_packs"), dict) else {}
        pay = _payment_config()
        return {
            "enabled": bool(block.get("enabled", True)),
            "packs": block.get("packs") if isinstance(block.get("packs"), list) else [],
            "paypal_packs": pay.get("paypal_deposit_packs") or [],
            "currency": pay.get("paypal_currency") or "USD",
        }
    except Exception:
        return {"enabled": True, "packs": [], "paypal_packs": [], "currency": "USD"}


def _pack_index() -> Dict[str, Dict[str, Any]]:
    cfg = _config()
    merged: Dict[str, Dict[str, Any]] = {}
    for row in cfg.get("paypal_packs") or []:
        if isinstance(row, dict) and row.get("id"):
            merged[str(row["id"])] = dict(row)
    for row in cfg.get("packs") or []:
        if isinstance(row, dict) and row.get("id"):
            pid = str(row["id"])
            base = merged.get(pid, {})
            merged[pid] = {**base, **row}
    return merged


def _user_purchased_pack_ids(user_id: str) -> Set[str]:
    try:
        from backend.services.casino_service import _load_paypal_deposits

        data = _load_paypal_deposits()
        ids: Set[str] = set()
        for row in (data.get("captured") or {}).values():
            if isinstance(row, dict) and row.get("user_id") == user_id and row.get("pack_id"):
                ids.add(str(row["pack_id"]))
        extra = (data.get("pack_purchases") or {}).get(user_id) or []
        if isinstance(extra, list):
            ids.update(str(x) for x in extra)
        return ids
    except Exception:
        return set()


def _pack_available(user_id: str, pack: Dict[str, Any], purchased: Set[str]) -> bool:
    pid = str(pack.get("id") or "")
    if pack.get("starter_only") and pid in purchased:
        return False
    max_per = pack.get("max_per_user")
    if max_per is not None:
        count = sum(1 for p in purchased if p == pid)
        if count >= int(max_per):
            return False
    expires = pack.get("expires") or pack.get("expires_at")
    if expires:
        try:
            exp = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp:
                return False
        except Exception:
            pass
    return True


def _normalize_pack(row: Dict[str, Any], user_id: str, purchased: Set[str]) -> Dict[str, Any]:
    amount = float(row.get("amount_usd") or 0)
    bonus_usd = float(row.get("bonus_usd") or 0)
    bonus_coins = int(row.get("bonus_coins") or 0)
    available = _pack_available(user_id, row, purchased)
    return {
        "id": str(row["id"]),
        "label": row.get("label") or row["id"],
        "amount_usd": amount,
        "bonus_usd": bonus_usd,
        "bonus_coins": bonus_coins,
        "total_usd": round(amount + bonus_usd, 2),
        "badge": row.get("badge"),
        "starter_only": bool(row.get("starter_only")),
        "available": available,
        "unavailable_reason": None if available else (
            "Starter pack already claimed" if row.get("starter_only") else "Pack limit reached"
        ),
    }


def list_deposit_packs(user_id: str = "") -> Dict[str, Any]:
    cfg = _config()
    purchased = _user_purchased_pack_ids(user_id) if user_id else set()
    packs: List[Dict[str, Any]] = []
    for row in _pack_index().values():
        packs.append(_normalize_pack(row, user_id, purchased))
    packs.sort(key=lambda p: (not p.get("starter_only"), p.get("amount_usd") or 0))
    try:
        from backend.services.casino_service import _paypal_enabled

        enabled = _paypal_enabled() and cfg.get("enabled", True)
    except Exception:
        enabled = False
    return {
        "success": True,
        "enabled": enabled,
        "currency": cfg.get("currency") or "USD",
        "packs": packs,
        "starter_packs": [p for p in packs if p.get("starter_only")],
    }


def resolve_pack(pack_id: str) -> Optional[Dict[str, Any]]:
    return _pack_index().get((pack_id or "").strip())


def record_pack_purchase(user_id: str, pack_id: str) -> None:
    try:
        from backend.services.casino_service import _load_paypal_deposits, _save_paypal_deposits

        data = _load_paypal_deposits()
        bucket = data.setdefault("pack_purchases", {})
        rows = list(bucket.get(user_id) or [])
        rows.append(str(pack_id))
        bucket[user_id] = rows
        _save_paypal_deposits(data)
    except Exception:
        pass


def apply_pack_bonuses(user_id: str, pack: Dict[str, Any]) -> Dict[str, Any]:
    """Credit bonus USD/coins after base deposit capture."""
    bonus_usd = float(pack.get("bonus_usd") or 0)
    bonus_coins = int(pack.get("bonus_coins") or 0)
    out: Dict[str, Any] = {"bonus_usd": 0.0, "bonus_coins": 0}
    if bonus_usd > 0:
        try:
            from backend.services.casino_service import _apply_balance_delta

            _apply_balance_delta(
                user_id,
                bonus_usd,
                "usd",
                "paypal_deposit_bonus",
                {"pack_id": pack.get("id"), "phase": "bonus"},
            )
            out["bonus_usd"] = bonus_usd
        except Exception:
            pass
    if bonus_coins > 0:
        try:
            from backend.services.casino_service import _apply_coin_delta

            _apply_coin_delta(
                user_id,
                bonus_coins,
                "paypal_deposit_bonus",
                {"pack_id": pack.get("id")},
            )
            out["bonus_coins"] = bonus_coins
        except Exception:
            pass
    return out
