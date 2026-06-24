"""
Casino v12 — income/revalue/earn features, shop, gaming hunt.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_FEATURES_PATH = os.path.join(_BASE, "data", "casino_features_v12.json")
_SHOP_PATH = os.path.join(_BASE, "data", "casino_shop_catalog.json")
_HUNT_PATH = os.path.join(_BASE, "data", "casino_hunt_quests.json")
_STATE_PATH = os.path.join(_BASE, "logs", "casino_earnings", "users.json")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load_json(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
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
    users = data.setdefault("users", {})
    row = users.setdefault(uid, {})
    row.setdefault("owned_items", [])
    row.setdefault("hunt_claimed", [])
    row.setdefault("daily_chest_at", None)
    _save_state(data)
    return row


def _casino_level(user_id: str) -> int:
    try:
        from backend.services.casino_progression_service import get_user_progression

        st = get_user_progression(user_id)
        return int(st.get("level") or 1) if st.get("success") else 1
    except Exception:
        return 1


def _progression_metrics(user_id: str) -> Dict[str, Any]:
    try:
        from backend.services.casino_progression_service import _user_row as prog_row

        row = prog_row(user_id)
        metrics = dict(row.get("metrics") or {})
        metrics["casino_level"] = int(row.get("level") or 1)
        metrics["walk_agent_days"] = int(row.get("walk_agent_days") or 0)
        walk = row.get("walk_today") or {}
        metrics["walk_steps"] = len(walk.get("completed") or [])
        return metrics
    except Exception:
        return {"casino_level": 1}


def _friend_count(user_id: str) -> int:
    try:
        from backend.routes.social_routes import _load_social

        social = _load_social()
        return len((social.get("friends") or {}).get(user_id, []) or [])
    except Exception:
        return 0


def _metric_value(user_id: str, metric: str, metrics: Dict[str, Any]) -> int:
    if metric == "social_friends":
        return _friend_count(user_id)
    try:
        return int(metrics.get(metric) or 0)
    except (TypeError, ValueError):
        return 0


def get_features_public(user_id: str) -> Dict[str, Any]:
    cfg = _load_json(_FEATURES_PATH)
    level = _casino_level(user_id)
    features = []
    for row in cfg.get("features") or []:
        if not isinstance(row, dict):
            continue
        min_lv = int(row.get("min_level") or 1)
        features.append({**row, "unlocked": level >= min_lv})
    return {
        "success": True,
        "version": cfg.get("version"),
        "theme": cfg.get("theme"),
        "user_level": level,
        "features": features,
    }


def get_shop_catalog(user_id: str) -> Dict[str, Any]:
    cfg = _load_json(_SHOP_PATH)
    level = _casino_level(user_id)
    row = _user_row(user_id)
    owned = set(row.get("owned_items") or [])
    items = []
    for item in cfg.get("items") or []:
        if not isinstance(item, dict):
            continue
        iid = item.get("id")
        min_lv = int(item.get("min_level") or 1)
        items.append({
            **item,
            "owned": iid in owned,
            "purchasable": level >= min_lv and iid not in owned,
            "discounted_price": _discounted_price(int(item.get("price_coins") or 0), level),
        })
    return {
        "success": True,
        "currency": cfg.get("currency") or "coins",
        "user_level": level,
        "owned_items": list(owned),
        "items": items,
    }


def _discounted_price(base: int, level: int) -> int:
    if base <= 0:
        return 0
    discount = min(0.25, max(0, (level - 4) * 0.02))
    return max(0, int(round(base * (1 - discount))))


def purchase_shop_item(user_id: str, item_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    iid = (item_id or "").strip()
    if not uid or not iid:
        return {"success": False, "error": "user_id and item_id required"}
    cfg = _load_json(_SHOP_PATH)
    item = next((x for x in (cfg.get("items") or []) if isinstance(x, dict) and x.get("id") == iid), None)
    if not item:
        return {"success": False, "error": "unknown_item"}
    level = _casino_level(uid)
    if level < int(item.get("min_level") or 1):
        return {"success": False, "error": "level_too_low"}
    row = _user_row(uid)
    if iid in (row.get("owned_items") or []):
        return {"success": False, "error": "already_owned"}
    price = _discounted_price(int(item.get("price_coins") or 0), level)
    if item.get("requires_play_app"):
        return {"success": False, "error": "play_app_only"}
    try:
        from backend.services import casino_service

        bal = casino_service.get_balance(uid)
        coins = float(bal.get("coins") or bal.get("balances", {}).get("coins") or 0)
        if price > 0 and coins < price:
            return {"success": False, "error": "insufficient_coins"}
        if price > 0:
            casino_service._apply_balance_delta(uid, -float(price), "coins", "casino_shop", {"item_id": iid})
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    owned = list(row.get("owned_items") or [])
    owned.append(iid)
    row["owned_items"] = owned
    data = _load_state()
    data.setdefault("users", {})[uid] = row
    _save_state(data)
    try:
        from backend.services.casino_social_hub_service import push_casino_activity

        push_casino_activity(uid, "casino_shop_buy", f"Purchased {item.get('name')}", {"item_id": iid, "price": price})
    except Exception:
        pass
    try:
        from backend.services.casino_progression_service import _check_trophies

        _check_trophies(uid)
    except Exception:
        pass
    return {"success": True, "item_id": iid, "price_paid": price, "owned_items": owned}


def get_hunt_status(user_id: str) -> Dict[str, Any]:
    cfg = _load_json(_HUNT_PATH)
    level = _casino_level(user_id)
    row = _user_row(user_id)
    claimed = set(row.get("hunt_claimed") or [])
    metrics = _progression_metrics(user_id)
    quests = []
    for q in cfg.get("quests") or []:
        if not isinstance(q, dict):
            continue
        qid = q.get("id")
        target = int(q.get("target") or 1)
        metric = q.get("metric") or "bets"
        progress = _metric_value(user_id, metric, metrics)
        quests.append({
            **q,
            "progress": progress,
            "target": target,
            "completed": progress >= target,
            "claimed": qid in claimed,
            "claimable": progress >= target and qid not in claimed and level >= int(q.get("min_level") or 1),
        })
    return {
        "success": True,
        "user_level": level,
        "quests": quests,
        "game_hub_href": "/game/?tab=social",
    }


def claim_hunt_quest(user_id: str, quest_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    qid = (quest_id or "").strip()
    st = get_hunt_status(uid)
    quest = next((q for q in st.get("quests") or [] if q.get("id") == qid), None)
    if not quest:
        return {"success": False, "error": "unknown_quest"}
    if not quest.get("claimable"):
        return {"success": False, "error": "not_claimable"}
    row = _user_row(uid)
    claimed = list(row.get("hunt_claimed") or [])
    claimed.append(qid)
    row["hunt_claimed"] = claimed
    data = _load_state()
    data.setdefault("users", {})[uid] = row
    _save_state(data)
    coins = int(quest.get("reward_coins") or 0)
    mn2 = float(quest.get("reward_mn2") or 0)
    try:
        from backend.services.casino_progression_service import _grant_rewards

        _grant_rewards(uid, coins, mn2, source="casino_hunt", metadata={"quest_id": qid})
    except Exception:
        pass
    try:
        from backend.services.casino_social_hub_service import push_casino_activity

        push_casino_activity(uid, "casino_hunt", f"Completed hunt: {quest.get('title')}", {"quest_id": qid})
    except Exception:
        pass
    try:
        from backend.services.casino_progression_service import _check_trophies

        _check_trophies(uid)
    except Exception:
        pass
    return {"success": True, "quest_id": qid, "reward_coins": coins, "reward_mn2": mn2 or None}


def get_earnings_hub(user_id: str) -> Dict[str, Any]:
    return {
        "success": True,
        "features": get_features_public(user_id),
        "shop": get_shop_catalog(user_id),
        "hunt": get_hunt_status(user_id),
    }


def claim_play_app_daily_chest(user_id: str, *, from_play_app: bool = False) -> Dict[str, Any]:
    if not from_play_app:
        return {"success": False, "error": "play_app_only"}
    uid = (user_id or "").strip()
    row = _user_row(uid)
    today = _utcnow().strftime("%Y-%m-%d")
    if row.get("daily_chest_at") == today:
        return {"success": False, "error": "already_claimed_today"}
    row["daily_chest_at"] = today
    row["play_app_chests"] = int(row.get("play_app_chests") or 0) + 1
    data = _load_state()
    data.setdefault("users", {})[uid] = row
    _save_state(data)
    reward = 25 + _casino_level(uid) * 2
    try:
        from backend.services.casino_progression_service import _grant_rewards

        _grant_rewards(uid, reward, 0, source="play_app_chest", metadata={"date": today})
    except Exception:
        pass
    return {"success": True, "reward_coins": reward}
