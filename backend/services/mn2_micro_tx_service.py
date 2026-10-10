"""
MN2 micro-transaction / instant reward payout service.

Credits in-app mn2_balance immediately via unified_points_database (no per-reward chain tx).
Idempotent payout keys, configurable limits, daily caps, and append-only audit trail.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "mn2_micro_tx_config.json")
_LOG_DIR = os.path.join(_BASE, "logs", "mn2_micro_tx")
_LEDGER_PATH = os.path.join(_LOG_DIR, "ledger.jsonl")
_IDEM_PATH = os.path.join(_LOG_DIR, "idempotency.json")
_DAILY_PATH = os.path.join(_LOG_DIR, "daily_totals.json")
_STATS_PATH = os.path.join(_LOG_DIR, "platform_stats.json")
_SWEEP_PATH = os.path.join(_LOG_DIR, "batch_sweep_queue.json")

_DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "min_amount_mn2": 1e-8,
    "max_amount_mn2": 1.0,
    "daily_cap_per_user_mn2": 10.0,
    "rate_limit_per_minute": 120,
    "allowed_sources": [
        "shop_purchase", "game_win", "quest_complete", "casino_spin",
        "staking_accrual", "referral", "daily_login", "aggregator_action",
        "creator_rating", "manual_ops",
    ],
    "source_default_amounts_mn2": {},
    "batch_sweep": {"enabled": False, "threshold_mn2": 1.0},
    "idempotency_ttl_days": 30,
}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


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


def _append_ledger(entry: dict) -> None:
    os.makedirs(_LOG_DIR, exist_ok=True)
    with _LOCK:
        with open(_LEDGER_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_config() -> Dict[str, Any]:
    cfg = dict(_DEFAULTS)
    root = _read_json(_CONFIG_PATH)
    if root:
        cfg.update(root)
    if not isinstance(cfg.get("allowed_sources"), list):
        cfg["allowed_sources"] = list(_DEFAULTS["allowed_sources"])
    if not isinstance(cfg.get("source_default_amounts_mn2"), dict):
        cfg["source_default_amounts_mn2"] = {}
    if not isinstance(cfg.get("batch_sweep"), dict):
        cfg["batch_sweep"] = dict(_DEFAULTS["batch_sweep"])
    return cfg


def _normalize_source(source: str) -> str:
    return (source or "").strip().lower().replace(" ", "_").replace("-", "_")


def _resolve_amount(amount_mn2: Optional[float], source: str, cfg: Dict[str, Any]) -> float:
    if amount_mn2 is not None:
        return round(float(amount_mn2), 8)
    defaults = cfg.get("source_default_amounts_mn2") or {}
    key = _normalize_source(source)
    if key in defaults:
        return round(float(defaults[key] or 0), 8)
    return 0.0


def _user_daily_total(user_id: str, day: str) -> float:
    data = _read_json(_DAILY_PATH)
    users = data.get("users") if isinstance(data.get("users"), dict) else {}
    rec = users.get(user_id) if isinstance(users.get(user_id), dict) else {}
    days = rec.get("days") if isinstance(rec.get("days"), dict) else {}
    return float(days.get(day) or 0)


def _record_daily(user_id: str, amount: float) -> None:
    day = _today()
    with _LOCK:
        data = _read_json(_DAILY_PATH)
        users = data.setdefault("users", {})
        rec = users.setdefault(user_id, {"days": {}, "total_mn2": 0.0, "count": 0})
        days = rec.setdefault("days", {})
        days[day] = round(float(days.get(day) or 0) + amount, 8)
        rec["total_mn2"] = round(float(rec.get("total_mn2") or 0) + amount, 8)
        rec["count"] = int(rec.get("count") or 0) + 1
        rec["last_at"] = _iso()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        rec["days"] = {k: v for k, v in days.items() if k >= cutoff}
        _write_json(_DAILY_PATH, data)


def _check_idempotency(key: str, cfg: Dict[str, Any]) -> Optional[dict]:
    if not key:
        return None
    with _LOCK:
        store = _read_json(_IDEM_PATH)
        hits = store.get("keys") if isinstance(store.get("keys"), dict) else {}
        if key in hits:
            return hits[key]
    return None


def _save_idempotency(key: str, result: dict, cfg: Dict[str, Any]) -> None:
    if not key:
        return
    ttl_days = int(cfg.get("idempotency_ttl_days") or 30)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=ttl_days)).isoformat()
    with _LOCK:
        store = _read_json(_IDEM_PATH)
        hits = store.setdefault("keys", {})
        hits[key] = {**result, "stored_at": _iso()}
        hits = {k: v for k, v in hits.items() if (v.get("stored_at") or "") >= cutoff}
        store["keys"] = hits
        _write_json(_IDEM_PATH, store)


def _rate_limit_ok(user_id: str, cfg: Dict[str, Any]) -> bool:
    limit = int(cfg.get("rate_limit_per_minute") or 0)
    if limit <= 0:
        return True
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    count = 0
    if not os.path.isfile(_LEDGER_PATH):
        return True
    try:
        with open(_LEDGER_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("user_id") != user_id:
                    continue
                if (row.get("created_at") or "") >= cutoff:
                    count += 1
                    if count >= limit:
                        return False
    except Exception:
        return True
    return True


def _bump_platform_stats(amount: float, source: str, status: str) -> None:
    with _LOCK:
        stats = _read_json(_STATS_PATH)
        stats["total_volume_mn2"] = round(float(stats.get("total_volume_mn2") or 0) + amount, 8)
        stats["total_count"] = int(stats.get("total_count") or 0) + 1
        by_source = stats.setdefault("by_source", {})
        src = _normalize_source(source)
        rec = by_source.setdefault(src, {"volume_mn2": 0.0, "count": 0})
        rec["volume_mn2"] = round(float(rec.get("volume_mn2") or 0) + amount, 8)
        rec["count"] = int(rec.get("count") or 0) + 1
        if status == "failed":
            stats["failed_count"] = int(stats.get("failed_count") or 0) + 1
        stats["updated_at"] = _iso()
        _write_json(_STATS_PATH, stats)


def _current_balance(user_id: str) -> float:
    from backend.services.unified_points_database import unified_points_db
    snap = unified_points_db.get_all_points(user_id) or {}
    pts = snap.get("points") or {}
    return float(pts.get("mn2_balance") or pts.get("systems", {}).get("mn2_balance") or 0)


def instant_payout(
    user_id: str,
    amount_mn2: Optional[float] = None,
    reason: str = "",
    source: str = "manual_ops",
    idempotency_key: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Dict[str, Any]:
    """
    Credit MN2 instantly to in-app wallet. Returns payout result dict.
    Pass idempotency_key to prevent double-reward on retries.
    """
    from backend.services.mn2_earn_auth import require_earn_user
    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry

    uid = str(user_id or "").strip()
    ok, err = require_earn_user(uid)
    if not ok:
        return {"success": False, "error": err, "code": "auth_required"}

    cfg = get_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "Micro-tx disabled", "code": "disabled"}

    src = _normalize_source(source)
    allowed = {_normalize_source(s) for s in (cfg.get("allowed_sources") or [])}
    if src not in allowed:
        return {"success": False, "error": f"Source not allowed: {src}", "code": "source_denied"}

    try:
        amount = _resolve_amount(amount_mn2, src, cfg)
    except (TypeError, ValueError):
        return {"success": False, "error": "Invalid amount", "code": "invalid_amount"}

    min_amt = float(cfg.get("min_amount_mn2") or 0)
    max_amt = float(cfg.get("max_amount_mn2") or 1.0)
    if amount < min_amt:
        return {"success": False, "error": f"Below min {min_amt} MN2", "code": "below_min", "amount_mn2": amount}
    if amount > max_amt:
        return {"success": False, "error": f"Above max {max_amt} MN2", "code": "above_max", "amount_mn2": amount}

    idem_key = (idempotency_key or "").strip()
    if not idem_key:
        idem_key = f"micro-tx:{uid}:{src}:{reason or 'reward'}:{uuid.uuid4().hex[:12]}"
    cached = _check_idempotency(idem_key, cfg)
    if cached:
        return {
            "success": True,
            "duplicate": True,
            "payout_id": cached.get("payout_id"),
            "amount_mn2": cached.get("amount_mn2", amount),
            "mn2_balance": _current_balance(uid),
            "idempotency_key": idem_key,
        }

    day = _today()
    daily_cap = float(cfg.get("daily_cap_per_user_mn2") or 0)
    earned_today = _user_daily_total(uid, day)
    if daily_cap > 0 and earned_today + amount > daily_cap + 1e-12:
        return {
            "success": False,
            "error": "Daily micro-tx cap reached",
            "code": "daily_cap",
            "earned_today_mn2": round(earned_today, 8),
            "daily_cap_mn2": daily_cap,
        }

    if not _rate_limit_ok(uid, cfg):
        return {"success": False, "error": "Rate limit exceeded", "code": "rate_limit"}

    payout_id = f"mtx-{uuid.uuid4().hex[:16]}"
    meta = {
        "payout_id": payout_id,
        "source": src,
        "reason": (reason or "")[:200],
        "reference": idem_key,
        "idempotency_key": idem_key,
    }
    if metadata:
        meta.update(metadata)

    credit = unified_points_db.add_points(
        uid, "mn2_balance", amount, source=f"micro_tx_{src}", metadata=meta,
    )
    if not credit.get("success", True):
        _append_ledger({
            "payout_id": payout_id, "user_id": uid, "amount_mn2": amount,
            "source": src, "reason": reason, "status": "failed",
            "error": credit.get("error"), "created_at": _iso(), "idempotency_key": idem_key,
        })
        _bump_platform_stats(amount, src, "failed")
        return {"success": False, "error": credit.get("error", "Credit failed"), "code": "credit_failed"}

    if credit.get("duplicate"):
        result = {
            "success": True, "duplicate": True, "payout_id": payout_id,
            "amount_mn2": amount, "mn2_balance": _current_balance(uid),
            "idempotency_key": idem_key,
        }
        _save_idempotency(idem_key, result, cfg)
        return result

    try:
        append_entry(uid, "micro_tx_reward", amount, metadata=meta)
    except Exception:
        pass

    _record_daily(uid, amount)
    new_bal = _current_balance(uid)
    result = {
        "success": True,
        "payout_id": payout_id,
        "user_id": uid,
        "amount_mn2": amount,
        "source": src,
        "reason": reason or None,
        "mn2_balance": round(new_bal, 8),
        "earned_today_mn2": round(earned_today + amount, 8),
        "idempotency_key": idem_key,
        "instant": True,
    }
    _append_ledger({**result, "status": "completed", "created_at": _iso()})
    _save_idempotency(idem_key, result, cfg)
    _bump_platform_stats(amount, src, "completed")
    _maybe_queue_sweep(uid, amount, cfg)
    return result


def _maybe_queue_sweep(user_id: str, amount: float, cfg: Dict[str, Any]) -> None:
    sweep_cfg = cfg.get("batch_sweep") or {}
    if not sweep_cfg.get("enabled"):
        return
    threshold = float(sweep_cfg.get("threshold_mn2") or 1.0)
    bal = _current_balance(user_id)
    if bal < threshold:
        return
    with _LOCK:
        q = _read_json(_SWEEP_PATH)
        pending = q.setdefault("pending", {})
        pending[user_id] = {
            "balance_mn2": round(bal, 8),
            "threshold_mn2": threshold,
            "queued_at": _iso(),
            "status": "pending",
        }
        _write_json(_SWEEP_PATH, q)


def get_user_stats(user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    cfg = get_config()
    day = _today()
    earned_today = _user_daily_total(uid, day) if uid else 0.0
    data = _read_json(_DAILY_PATH)
    users = data.get("users") if isinstance(data.get("users"), dict) else {}
    rec = users.get(uid) if uid and isinstance(users.get(uid), dict) else {}
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "user_id": uid or None,
        "earned_today_mn2": round(earned_today, 8),
        "lifetime_mn2": round(float(rec.get("total_mn2") or 0), 8),
        "payout_count": int(rec.get("count") or 0),
        "daily_cap_mn2": float(cfg.get("daily_cap_per_user_mn2") or 0),
        "mn2_balance": round(_current_balance(uid), 8) if uid else None,
    }


def get_platform_stats() -> Dict[str, Any]:
    cfg = get_config()
    stats = _read_json(_STATS_PATH)
    sweep = _read_json(_SWEEP_PATH)
    pending = sweep.get("pending") if isinstance(sweep.get("pending"), dict) else {}
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "total_volume_mn2": round(float(stats.get("total_volume_mn2") or 0), 8),
        "total_count": int(stats.get("total_count") or 0),
        "failed_count": int(stats.get("failed_count") or 0),
        "by_source": stats.get("by_source") or {},
        "pending_sweep_count": len(pending),
        "limits": {
            "min_amount_mn2": float(cfg.get("min_amount_mn2") or 0),
            "max_amount_mn2": float(cfg.get("max_amount_mn2") or 1.0),
            "daily_cap_per_user_mn2": float(cfg.get("daily_cap_per_user_mn2") or 0),
        },
        "updated_at": stats.get("updated_at"),
    }


def get_public_config() -> Dict[str, Any]:
    cfg = get_config()
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "allowed_sources": list(cfg.get("allowed_sources") or []),
        "source_default_amounts_mn2": dict(cfg.get("source_default_amounts_mn2") or {}),
        "limits": {
            "min_amount_mn2": float(cfg.get("min_amount_mn2") or 0),
            "max_amount_mn2": float(cfg.get("max_amount_mn2") or 1.0),
            "daily_cap_per_user_mn2": float(cfg.get("daily_cap_per_user_mn2") or 0),
        },
    }


def run_batch_sweep(dry_run: bool = False) -> Dict[str, Any]:
    """
    Mark users with balance above batch_sweep.threshold for ops review.
    Does not move on-chain funds — in-app credits remain instant; sweep is treasury ops.
    """
    cfg = get_config()
    sweep_cfg = cfg.get("batch_sweep") or {}
    if not sweep_cfg.get("enabled"):
        return {"success": True, "skipped": "batch_sweep_disabled", "marked": 0}

    threshold = float(sweep_cfg.get("threshold_mn2") or 1.0)
    data = _read_json(_DAILY_PATH)
    users = data.get("users") if isinstance(data.get("users"), dict) else {}
    marked: List[dict] = []
    for uid in users:
        bal = _current_balance(uid)
        if bal >= threshold:
            marked.append({"user_id": uid, "balance_mn2": round(bal, 8), "threshold_mn2": threshold})

    if dry_run:
        return {"success": True, "dry_run": True, "would_mark": len(marked), "users": marked[:50]}

    with _LOCK:
        q = _read_json(_SWEEP_PATH)
        pending = q.setdefault("pending", {})
        for row in marked:
            uid = row["user_id"]
            pending[uid] = {
                **row,
                "queued_at": _iso(),
                "status": "pending",
            }
        q["last_sweep_at"] = _iso()
        q["last_marked"] = len(marked)
        _write_json(_SWEEP_PATH, q)

    return {"success": True, "marked": len(marked), "threshold_mn2": threshold, "users": marked[:50]}


def recent_ledger(limit: int = 50, user_id: Optional[str] = None) -> List[dict]:
    limit = max(1, min(int(limit or 50), 500))
    uid = (user_id or "").strip()
    rows: List[dict] = []
    if not os.path.isfile(_LEDGER_PATH):
        return rows
    try:
        with open(_LEDGER_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if uid and row.get("user_id") != uid:
                    continue
                rows.append(row)
    except Exception:
        return []
    return list(reversed(rows[-limit:]))
