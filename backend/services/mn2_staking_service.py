"""
MN2 staking service.

Custodial staking of in-app MN2 balance with:
- stake / instant-unstake (balance <-> staked, via unified_points_database)
- longevity tiers, browser-rig uptime weighting, shop staking boost, referral, streak
- reward accrual from realized daemon yield (fallback: dynamic-APR budget)
- per-interval reward tracking rows, stabilization reserve, calculator, monitor

State files (data/):
  mn2_staking_config.json     - config (read-only)
  mn2_staking_terms.json      - versioned terms (read-only)
  mn2_stakes.json             - per-user stake state
  mn2_worker_sessions.json    - per-user browser rig uptime accounting
  mn2_staking_consent.json    - per-user terms acceptance
  mn2_staking_reserve.json    - stabilization reserve + lifetime totals
  mn2_staking_rewards.jsonl   - append-only per-interval reward rows
  mn2_staking_referrals.json  - active referral boosts

See docs/MN2_STAKING_PLAN.md.
"""
import os
import json
import hashlib
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

_LOCK = threading.RLock()

_CONFIG_FILE = "mn2_staking_config.json"
_TERMS_FILE = "mn2_staking_terms.json"
_STAKES_FILE = "mn2_stakes.json"
_WORKER_FILE = "mn2_worker_sessions.json"
_CONSENT_FILE = "mn2_staking_consent.json"
_RESERVE_FILE = "mn2_staking_reserve.json"
_REWARDS_FILE = "mn2_staking_rewards.jsonl"
_REFERRALS_FILE = "mn2_staking_referrals.json"


# ---------------------------------------------------------------- paths / io

def _base_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _data_dir() -> str:
    return os.path.join(_base_dir(), "data")


def _path(filename: str) -> str:
    return os.path.join(_data_dir(), filename)


def _read_json(filename: str, default: Any) -> Any:
    path = _path(filename)
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(filename: str, data: Any) -> None:
    os.makedirs(_data_dir(), exist_ok=True)
    path = _path(filename)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime] = None) -> str:
    return (dt or _now()).isoformat().replace("+00:00", "Z")


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


# ------------------------------------------------------------------- config

_DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "min_stake": 0.1,
    "max_stake_per_user": 10000,
    "instant_unstake": True,
    "base_apr_percent": 5.0,
    "reward_pool_mode": "realized_yield",
    "site_margin_percent": 20.0,
    "accrual_interval_minutes": 60,
    "requires_verification": False,
    "terms_version": "1.0",
    "worker": {
        "uptime_weight": 1.25, "min_uptime_weight": 1.0, "max_uptime_weight": 1.5,
        "heartbeat_interval_seconds": 30, "grace_missed_heartbeats": 2, "uptime_window_minutes": 60,
    },
    "longevity_tiers": [{"id": "bronze", "min_days": 0, "multiplier": 1.0, "label": "Bronze"}],
    "boost": {"shop_effect": "staking_boost", "max_stacked_multiplier": 2.0},
    "auto_compound": {"enabled_default": False, "min_reward_to_compound": 0.01},
    "dynamic_apr": {"enabled": True, "target_total_staked": 1000000, "min_apr_percent": 2.0, "max_apr_percent": 8.0},
    "referral": {"enabled": True, "inviter_boost": 1.1, "invitee_boost": 1.1, "duration_minutes": 1440,
                 "max_referrals_per_user_per_day": 5, "requires_verification": True},
    "streak": {"enabled": True, "per_day_bonus": 0.01, "max_bonus": 0.1, "merged_into_longevity": True},
    "stabilization_reserve": {"enabled": True, "fund_from_margin_percent": 25.0, "max_reserve_mn2": 50000},
    "disclaimer": "",
}


def get_config() -> Dict[str, Any]:
    cfg = _read_json(_CONFIG_FILE, {})
    if not isinstance(cfg, dict):
        cfg = {}
    merged = dict(_DEFAULT_CONFIG)
    merged.update(cfg)
    return merged


def get_terms() -> Dict[str, Any]:
    return _read_json(_TERMS_FILE, {"version": get_config().get("terms_version", "1.0"), "sections": []})


# ----------------------------------------------------------- balance helpers

def _points():
    from backend.services.unified_points_database import unified_points_db
    return unified_points_db


def get_balances(user_id: str) -> Tuple[float, float]:
    """Return (mn2_balance, mn2_staked) for the user."""
    try:
        res = _points().get_all_points(str(user_id).strip())
        pts = res.get("points") or {}
        bal = float(pts.get("mn2_balance", 0) or 0)
        staked = pts.get("mn2_staked")
        if staked is None and isinstance(pts.get("systems"), dict):
            staked = pts["systems"].get("mn2_staked", 0)
        return bal, float(staked or 0)
    except Exception:
        return 0.0, 0.0


# ------------------------------------------------------------- stake records

def _load_stakes() -> Dict[str, Any]:
    data = _read_json(_STAKES_FILE, {})
    return data if isinstance(data, dict) else {}


def _save_stakes(d: Dict[str, Any]) -> None:
    _write_json(_STAKES_FILE, d)


def _get_record(stakes: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    rec = stakes.get(user_id)
    if not isinstance(rec, dict):
        rec = {}
    rec.setdefault("staked", 0.0)
    rec.setdefault("staking_since_iso", None)
    rec.setdefault("since_iso", None)
    rec.setdefault("last_accrued_iso", None)
    rec.setdefault("total_earned", 0.0)
    rec.setdefault("auto_compound", bool(get_config().get("auto_compound", {}).get("enabled_default", False)))
    rec.setdefault("streak_days", 0)
    rec.setdefault("last_stake_day", None)
    return rec


# --------------------------------------------------------------- consent

def has_accepted_terms(user_id: str) -> bool:
    consent = _read_json(_CONSENT_FILE, {})
    if not isinstance(consent, dict):
        return False
    rec = consent.get(str(user_id).strip())
    if not isinstance(rec, dict):
        return False
    return str(rec.get("version") or "") == str(get_config().get("terms_version") or "1.0")


def accept_terms(user_id: str, version: Optional[str] = None) -> Dict[str, Any]:
    uid = str(user_id).strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    ver = str(version or get_config().get("terms_version") or "1.0")
    with _LOCK:
        consent = _read_json(_CONSENT_FILE, {})
        if not isinstance(consent, dict):
            consent = {}
        consent[uid] = {"version": ver, "accepted_at": _iso()}
        _write_json(_CONSENT_FILE, consent)
    return {"success": True, "user_id": uid, "version": ver}


# ----------------------------------------------------- multipliers / weights

def longevity_days(rec: Dict[str, Any]) -> float:
    since = _parse_iso(rec.get("staking_since_iso"))
    if not since:
        return 0.0
    return max(0.0, (_now() - since).total_seconds() / 86400.0)


def longevity_tier(days: float) -> Dict[str, Any]:
    tiers = sorted(get_config().get("longevity_tiers", []), key=lambda t: t.get("min_days", 0))
    chosen = {"id": "bronze", "multiplier": 1.0, "label": "Bronze", "min_days": 0}
    nxt = None
    for t in tiers:
        if days >= float(t.get("min_days", 0)):
            chosen = t
        elif nxt is None:
            nxt = t
    out = dict(chosen)
    out["days"] = round(days, 3)
    out["next_tier"] = nxt
    if nxt:
        out["days_to_next"] = max(0.0, float(nxt.get("min_days", 0)) - days)
    return out


def streak_multiplier(rec: Dict[str, Any]) -> float:
    cfg = get_config().get("streak", {})
    if not cfg.get("enabled"):
        return 1.0
    bonus = min(float(rec.get("streak_days", 0)) * float(cfg.get("per_day_bonus", 0.0)),
                float(cfg.get("max_bonus", 0.0)))
    return 1.0 + bonus


def _staking_boost_sku_map() -> Dict[str, float]:
    """sku_id -> boost_multiplier for shop SKUs with effect == staking_boost."""
    out: Dict[str, float] = {}
    effect = get_config().get("boost", {}).get("shop_effect", "staking_boost")
    try:
        base = _base_dir()
        cfg = _read_json("monetization_config.json", {})
        if not cfg:
            path = os.path.join(base, "data", "monetization_config.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
        for sku in (cfg.get("shop_booster_skus") or []):
            if isinstance(sku, dict) and (sku.get("effect") or "") == effect:
                out[str(sku.get("id"))] = float(sku.get("boost_multiplier", 1.0) or 1.0)
    except Exception:
        pass
    return out


def active_boost_multiplier(user_id: str) -> float:
    try:
        sku_map = _staking_boost_sku_map()
        if not sku_map:
            return 1.0
        gtb = _points().get_game_time_and_boosters(str(user_id).strip())
        best = 1.0
        for b in (gtb.get("active_boosters") or []):
            bid = str(b.get("id") or "")
            if bid in sku_map:
                best = max(best, sku_map[bid])
        cap = float(get_config().get("boost", {}).get("max_stacked_multiplier", 2.0))
        return min(best, cap)
    except Exception:
        return 1.0


def active_referral_multiplier(user_id: str) -> float:
    refs = _read_json(_REFERRALS_FILE, {})
    if not isinstance(refs, dict):
        return 1.0
    rec = refs.get(str(user_id).strip())
    if not isinstance(rec, dict):
        return 1.0
    exp = _parse_iso(rec.get("expires_at"))
    if exp and exp > _now():
        return float(rec.get("multiplier", 1.0) or 1.0)
    return 1.0


def _worker_sessions() -> Dict[str, Any]:
    d = _read_json(_WORKER_FILE, {})
    return d if isinstance(d, dict) else {}


def uptime_ratio(user_id: str) -> float:
    """Fraction of expected heartbeats received in the rolling window (0..1)."""
    cfg = get_config().get("worker", {})
    sess = _worker_sessions().get(str(user_id).strip())
    if not isinstance(sess, dict):
        return 0.0
    last = _parse_iso(sess.get("last_heartbeat_iso"))
    if not last:
        return 0.0
    interval = max(1, int(cfg.get("heartbeat_interval_seconds", 30)))
    grace = int(cfg.get("grace_missed_heartbeats", 2))
    if (_now() - last).total_seconds() > interval * (grace + 1):
        return 0.0
    window_min = int(cfg.get("uptime_window_minutes", 60))
    expected = max(1, (window_min * 60) // interval)
    got = int(sess.get("heartbeats_in_window", 0) or 0)
    return max(0.0, min(1.0, got / expected))


def rig_active(user_id: str) -> bool:
    return uptime_ratio(user_id) > 0.0


def uptime_weight(user_id: str) -> float:
    cfg = get_config().get("worker", {})
    mn = float(cfg.get("min_uptime_weight", 1.0))
    target = float(cfg.get("uptime_weight", 1.25))
    mx = float(cfg.get("max_uptime_weight", 1.5))
    ratio = uptime_ratio(user_id)
    return min(mx, mn + ratio * (target - mn))


def dynamic_apr() -> float:
    cfg = get_config()
    base = float(cfg.get("base_apr_percent", 5.0))
    dy = cfg.get("dynamic_apr", {})
    if not dy.get("enabled"):
        return base
    total = total_staked()
    target = float(dy.get("target_total_staked", 1000000) or 1)
    mn = float(dy.get("min_apr_percent", 2.0))
    mx = float(dy.get("max_apr_percent", 8.0))
    if total <= 0:
        return mx
    apr = base * (target / total)
    return max(mn, min(mx, apr))


def total_staked() -> float:
    return round(sum(float(r.get("staked", 0) or 0) for r in _load_stakes().values()), 8)


def effective_multiplier(user_id: str, rec: Dict[str, Any]) -> Dict[str, float]:
    days = longevity_days(rec)
    tier = longevity_tier(days)
    lon = float(tier.get("multiplier", 1.0))
    strk = streak_multiplier(rec) if get_config().get("streak", {}).get("merged_into_longevity") else 1.0
    up = uptime_weight(user_id)
    boost = active_boost_multiplier(user_id)
    ref = active_referral_multiplier(user_id)
    return {
        "longevity": lon * strk,
        "uptime": up,
        "boost": boost,
        "referral": ref,
        "combined": lon * strk * up * boost * ref,
    }


# ------------------------------------------------------------- stake/unstake

def _verification_ok(user_id: str) -> bool:
    if not get_config().get("requires_verification"):
        return True
    try:
        from backend.services.mn2_verification import is_verified
        return bool(is_verified(user_id))
    except Exception:
        return False


def stake(user_id: str, amount: Any) -> Dict[str, Any]:
    cfg = get_config()
    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    if not cfg.get("enabled"):
        return {"success": False, "error": "Staking is currently disabled"}
    try:
        amt = round(float(amount), 8)
    except (TypeError, ValueError):
        return {"success": False, "error": "amount must be a number"}
    if amt <= 0:
        return {"success": False, "error": "amount must be positive"}
    if amt < float(cfg.get("min_stake", 0)):
        return {"success": False, "error": f"Minimum stake is {cfg.get('min_stake')} MN2"}
    if not has_accepted_terms(uid):
        return {"success": False, "error": "Staking terms must be accepted first", "code": "consent_required",
                "terms_version": cfg.get("terms_version", "1.0")}
    if not _verification_ok(uid):
        return {"success": False, "error": "Account verification required to stake", "code": "verification_required"}

    with _LOCK:
        bal, staked = get_balances(uid)
        if bal < amt:
            return {"success": False, "error": "Insufficient MN2 balance"}
        max_user = float(cfg.get("max_stake_per_user", 0) or 0)
        if max_user > 0 and staked + amt > max_user:
            return {"success": False, "error": f"Max staked per user is {max_user} MN2"}

        _points().add_points(uid, "mn2_balance", -amt, source="mn2_stake")
        _points().add_points(uid, "mn2_staked", amt, source="mn2_stake")

        stakes = _load_stakes()
        rec = _get_record(stakes, uid)
        was_zero = float(rec.get("staked", 0) or 0) <= 0
        rec["staked"] = round(float(rec.get("staked", 0) or 0) + amt, 8)
        now_iso = _iso()
        rec["since_iso"] = now_iso
        if was_zero or not rec.get("staking_since_iso"):
            rec["staking_since_iso"] = now_iso
        _update_streak(rec)
        stakes[uid] = rec
        _save_stakes(stakes)

    _ledger_append(uid, "stake", amt)
    return {"success": True, **get_stake(uid)}


def unstake(user_id: str, amount: Any) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    try:
        amt = round(float(amount), 8)
    except (TypeError, ValueError):
        return {"success": False, "error": "amount must be a number"}
    if amt <= 0:
        return {"success": False, "error": "amount must be positive"}

    with _LOCK:
        stakes = _load_stakes()
        rec = _get_record(stakes, uid)
        cur = round(float(rec.get("staked", 0) or 0), 8)
        if amt > cur:
            return {"success": False, "error": "Cannot unstake more than staked"}

        _points().add_points(uid, "mn2_staked", -amt, source="mn2_unstake")
        _points().add_points(uid, "mn2_balance", amt, source="mn2_unstake")

        rec["staked"] = round(cur - amt, 8)
        if rec["staked"] <= 0:
            rec["staked"] = 0.0
            rec["staking_since_iso"] = None
            rec["streak_days"] = 0
        stakes[uid] = rec
        _save_stakes(stakes)

    _ledger_append(uid, "unstake", amt)
    return {"success": True, **get_stake(uid)}


def _update_streak(rec: Dict[str, Any]) -> None:
    if not get_config().get("streak", {}).get("enabled"):
        return
    today = _now().date().isoformat()
    last = rec.get("last_stake_day")
    if last == today:
        return
    yesterday = (_now().date() - timedelta(days=1)).isoformat()
    rec["streak_days"] = int(rec.get("streak_days", 0) or 0) + 1 if last == yesterday else 1
    rec["last_stake_day"] = today


def _ledger_append(user_id: str, entry_type: str, amount: float, metadata: Optional[Dict[str, Any]] = None) -> None:
    try:
        from backend.services.mn2_ledger import append_entry
        append_entry(user_id=user_id, entry_type=entry_type, amount=float(amount), metadata=metadata or {})
    except Exception:
        pass


# ------------------------------------------------------------------- status

def get_stake(user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    cfg = get_config()
    bal, staked = get_balances(uid)
    stakes = _load_stakes()
    rec = _get_record(stakes, uid)
    days = longevity_days(rec)
    tier = longevity_tier(days)
    mults = effective_multiplier(uid, rec)
    apr = dynamic_apr()
    interval_fraction = float(cfg.get("accrual_interval_minutes", 60)) / (60.0 * 24.0 * 365.0)
    est_next = round(staked * (apr / 100.0) * interval_fraction * mults["combined"], 8)
    return {
        "user_id": uid,
        "enabled": bool(cfg.get("enabled")),
        "mn2_balance": round(bal, 8),
        "staked": round(staked, 8),
        "total_earned": round(float(rec.get("total_earned", 0) or 0), 8),
        "apr_percent": round(apr, 4),
        "effective_apr_percent": round(apr * mults["combined"], 4),
        "longevity_days": round(days, 3),
        "longevity_tier": tier.get("id"),
        "longevity_label": tier.get("label"),
        "days_to_next_tier": tier.get("days_to_next"),
        "next_tier": (tier.get("next_tier") or {}).get("id") if tier.get("next_tier") else None,
        "multipliers": {k: round(v, 4) for k, v in mults.items()},
        "rig_active": rig_active(uid),
        "uptime_ratio": round(uptime_ratio(uid), 4),
        "auto_compound": bool(rec.get("auto_compound")),
        "streak_days": int(rec.get("streak_days", 0) or 0),
        "boost_multiplier": round(mults["boost"], 4),
        "referral_multiplier": round(mults["referral"], 4),
        "estimated_next_interval_reward": est_next,
        "accrual_interval_minutes": int(cfg.get("accrual_interval_minutes", 60)),
        "terms_accepted": has_accepted_terms(uid),
        "terms_version": cfg.get("terms_version", "1.0"),
        "instant_unstake": bool(cfg.get("instant_unstake", True)),
        "disclaimer": cfg.get("disclaimer", ""),
    }


def set_auto_compound(user_id: str, enabled: bool) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    with _LOCK:
        stakes = _load_stakes()
        rec = _get_record(stakes, uid)
        rec["auto_compound"] = bool(enabled)
        stakes[uid] = rec
        _save_stakes(stakes)
    return {"success": True, "user_id": uid, "auto_compound": bool(enabled)}


# --------------------------------------------------------------- calculator

def estimate_rewards(amount: Any, days: Any = 30, uptime: Any = 1.0,
                     boost: Any = 1.0, tier_multiplier: Optional[float] = None) -> Dict[str, Any]:
    cfg = get_config()
    try:
        amt = max(0.0, float(amount))
    except (TypeError, ValueError):
        amt = 0.0
    try:
        n_days = max(0.0, float(days))
    except (TypeError, ValueError):
        n_days = 30.0
    try:
        up_ratio = max(0.0, min(1.0, float(uptime)))
    except (TypeError, ValueError):
        up_ratio = 1.0
    try:
        boost_m = max(1.0, float(boost))
    except (TypeError, ValueError):
        boost_m = 1.0

    w = cfg.get("worker", {})
    mn, target, mx = float(w.get("min_uptime_weight", 1.0)), float(w.get("uptime_weight", 1.25)), float(w.get("max_uptime_weight", 1.5))
    up_weight = min(mx, mn + up_ratio * (target - mn))
    if tier_multiplier is None:
        tier_multiplier = float(longevity_tier(n_days).get("multiplier", 1.0))
    apr = dynamic_apr()
    daily_base = amt * (apr / 100.0) / 365.0
    effective_daily = daily_base * float(tier_multiplier) * up_weight * boost_m
    projected = effective_daily * n_days
    return {
        "success": True,
        "amount": round(amt, 8),
        "days": n_days,
        "apr_percent": round(apr, 4),
        "uptime_weight": round(up_weight, 4),
        "tier_multiplier": round(float(tier_multiplier), 4),
        "boost_multiplier": round(boost_m, 4),
        "daily_base_mn2": round(daily_base, 8),
        "effective_daily_mn2": round(effective_daily, 8),
        "projected_reward_mn2": round(projected, 8),
        "projected_total_mn2": round(amt + projected, 8),
        "note": "Estimate only. Rewards are variable, not guaranteed, and depend on realized pool yield.",
    }


# ---------------------------------------------------------------- rig proof

def submit_work_proof(user_id: str, proof: Optional[str] = None,
                      nonce: Optional[str] = None, ts: Optional[Any] = None) -> Dict[str, Any]:
    """Record a browser-rig heartbeat. Proof validation is lightweight (engagement signal)."""
    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    cfg = get_config().get("worker", {})
    interval = max(1, int(cfg.get("heartbeat_interval_seconds", 30)))
    window_min = int(cfg.get("uptime_window_minutes", 60))
    with _LOCK:
        sessions = _worker_sessions()
        sess = sessions.get(uid) if isinstance(sessions.get(uid), dict) else {}
        now = _now()
        win_start = _parse_iso(sess.get("window_start_iso"))
        if not win_start or (now - win_start).total_seconds() > window_min * 60:
            sess["window_start_iso"] = _iso(now)
            sess["heartbeats_in_window"] = 0
        last = _parse_iso(sess.get("last_heartbeat_iso"))
        # rate-limit: ignore heartbeats faster than ~half the interval (anti-spam)
        if last and (now - last).total_seconds() < interval * 0.5:
            return {"success": True, "throttled": True, "uptime_ratio": round(uptime_ratio(uid), 4)}
        sess["last_heartbeat_iso"] = _iso(now)
        sess["heartbeats_in_window"] = int(sess.get("heartbeats_in_window", 0) or 0) + 1
        sess["accepted_proofs"] = int(sess.get("accepted_proofs", 0) or 0) + 1
        if proof:
            sess["last_proof"] = str(proof)[:64]
        sessions[uid] = sess
        _write_json(_WORKER_FILE, sessions)
    return {"success": True, "uptime_ratio": round(uptime_ratio(uid), 4),
            "uptime_weight": round(uptime_weight(uid), 4), "rig_active": True,
            "next_heartbeat_seconds": interval}


# ------------------------------------------------------------------ reserve

def _load_reserve() -> Dict[str, Any]:
    r = _read_json(_RESERVE_FILE, {})
    if not isinstance(r, dict):
        r = {}
    r.setdefault("reserve_mn2", 0.0)
    r.setdefault("lifetime_realized_yield", 0.0)
    r.setdefault("lifetime_paid", 0.0)
    return r


def _save_reserve(r: Dict[str, Any]) -> None:
    _write_json(_RESERVE_FILE, r)


# -------------------------------------------------------------- realized yield

def _read_realized_yield_mn2() -> float:
    """Best-effort: sum new daemon staking income (stake/generate). 0 on any error (APR fallback)."""
    try:
        from backend.services.mn2_rpc_client import listtransactions
        r = listtransactions(count=200)
        if r.get("error") or not isinstance(r.get("result"), list):
            return 0.0
        total = 0.0
        for tx in r["result"]:
            cat = str(tx.get("category") or "").lower()
            if cat in ("stake", "generate", "immature", "mint"):
                try:
                    total += abs(float(tx.get("amount") or 0))
                except (TypeError, ValueError):
                    pass
        return round(total, 8)
    except Exception:
        return 0.0


def _interval_id(now: Optional[datetime] = None) -> str:
    now = now or _now()
    minutes = max(1, int(get_config().get("accrual_interval_minutes", 60)))
    epoch_min = int(now.timestamp() // 60)
    bucket = (epoch_min // minutes) * minutes
    return datetime.fromtimestamp(bucket * 60, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _interval_already_processed(interval_id: str) -> bool:
    path = _path(_REWARDS_FILE)
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if f'"interval_id": "{interval_id}"' in line:
                    return True
    except Exception:
        return False
    return False


def _append_reward_rows(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    os.makedirs(_data_dir(), exist_ok=True)
    path = _path(_REWARDS_FILE)
    with open(path, "a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def accrue_rewards(force: bool = False) -> Dict[str, Any]:
    """Run one accrual interval. Idempotent per interval_id. Credits rewards to mn2_balance."""
    cfg = get_config()
    if not cfg.get("enabled"):
        return {"success": False, "error": "Staking disabled"}
    with _LOCK:
        interval_id = _interval_id()
        if not force and _interval_already_processed(interval_id):
            return {"success": True, "skipped": True, "reason": "interval already processed", "interval_id": interval_id}

        stakes = _load_stakes()
        active = {uid: _get_record(stakes, uid) for uid, r in stakes.items()
                  if float((r or {}).get("staked", 0) or 0) > 0}
        if not active:
            return {"success": True, "interval_id": interval_id, "rewarded_users": 0, "total_reward_mn2": 0.0}

        # weights
        weights: Dict[str, float] = {}
        mults_by_user: Dict[str, Dict[str, float]] = {}
        for uid, rec in active.items():
            m = effective_multiplier(uid, rec)
            mults_by_user[uid] = m
            weights[uid] = float(rec.get("staked", 0) or 0) * m["combined"]
        sum_weight = sum(weights.values()) or 0.0

        # budget
        margin = float(cfg.get("site_margin_percent", 0)) / 100.0
        realized = _read_realized_yield_mn2() if cfg.get("reward_pool_mode") == "realized_yield" else 0.0
        reserve = _load_reserve()
        apr = dynamic_apr()
        interval_fraction = float(cfg.get("accrual_interval_minutes", 60)) / (60.0 * 24.0 * 365.0)

        use_realized = realized > 0
        budget = realized * (1.0 - margin) if use_realized else 0.0

        # reserve funding from margin slice
        rcfg = cfg.get("stabilization_reserve", {})
        if use_realized and rcfg.get("enabled"):
            fund = realized * margin * (float(rcfg.get("fund_from_margin_percent", 0)) / 100.0)
            cap = float(rcfg.get("max_reserve_mn2", 0) or 0)
            reserve["reserve_mn2"] = min(cap, reserve.get("reserve_mn2", 0.0) + fund) if cap > 0 else reserve.get("reserve_mn2", 0.0) + fund
        if use_realized:
            reserve["lifetime_realized_yield"] = reserve.get("lifetime_realized_yield", 0.0) + realized

        rows: List[Dict[str, Any]] = []
        total_reward = 0.0
        ac_cfg = cfg.get("auto_compound", {})
        now_iso = _iso()

        for uid, rec in active.items():
            staked = float(rec.get("staked", 0) or 0)
            m = mults_by_user[uid]
            if use_realized and sum_weight > 0:
                reward = budget * (weights[uid] / sum_weight)
            else:
                # APR fallback: headline APR already, multipliers boost it
                reward = staked * (apr / 100.0) * interval_fraction * m["combined"]
            reward = round(max(0.0, reward), 8)
            reserve_topup = 0.0
            if reward <= 0:
                continue

            _points().add_points(uid, "mn2_balance", reward, source="mn2_staking_reward",
                                 metadata={"interval_id": interval_id})
            _ledger_append(uid, "staking_reward", reward, metadata={"interval_id": interval_id})

            compounded = 0.0
            if rec.get("auto_compound") and reward >= float(ac_cfg.get("min_reward_to_compound", 0.01)):
                # restake immediately (internal move, no consent re-check)
                _points().add_points(uid, "mn2_balance", -reward, source="mn2_auto_compound")
                _points().add_points(uid, "mn2_staked", reward, source="mn2_auto_compound")
                rec["staked"] = round(staked + reward, 8)
                compounded = reward
                _ledger_append(uid, "stake", reward, metadata={"auto_compound": True})

            rec["total_earned"] = round(float(rec.get("total_earned", 0) or 0) + reward, 8)
            rec["last_accrued_iso"] = now_iso
            stakes[uid] = rec
            total_reward += reward

            bal_after, staked_after = get_balances(uid)
            tier = longevity_tier(longevity_days(rec))
            rows.append({
                "interval_id": interval_id,
                "user_id": uid,
                "accrued_at": now_iso,
                "staked": round(staked, 8),
                "longevity_days": round(longevity_days(rec), 3),
                "longevity_tier": tier.get("id"),
                "longevity_mult": round(m["longevity"], 4),
                "uptime_ratio": round(uptime_ratio(uid), 4),
                "uptime_weight": round(m["uptime"], 4),
                "boost_mult": round(m["boost"], 4),
                "referral_mult": round(m["referral"], 4),
                "effective_apr": round(apr * m["combined"], 4),
                "weight": round(weights[uid], 8),
                "pool_share_pct": round((weights[uid] / sum_weight * 100.0) if sum_weight else 0.0, 6),
                "pool_budget_mn2": round(budget, 8) if use_realized else None,
                "reward_mn2": reward,
                "compounded_mn2": round(compounded, 8),
                "reserve_topup_mn2": round(reserve_topup, 8),
                "cumulative_earned_mn2": round(float(rec.get("total_earned", 0) or 0), 8),
                "balance_after_mn2": round(bal_after, 8),
                "staked_after_mn2": round(staked_after, 8),
                "source": "realized_yield" if use_realized else "apr_fallback",
            })

        reserve["lifetime_paid"] = reserve.get("lifetime_paid", 0.0) + total_reward
        _save_reserve(reserve)
        _save_stakes(stakes)
        _append_reward_rows(rows)

        return {
            "success": True,
            "interval_id": interval_id,
            "rewarded_users": len(rows),
            "total_reward_mn2": round(total_reward, 8),
            "source": "realized_yield" if use_realized else "apr_fallback",
            "realized_yield_mn2": round(realized, 8),
            "reserve_mn2": round(reserve.get("reserve_mn2", 0.0), 8),
        }


# ------------------------------------------------------------- reward table

def get_rewards_table(user_id: str, limit: int = 100, since_iso: Optional[str] = None) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    path = _path(_REWARDS_FILE)
    rows: List[Dict[str, Any]] = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    if (row.get("user_id") or "") != uid:
                        continue
                    if since_iso and (row.get("accrued_at") or "") < since_iso:
                        continue
                    rows.append(row)
        except Exception:
            pass
    rows.sort(key=lambda r: r.get("accrued_at") or "", reverse=True)
    total_earned = round(sum(float(r.get("reward_mn2", 0) or 0) for r in rows), 8)
    aprs = [float(r.get("effective_apr", 0) or 0) for r in rows if r.get("effective_apr") is not None]
    best = max(rows, key=lambda r: float(r.get("reward_mn2", 0) or 0), default=None)
    return {
        "success": True,
        "user_id": uid,
        "rows": rows[: max(1, min(int(limit or 100), 1000))],
        "summary": {
            "total_earned_mn2": total_earned,
            "intervals": len(rows),
            "avg_effective_apr": round(sum(aprs) / len(aprs), 4) if aprs else 0.0,
            "best_interval_reward_mn2": round(float(best.get("reward_mn2", 0)), 8) if best else 0.0,
        },
    }


# ----------------------------------------------------------- leaderboard/monitor

def _anon_id(user_id: str) -> str:
    h = hashlib.sha256(str(user_id).encode("utf-8")).hexdigest()[:8]
    return f"user_{h}"


def get_staking_leaderboard(limit: int = 10) -> Dict[str, Any]:
    stakes = _load_stakes()
    entries = []
    for uid, r in stakes.items():
        staked = float((r or {}).get("staked", 0) or 0)
        if staked <= 0:
            continue
        rec = _get_record(stakes, uid)
        entries.append({
            "display_id": _anon_id(uid),
            "staked": round(staked, 8),
            "total_earned": round(float(rec.get("total_earned", 0) or 0), 8),
            "longevity_days": round(longevity_days(rec), 2),
            "longevity_tier": longevity_tier(longevity_days(rec)).get("id"),
        })
    entries.sort(key=lambda e: e["staked"], reverse=True)
    return {"success": True, "leaderboard": entries[: max(1, min(int(limit or 10), 100))]}


_AGENT_ACTIVITY_FILE = "mn2_staking_agent_activity.jsonl"


def _agent_actions_24h() -> int:
    """Count agent automation actions logged in the last 24h (for the monitor)."""
    path = os.path.join(_data_dir(), _AGENT_ACTIVITY_FILE)
    if not os.path.exists(path):
        return 0
    from datetime import datetime, timezone, timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    n = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    ts = str(row.get("ts") or "").replace("Z", "+00:00")
                    if ts and datetime.fromisoformat(ts) >= cutoff:
                        n += 1
                except Exception:
                    pass
    except Exception:
        pass
    return n


def get_staking_monitor(limit: int = 50) -> Dict[str, Any]:
    stakes = _load_stakes()
    processes = []
    active_rigs = 0
    total = 0.0
    agent_managed_count = 0
    agent_staked = 0.0
    for uid, r in stakes.items():
        staked = float((r or {}).get("staked", 0) or 0)
        if staked <= 0:
            continue
        rec = _get_record(stakes, uid)
        total += staked
        active = rig_active(uid)
        if active:
            active_rigs += 1
        is_agent = bool((r or {}).get("managed_by_agent"))
        if is_agent:
            agent_managed_count += 1
            agent_staked += staked
        m = effective_multiplier(uid, rec)
        sess = _worker_sessions().get(uid) or {}
        processes.append({
            "display_id": _anon_id(uid),
            "staked": round(staked, 8),
            "longevity_tier": longevity_tier(longevity_days(rec)).get("id"),
            "longevity_days": round(longevity_days(rec), 2),
            "uptime_ratio": round(uptime_ratio(uid), 4),
            "rig_active": active,
            "agent_managed": is_agent,
            "effective_apr": round(dynamic_apr() * m["combined"], 4),
            "total_earned": round(float(rec.get("total_earned", 0) or 0), 8),
            "last_heartbeat": sess.get("last_heartbeat_iso"),
        })
    processes.sort(key=lambda p: p["staked"], reverse=True)
    reserve = _load_reserve()
    aggregates = {
        "total_staked": round(total, 8),
        "active_stakers": len(processes),
        "active_rigs": active_rigs,
        "pool_apr_percent": round(dynamic_apr(), 4),
        "rewards_paid_lifetime_mn2": round(reserve.get("lifetime_paid", 0.0), 8),
        "realized_yield_lifetime_mn2": round(reserve.get("lifetime_realized_yield", 0.0), 8),
        "reserve_mn2": round(reserve.get("reserve_mn2", 0.0), 8),
        "agent_managed_stakers": agent_managed_count,
        "agent_staked_mn2": round(agent_staked, 8),
        "agent_actions_24h": _agent_actions_24h(),
    }
    return {"success": True, "aggregates": aggregates,
            "processes": processes[: max(1, min(int(limit or 50), 500))]}
