"""
Cross-instance casino hub controller — global leaderboards and network stats.

Today this site is the sole hub member (`masternoder-main`). The design accepts
future peer instances via `data/casino_hub_config.json` so leaderboards and
social identity can merge without changing route contracts.

Unified auth: `user_id` is the canonical key across instances (same as
`unified_points_database` / account resolution). Remote peers are optional.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_HUB_PATH = os.path.join(_ROOT, "data", "casino_hub_config.json")
_CASINO_CONFIG_PATH = os.path.join(_ROOT, "data", "casino_config.json")
_NETWORK_LABEL = "MasterNoder Network"


def _load_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def get_hub_config() -> Dict[str, Any]:
    """Merged hub config: dedicated file overrides casino_config.global_sync."""
    hub = _load_json(_HUB_PATH)
    casino = _load_json(_CASINO_CONFIG_PATH)
    sync = casino.get("global_sync") if isinstance(casino.get("global_sync"), dict) else {}
    merged = {
        "global_sync": bool(sync.get("enabled", hub.get("global_sync", True))),
        "hub_id": str(hub.get("hub_id") or sync.get("hub_id") or "masternoder-main"),
        "network_label": str(hub.get("network_label") or sync.get("network_label") or _NETWORK_LABEL),
        "instances": [],
        "peers": [],
    }
    instances = hub.get("instances") if isinstance(hub.get("instances"), list) else []
    if not instances:
        instances = [{
            "instance_id": merged["hub_id"],
            "label": "masternoder.dk",
            "api_base": os.environ.get("BASE_URL", "https://masternoder.dk").rstrip("/"),
            "is_local": True,
        }]
    merged["instances"] = [i for i in instances if isinstance(i, dict)]
    peers = hub.get("peers") if isinstance(hub.get("peers"), list) else []
    merged["peers"] = [p for p in peers if isinstance(p, dict)]
    return merged


def _format_net(net: float, currency: str) -> float | int:
    if currency == "mn2":
        return round(net, 8)
    if currency == "usd":
        return round(net, 2)
    return int(net)


def _leaderboard_rows(
    agg: Dict[str, Dict[str, float]],
    *,
    limit: int,
    currency: str,
    user_id: Optional[str],
) -> Dict[str, Any]:
    ranked = sorted(agg.items(), key=lambda item: (item[1]["net"], item[1]["wins"]), reverse=True)

    def _row(uid: str, stats: Dict[str, float], rank: int) -> Dict[str, Any]:
        bets = int(stats["bets"])
        wins = int(stats["wins"])
        wagered = float(stats["wagered"])
        net = float(stats["net"])
        win_rate = round(100.0 * wins / bets, 1) if bets else 0.0
        roi = round(100.0 * net / wagered, 1) if wagered else 0.0
        return {
            "rank": rank,
            "user_id": uid,
            "net": _format_net(net, currency),
            "bets": bets,
            "wins": wins,
            "wagered": _format_net(wagered, currency),
            "win_rate": win_rate,
            "roi": roi,
            "currency": currency,
        }

    leaderboard = [_row(uid, stats, rank) for rank, (uid, stats) in enumerate(ranked[:limit], start=1)]
    your_rank = None
    if user_id:
        for rank, (uid, stats) in enumerate(ranked, start=1):
            if uid == user_id:
                your_rank = _row(uid, stats, rank)
                if ranked:
                    first_net = float(ranked[0][1]["net"])
                    your_rank["gap_to_first"] = _format_net(max(0.0, first_net - float(stats["net"])), currency)
                break

    cfg = get_hub_config()
    return {
        "success": True,
        "scope": "global",
        "hub_id": cfg["hub_id"],
        "network_label": cfg["network_label"],
        "instance_count": len(cfg["instances"]) + len(cfg["peers"]),
        "leaderboard": leaderboard,
        "your_rank": your_rank,
    }


def _local_aggregate(period: str, currency: str) -> Dict[str, Dict[str, float]]:
    from backend.services import casino_ledger

    rows = casino_ledger.leaderboard_aggregate(period=period, currency=currency)
    if rows:
        return rows

    # JSONL fallback when DB mirror is empty (tests / fresh installs).
    from backend.services import casino_service
    from collections import defaultdict

    agg: Dict[str, Dict[str, float]] = defaultdict(lambda: {"net": 0.0, "bets": 0, "wins": 0, "wagered": 0.0})
    path = casino_service._ledger_path()
    if not os.path.isfile(path):
        return {}
    currency = casino_service._normalize_currency(currency)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict) or not row.get("user_id"):
                    continue
                if casino_service._normalize_currency(row.get("currency") or "coins") != currency:
                    continue
                if row.get("exclude_leaderboard"):
                    continue
                if not casino_service._row_in_period(row, period):
                    continue
                uid = str(row["user_id"])
                agg[uid]["net"] += float(row.get("net") or 0)
                agg[uid]["bets"] += 1
                agg[uid]["wagered"] += float(row.get("bet") or 0)
                if row.get("outcome") == "win":
                    agg[uid]["wins"] += 1
    except OSError:
        pass
    return dict(agg)


def _merge_peer_leaderboards(
    local: Dict[str, Dict[str, float]],
    peers: List[Dict[str, Any]],
    period: str,
    currency: str,
) -> Dict[str, Dict[str, float]]:
    """Future: fetch peer hub APIs and merge by user_id. Stub returns local only."""
    merged = {uid: dict(stats) for uid, stats in local.items()}
    _ = (peers, period, currency)  # reserved for multi-site rollout
    return merged


def get_global_leaderboard(
    period: str = "today",
    limit: int = 25,
    currency: str = "coins",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    cfg = get_hub_config()
    if not cfg.get("global_sync"):
        return {"success": False, "error": "Global sync disabled", "code": "GLOBAL_SYNC_OFF"}

    safe_limit = max(1, min(int(limit or 25), 50))
    from backend.services import casino_service

    currency = casino_service._normalize_currency(currency)
    local = _local_aggregate(period, currency)
    merged = _merge_peer_leaderboards(local, cfg.get("peers") or [], period, currency)
    out = _leaderboard_rows(merged, limit=safe_limit, currency=currency, user_id=user_id)
    out["period"] = period
    return out


def get_global_stats() -> Dict[str, Any]:
    """Site-wide totals across currency rails (local instance; peers stubbed)."""
    import sqlite3

    cfg = get_hub_config()
    log_dir = os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(_ROOT, "logs")
    db_path = os.path.join(log_dir, "casino_ledger.db")
    by_currency: Dict[str, Dict[str, Any]] = {}
    totals = {"bets": 0, "unique_players": 0, "total_wagered": 0.0, "total_payout": 0.0, "house_edge_profit": 0.0}

    if os.path.isfile(db_path):
        try:
            conn = sqlite3.connect(db_path, timeout=3.0)
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                """
                SELECT currency,
                       COUNT(*) AS bets,
                       COUNT(DISTINCT user_id) AS unique_players,
                       SUM(bet) AS wagered,
                       SUM(payout) AS payout,
                       SUM(bet) - SUM(payout) AS house_edge
                FROM casino_bets
                WHERE exclude_leaderboard = 0
                GROUP BY currency
                """
            )
            for row in cur.fetchall():
                c = str(row["currency"] or "coins")
                wagered = float(row["wagered"] or 0)
                payout = float(row["payout"] or 0)
                house = float(row["house_edge"] or 0)
                by_currency[c] = {
                    "bets": int(row["bets"] or 0),
                    "unique_players": int(row["unique_players"] or 0),
                    "total_wagered": round(wagered, 8 if c == "mn2" else 2),
                    "total_payout": round(payout, 8 if c == "mn2" else 2),
                    "house_edge_profit": round(house, 8 if c == "mn2" else 2),
                }
                totals["bets"] += int(row["bets"] or 0)
                totals["unique_players"] += int(row["unique_players"] or 0)
                totals["total_wagered"] += wagered
                totals["total_payout"] += payout
                totals["house_edge_profit"] += house
            conn.close()
        except Exception:
            pass

    return {
        "success": True,
        "hub_id": cfg["hub_id"],
        "network_label": cfg["network_label"],
        "global_sync": bool(cfg.get("global_sync")),
        "instances": cfg.get("instances") or [],
        "peer_count": len(cfg.get("peers") or []),
        "by_currency": by_currency,
        "totals": {
            "bets": totals["bets"],
            "unique_players": totals["unique_players"],
            "total_wagered": round(totals["total_wagered"], 4),
            "total_payout": round(totals["total_payout"], 4),
            "house_edge_profit": round(totals["house_edge_profit"], 4),
        },
    }
