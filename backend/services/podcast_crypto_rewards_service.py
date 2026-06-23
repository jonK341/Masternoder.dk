"""
Podcast crypto (MN2) rewards — play, share, listen-complete, generator finish.

Credits mn2_balance via game_mn2_rewards.credit_mn2 (idempotent references).
Config: data/mn2_config.json -> podcast
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DAILY_FILE = os.path.join(_BASE, "data", "podcast_crypto_daily.json")
_MN2_CONFIG = os.path.join(_BASE, "data", "mn2_config.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _today_utc() -> str:
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


def _podcast_cfg() -> Dict[str, Any]:
    raw = _read_json(_MN2_CONFIG).get("podcast") or {}
    defaults: Dict[str, Any] = {
        "enabled": True,
        "earn_on_play_mn2": 0.001,
        "earn_on_share_mn2": 0.002,
        "earn_on_listen_complete_mn2": 0.003,
        "earn_on_generate_mn2": 0.005,
        "earn_on_comment_mn2": 0.0015,
        "earn_on_news_comment_mn2": 0.002,
        "daily_first_listen_mn2": 0.01,
        "daily_cap_mn2": 0.25,
        "view_milestone_mn2": 0.0001,
        "view_milestone_every": 100,
        "staking_bonus_percent_per_1000_mn2": 0.5,
        "staking_bonus_cap_percent": 15.0,
    }
    defaults.update(raw)
    return defaults


def _daily_total(user_id: str) -> float:
    with _LOCK:
        daily = _read_json(_DAILY_FILE)
        key = f"{user_id}:{_today_utc()}"
        return float(daily.get(key, {}).get("total_mn2", 0) or 0)


def _add_daily_total(user_id: str, amount: float) -> None:
    with _LOCK:
        daily = _read_json(_DAILY_FILE)
        key = f"{user_id}:{_today_utc()}"
        rec = daily.get(key) or {"total_mn2": 0.0, "events": []}
        rec["total_mn2"] = round(float(rec.get("total_mn2", 0)) + amount, 8)
        rec["events"] = (rec.get("events") or [])[-50:]
        rec["events"].append({"amount": amount, "at": _iso()})
        daily[key] = rec
        _write_json(_DAILY_FILE, daily)


def _staking_bonus_percent(user_id: str) -> float:
    try:
        from backend.services.mn2_staking_service import get_balances
        _, staked = get_balances(str(user_id))
        staked = float(staked or 0)
    except Exception:
        staked = 0.0
    c = _podcast_cfg()
    per_1k = float(c.get("staking_bonus_percent_per_1000_mn2") or 0.5)
    cap = float(c.get("staking_bonus_cap_percent") or 15.0)
    return round(min(cap, (staked / 1000.0) * per_1k), 4)


def _credit_reward(
    user_id: str,
    amount: float,
    source: str,
    reference: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    cfg = _podcast_cfg()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "podcast_rewards_disabled"}
    amt = float(amount or 0)
    if amt <= 0:
        return {"success": False, "error": "zero_amount"}

    cap = float(cfg.get("daily_cap_mn2") or 0.25)
    if cap > 0 and _daily_total(user_id) + amt > cap:
        return {"success": False, "error": "daily_cap_reached", "daily_cap_mn2": cap}

    stake_pct = _staking_bonus_percent(user_id)
    if stake_pct > 0:
        bonus = round(amt * (stake_pct / 100.0), 8)
        if bonus > 0:
            amt = round(amt + bonus, 8)

    from backend.services.game_mn2_rewards import credit_mn2
    meta = dict(metadata or {})
    meta["staking_bonus_percent"] = stake_pct
    result = credit_mn2(user_id, amt, source=source, reference=reference, metadata=meta)
    if result.get("success") and not result.get("duplicate"):
        _add_daily_total(user_id, amt)
    if result.get("success"):
        result["awarded_mn2"] = amt
    return result


def get_crypto_rewards_info(user_id: str) -> Dict[str, Any]:
    cfg = _podcast_cfg()
    return {
        "success": True,
        "enabled": cfg.get("enabled", True),
        "rates": {
            "play_mn2": cfg.get("earn_on_play_mn2"),
            "share_mn2": cfg.get("earn_on_share_mn2"),
            "listen_complete_mn2": cfg.get("earn_on_listen_complete_mn2"),
            "generate_mn2": cfg.get("earn_on_generate_mn2"),
            "comment_mn2": cfg.get("earn_on_comment_mn2"),
            "news_comment_mn2": cfg.get("earn_on_news_comment_mn2"),
            "daily_first_listen_mn2": cfg.get("daily_first_listen_mn2"),
        },
        "daily_cap_mn2": cfg.get("daily_cap_mn2"),
        "daily_earned_mn2": _daily_total(user_id),
        "staking_bonus_percent": _staking_bonus_percent(user_id),
    }


def award_play_reward(user_id: str, episode_id: str) -> Dict[str, Any]:
    cfg = _podcast_cfg()
    amt = float(cfg.get("earn_on_play_mn2") or 0.001)
    return _credit_reward(
        user_id, amt, "podcast_play",
        f"podcast-play:{user_id}:{episode_id}:{_today_utc()}",
        {"episode_id": episode_id, "action": "play"},
    )


def award_share_reward(user_id: str, episode_id: str, platform: str = "") -> Dict[str, Any]:
    cfg = _podcast_cfg()
    amt = float(cfg.get("earn_on_share_mn2") or 0.002)
    return _credit_reward(
        user_id, amt, "podcast_share",
        f"podcast-share:{user_id}:{episode_id}:{platform or 'any'}:{_today_utc()}",
        {"episode_id": episode_id, "platform": platform, "action": "share"},
    )


def award_listen_complete_reward(user_id: str, episode_id: str) -> Dict[str, Any]:
    cfg = _podcast_cfg()
    amt = float(cfg.get("earn_on_listen_complete_mn2") or 0.003)
    with _LOCK:
        daily = _read_json(_DAILY_FILE)
        first_key = f"first_listen:{user_id}:{_today_utc()}"
        if not daily.get(first_key):
            extra = float(cfg.get("daily_first_listen_mn2") or 0.01)
            if extra > 0:
                amt = round(amt + extra, 8)
            daily[first_key] = {"episode_id": episode_id, "at": _iso()}
            _write_json(_DAILY_FILE, daily)
    return _credit_reward(
        user_id, amt, "podcast_listen_complete",
        f"podcast-complete:{user_id}:{episode_id}:{_today_utc()}",
        {"episode_id": episode_id, "action": "listen_complete"},
    )


def award_generate_reward(user_id: str, job_id: str) -> Dict[str, Any]:
    cfg = _podcast_cfg()
    amt = float(cfg.get("earn_on_generate_mn2") or 0.005)
    return _credit_reward(
        user_id, amt, "podcast_generate",
        f"podcast-gen:{user_id}:{job_id}",
        {"job_id": job_id, "action": "generate"},
    )


def award_comment_reward(user_id: str, episode_id: str, comment_id: str) -> Dict[str, Any]:
    cfg = _podcast_cfg()
    amt = float(cfg.get("earn_on_comment_mn2") or 0.0015)
    return _credit_reward(
        user_id, amt, "podcast_comment",
        f"podcast-comment:{user_id}:{comment_id}",
        {"episode_id": episode_id, "comment_id": comment_id, "action": "comment"},
    )


def award_news_comment_reward(user_id: str, news_id: str, comment_id: str) -> Dict[str, Any]:
    cfg = _podcast_cfg()
    amt = float(cfg.get("earn_on_news_comment_mn2") or 0.002)
    return _credit_reward(
        user_id, amt, "podcast_news_comment",
        f"podcast-news-comment:{user_id}:{comment_id}",
        {"news_id": news_id, "comment_id": comment_id, "action": "news_comment"},
    )


def award_view_milestone_reward(user_id: str, episode_id: str, view_count: int) -> Dict[str, Any]:
    cfg = _podcast_cfg()
    every = int(cfg.get("view_milestone_every") or 100)
    if every <= 0 or view_count % every != 0:
        return {"success": True, "skipped": "not_milestone", "view_count": view_count}
    amt = float(cfg.get("view_milestone_mn2") or 0.0001)
    return _credit_reward(
        user_id, amt, "podcast_view_milestone",
        f"podcast-views:{episode_id}:{view_count}",
        {"episode_id": episode_id, "view_count": view_count, "action": "view_milestone"},
    )
