"""
Generator MN2 pay / earn — debit express tiers, refund on failure, finish bonus.

Charges are recorded in data/generator_mn2_charges.json keyed by doc_id.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_LOCK = threading.RLock()

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CHARGES_FILE = os.path.join(_BASE, "data", "generator_mn2_charges.json")
_MN2_CFG = os.path.join(_BASE, "data", "mn2_config.json")

_DEFAULTS = {
    "enabled": True,
    "earn_on_finish_mn2": 0.005,
    "express_pack_mn2": 0.5,
    "premium_encode_mn2": 0.1,
    "ultra_encode_mn2": 0.25,
    "duration_surcharge_per_min_mn2": 0.002,
    "max_earn_per_video_mn2": 0.05,
}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _load_charges() -> dict:
    with _LOCK:
        return _read_json(_CHARGES_FILE)


def _save_charges(data: dict) -> None:
    with _LOCK:
        _write_json(_CHARGES_FILE, data)


def get_generator_config() -> Dict[str, Any]:
    cfg = dict(_DEFAULTS)
    root = _read_json(_MN2_CFG)
    gen = root.get("generator") if isinstance(root.get("generator"), dict) else {}
    cfg.update(gen)
    cfg["coins_per_mn2"] = float(root.get("coins_per_mn2") or 100)
    return cfg


def _tier_from_config(config: Dict[str, Any], body: Optional[Dict[str, Any]] = None) -> str:
    body = body or {}
    if body.get("pay_with_mn2") or config.get("pay_with_mn2"):
        tier = (body.get("mn2_tier") or config.get("mn2_tier") or "express").strip().lower()
        return tier if tier in ("express", "premium", "ultra") else "express"
    qm = (config.get("quality_mode") or body.get("quality_mode") or "").strip().lower()
    ep = (config.get("encode_profile") or body.get("encode_profile") or "").strip().lower()
    if qm in ("ultra",) or ep in ("ultra",):
        return "ultra"
    if qm in ("premium",) or ep in ("premium", "high"):
        return "premium"
    return "standard"


def quote_generation(
    duration: int = 180,
    short_clip: bool = False,
    tier: str = "standard",
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return MN2 price quote for a generation job."""
    cfg = get_generator_config()
    tier = (tier or "standard").strip().lower()
    duration = max(10, min(300, int(duration or 60)))
    if short_clip:
        duration = min(duration, 90)

    base = 0.0
    if tier == "express":
        base = float(cfg.get("express_pack_mn2") or 0.5)
    elif tier == "premium":
        base = float(cfg.get("premium_encode_mn2") or 0.1)
    elif tier == "ultra":
        base = float(cfg.get("ultra_encode_mn2") or 0.25)

    minutes = duration / 60.0
    surcharge = minutes * float(cfg.get("duration_surcharge_per_min_mn2") or 0.002)
    price_mn2 = round(base + (surcharge if tier != "standard" else 0.0), 8)
    earn = float(cfg.get("earn_on_finish_mn2") or 0.005) if cfg.get("enabled", True) else 0.0

    return {
        "success": True,
        "tier": tier,
        "price_mn2": price_mn2,
        "earn_on_finish_mn2": earn,
        "duration_sec": duration,
        "short_clip": bool(short_clip),
        "coins_per_mn2": cfg.get("coins_per_mn2"),
        "charged": tier != "standard" and price_mn2 > 0,
    }


def get_public_pricing() -> Dict[str, Any]:
    cfg = get_generator_config()
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "currency": "MN2",
        "coins_per_mn2": cfg.get("coins_per_mn2"),
        "earn_on_finish_mn2": cfg.get("earn_on_finish_mn2"),
        "tiers": {
            "standard": quote_generation(tier="standard"),
            "express": quote_generation(tier="express", duration=180),
            "premium": quote_generation(tier="premium", duration=180),
            "ultra": quote_generation(tier="ultra", duration=180),
        },
        "express_pack_mn2": cfg.get("express_pack_mn2"),
    }


def _debit(user_id: str, amount: float, meta: dict) -> Dict[str, Any]:
    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry

    points_result = unified_points_db.get_all_points(user_id)
    if not points_result.get("success", True):
        return {"success": False, "error": "Failed to load balance"}
    pts = points_result.get("points", {}) or {}
    balance = float(pts.get("mn2_balance", 0) or 0)
    if balance == 0 and isinstance(pts.get("systems"), dict):
        balance = float(pts["systems"].get("mn2_balance", 0) or 0)
    if balance < amount:
        return {
            "success": False,
            "error": f"Insufficient MN2. Need {amount:.8f}, have {balance:.8f}",
            "price_mn2": amount,
            "mn2_balance": balance,
            "required": True,
        }
    result = unified_points_db.add_points(
        user_id, "mn2_balance", -amount, source="generator_mn2_pay", metadata=meta,
    )
    if not result.get("success", True):
        return {"success": False, "error": "Failed to debit MN2 balance", "required": True}
    try:
        append_entry(user_id=user_id, entry_type="generator_payment", amount=amount, metadata=meta)
    except Exception:
        pass
    try:
        from backend.services.activity_events_service import emit
        emit("generator_mn2_pay", channel="generator", user_id=user_id, payload={"amount": amount, **meta})
    except Exception:
        pass
    new_bal = unified_points_db.get_all_points(user_id).get("points", {}) or {}
    return {
        "success": True,
        "amount": amount,
        "mn2_balance": float(new_bal.get("mn2_balance", 0) or 0),
    }


def _credit(user_id: str, amount: float, source: str, meta: dict) -> bool:
    if amount <= 0:
        return False
    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry

    result = unified_points_db.add_points(
        user_id, "mn2_balance", amount, source=source, metadata=meta,
    )
    if not result.get("success", True):
        return False
    try:
        append_entry(user_id=user_id, entry_type=source, amount=amount, metadata=meta)
    except Exception:
        pass
    try:
        from backend.services.activity_events_service import emit
        emit("generator_mn2_credit", channel="generator", user_id=user_id, payload={"amount": amount, "source": source, **meta})
    except Exception:
        pass
    return True


def charge_if_requested(
    user_id: str,
    doc_id: str,
    config: Dict[str, Any],
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Debit MN2 when pay_with_mn2 or premium tier is selected. Records charge for refund."""
    cfg = get_generator_config()
    if not cfg.get("enabled", True):
        return {"success": True, "charged": False, "skipped": "disabled"}

    tier = _tier_from_config(config, body)
    quote = quote_generation(
        duration=int(config.get("duration") or 180),
        short_clip=bool(config.get("short_clip")),
        tier=tier,
        config=config,
    )
    price = float(quote.get("price_mn2") or 0)
    if tier == "standard" or price <= 0:
        return {"success": True, "charged": False, "tier": tier, "price_mn2": 0}

    meta = {
        "doc_id": doc_id,
        "tier": tier,
        "price_mn2": price,
        "user_id": user_id,
    }
    debit = _debit(user_id, price, meta)
    if not debit.get("success"):
        return debit

    charges = _load_charges()
    charges[doc_id] = {
        "user_id": user_id,
        "amount": price,
        "tier": tier,
        "charged_at": _iso(),
        "refunded": False,
        "earned": False,
    }
    _save_charges(charges)
    config["mn2_charge"] = {"tier": tier, "price_mn2": price, "doc_id": doc_id}
    return {
        "success": True,
        "charged": True,
        "tier": tier,
        "price_mn2": price,
        "mn2_balance": debit.get("mn2_balance"),
    }


def refund_on_failure(doc_id: str, reason: str = "generation_failed") -> Dict[str, Any]:
    charges = _load_charges()
    rec = charges.get(doc_id)
    if not rec or rec.get("refunded") or float(rec.get("amount") or 0) <= 0:
        return {"success": True, "refunded": False, "skipped": True}

    user_id = rec.get("user_id")
    amount = float(rec["amount"])
    meta = {"doc_id": doc_id, "reason": reason, "original_tier": rec.get("tier")}
    if not _credit(user_id, amount, "generator_mn2_refund", meta):
        return {"success": False, "error": "Refund credit failed", "doc_id": doc_id}

    rec["refunded"] = True
    rec["refunded_at"] = _iso()
    rec["refund_reason"] = reason
    charges[doc_id] = rec
    _save_charges(charges)
    return {"success": True, "refunded": True, "amount": amount, "doc_id": doc_id}


def award_finish_bonus(user_id: str, doc_id: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    from backend.services.mn2_earn_auth import require_earn_user
    ok, uid_or_err = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid_or_err, "awarded": 0.0}

    cfg = get_generator_config()
    if not cfg.get("enabled", True):
        return {"success": True, "awarded": 0.0, "skipped": "disabled"}

    charges = _load_charges()
    rec = charges.get(doc_id) or {}
    if rec.get("earned"):
        return {"success": True, "awarded": 0.0, "skipped": "already_awarded"}

    base_earn = float(cfg.get("earn_on_finish_mn2") or 0.005)
    tier = rec.get("tier") or _tier_from_config(config or {})
    tier_bonus = {"express": 0.002, "premium": 0.005, "ultra": 0.01}.get(tier, 0.0)
    amount = round(min(float(cfg.get("max_earn_per_video_mn2") or 0.05), base_earn + tier_bonus), 8)
    if amount <= 0:
        return {"success": True, "awarded": 0.0}

    meta = {"doc_id": doc_id, "tier": tier, "source": "generator_finish_bonus", "reference": f"gen-earn:{doc_id}"}
    if not _credit(uid_or_err, amount, "generator_mn2_earn", meta):
        return {"success": False, "error": "Earn credit failed"}

    if doc_id not in charges:
        charges[doc_id] = {"user_id": uid_or_err, "amount": 0, "tier": tier}
    charges[doc_id]["earned"] = True
    charges[doc_id]["earn_amount"] = amount
    charges[doc_id]["earned_at"] = _iso()
    _save_charges(charges)
    return {"success": True, "awarded": amount, "doc_id": doc_id}


def get_last_earn_for_user(user_id: str) -> Optional[float]:
    """Most recent finish bonus for UI refresh."""
    charges = _load_charges()
    best = None
    best_ts = ""
    for rec in charges.values():
        if rec.get("user_id") != user_id or not rec.get("earned"):
            continue
        ts = rec.get("earned_at") or ""
        if ts >= best_ts:
            best_ts = ts
            best = float(rec.get("earn_amount") or 0)
    return best
