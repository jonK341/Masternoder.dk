"""
Cross-account sybil correlation for withdrawal risk scoring.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Any, Dict, List, Set


def _base() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _read_json(name: str) -> Any:
    p = os.path.join(_base(), "data", name)
    if not os.path.isfile(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def score_user(user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    addr_to_users: Dict[str, Set[str]] = defaultdict(set)
    withdraw_addrs = _read_json("mn2_withdrawal_addresses.json")
    if isinstance(withdraw_addrs, dict):
        for u, recs in withdraw_addrs.items():
            if isinstance(recs, dict):
                for addr in recs:
                    addr_to_users[str(addr).strip()].add(str(u))

    cluster: Set[str] = {uid}
    user_addrs = withdraw_addrs.get(uid) if isinstance(withdraw_addrs, dict) else {}
    if isinstance(user_addrs, dict):
        for addr in user_addrs:
            cluster |= addr_to_users.get(str(addr).strip(), set())

    deposit_map = _read_json("mn2_user_addresses.json")
    if isinstance(deposit_map, dict):
        addr = deposit_map.get(uid)
        if addr:
            for u, a in deposit_map.items():
                if a == addr:
                    cluster.add(str(u))

    size = len(cluster)
    score = 0.0
    if size >= 4:
        score = 0.9
    elif size == 3:
        score = 0.6
    elif size == 2:
        score = 0.35

    return {
        "user_id": uid,
        "cluster_size": size,
        "cluster_users": sorted(cluster)[:10],
        "sybil_score": round(score, 3),
        "elevated": score >= 0.6,
    }


def ops_clusters(min_score: float = 0.6, limit: int = 50) -> Dict[str, Any]:
    withdraw_addrs = _read_json("mn2_withdrawal_addresses.json")
    users = list(withdraw_addrs.keys()) if isinstance(withdraw_addrs, dict) else []
    hits: List[Dict[str, Any]] = []
    for u in users[:2000]:
        s = score_user(u)
        if s.get("sybil_score", 0) >= min_score:
            hits.append(s)
    hits.sort(key=lambda x: -x.get("sybil_score", 0))
    return {"success": True, "count": len(hits), "clusters": hits[:limit]}
