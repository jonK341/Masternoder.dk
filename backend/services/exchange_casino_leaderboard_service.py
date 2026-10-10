"""Fused weekly Trader + High roller leaderboard (exchange profit + casino MN2 net)."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_CONFIG_PATH = os.path.join(ex._BASE, "data", "exchange_casino_quests.json")
_STATE_PATH = os.path.join(ex._DATA_DIR, "exchange_casino_leaderboard.json")


def _week_key() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"


def _lb_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CONFIG_PATH, {})
    return (cfg.get("leaderboard") or {}) if isinstance(cfg, dict) else {}


def _load() -> Dict[str, Any]:
    data = ex._read_json(_STATE_PATH, {})
    if not isinstance(data, dict):
        data = {}
    if data.get("week") != _week_key():
        data = {"week": _week_key(), "users": {}}
    data.setdefault("users", {})
    return data


def _save(data: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, data)


def record_trader_profit(user_id: str, profit_usd: float) -> None:
    if not _lb_config().get("enabled", True):
        return
    uid = (user_id or "").strip()
    delta = float(profit_usd or 0)
    if not uid or delta <= 0:
        return
    data = _load()
    row = data["users"].setdefault(uid, {"trader_usd": 0.0, "highroller_mn2": 0.0, "rentals": 0})
    row["trader_usd"] = round(float(row.get("trader_usd") or 0) + delta, 6)
    _save(data)


def record_highroller_net(user_id: str, mn2_net: float) -> None:
    if not _lb_config().get("enabled", True):
        return
    uid = (user_id or "").strip()
    if not uid:
        return
    data = _load()
    row = data["users"].setdefault(uid, {"trader_usd": 0.0, "highroller_mn2": 0.0, "rentals": 0})
    row["highroller_mn2"] = round(float(row.get("highroller_mn2") or 0) + float(mn2_net or 0), 8)
    _save(data)


def record_rental_start(user_id: str) -> None:
    if not _lb_config().get("enabled", True):
        return
    uid = (user_id or "").strip()
    if not uid:
        return
    data = _load()
    row = data["users"].setdefault(uid, {"trader_usd": 0.0, "highroller_mn2": 0.0, "rentals": 0})
    row["rentals"] = int(row.get("rentals") or 0) + 1
    _save(data)


def _score(row: Dict[str, Any], cfg: Dict[str, Any]) -> float:
    tw = float(cfg.get("trader_weight") or 10.0)
    hw = float(cfg.get("highroller_weight") or 100.0)
    rb = float(cfg.get("rental_bonus") or 25.0)
    return (
        float(row.get("trader_usd") or 0) * tw
        + float(row.get("highroller_mn2") or 0) * hw
        + int(row.get("rentals") or 0) * rb
    )


def weekly_leaderboard(*, limit: int = 15, user_id: Optional[str] = None) -> Dict[str, Any]:
    cfg = _lb_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "leaderboard_disabled"}
    data = _load()
    ranked: List[Dict[str, Any]] = []
    for uid, row in (data.get("users") or {}).items():
        score = _score(row, cfg)
        if score <= 0:
            continue
        ranked.append({
            "user_id": uid,
            "score": round(score, 2),
            "trader_profit_usd": round(float(row.get("trader_usd") or 0), 4),
            "casino_mn2_net": round(float(row.get("highroller_mn2") or 0), 6),
            "rentals_started": int(row.get("rentals") or 0),
        })
    ranked.sort(key=lambda r: r["score"], reverse=True)
    board = []
    for i, row in enumerate(ranked[: max(1, min(int(limit or 15), 50))], start=1):
        board.append({**row, "rank": i})

    your_rank = None
    if user_id:
        for entry in ranked:
            if entry["user_id"] == user_id.strip():
                your_rank = {**entry, "rank": ranked.index(entry) + 1}
                break

    return {
        "success": True,
        "week": data.get("week"),
        "title": "Trader + High roller",
        "leaderboard": board,
        "your_rank": your_rank,
        "top_rewards_coins": cfg.get("top_rewards_coins") or [200, 100, 50],
    }
