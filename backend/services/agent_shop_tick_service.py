"""Agent catalog finish-moves: cheap MN2 shop purchases + activity."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _cheap_coin_items(max_coins: int = 50, limit: int = 8) -> List[Dict[str, Any]]:
    from backend.routes.shop_routes import _get_shop_items

    items = []
    for it in _get_shop_items() or []:
        if not isinstance(it, dict):
            continue
        price = it.get("price")
        if not isinstance(price, (int, float)):
            continue
        if price <= 0 or price > max_coins:
            continue
        iid = (it.get("id") or "").strip()
        if not iid:
            continue
        items.append(it)
    items.sort(key=lambda x: float(x.get("price") or 0))
    return items[:limit]


def _bound_agent_users() -> List[Dict[str, str]]:
    import json
    import os

    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "data", "agent_crypto_wallet_agents.json")
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        agents = raw.get("agents") if isinstance(raw, dict) else raw
        for a in agents or []:
            if not isinstance(a, dict):
                continue
            uid = (a.get("bound_user_id") or a.get("user_id") or "").strip()
            aid = (a.get("id") or "mn2_scout").strip()
            if uid:
                rows.append({"user_id": uid, "agent_id": aid})
    except Exception:
        pass
    return rows


def run_agent_shop_tick(
    *,
    user_ids: Optional[List[str]] = None,
    max_purchases: int = 6,
    max_coins: int = 25,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Finish-move: agents buy the cheapest coin-priced catalog items with in-wallet MN2.
    Idempotent-ish: one purchase per user per tick, cheapest item first.
    """
    from backend.services.shop_mn2_purchase_core import purchase_with_mn2_balance
    from backend.services.agent_db_service import agent_db_service

    bound = _bound_agent_users()
    targets: List[Dict[str, str]] = list(bound)
    if user_ids:
        for uid in user_ids:
            u = str(uid or "").strip()
            if u and not any(t["user_id"] == u for t in targets):
                targets.append({"user_id": u, "agent_id": "mn2_scout"})
    if not targets:
        targets = [{"user_id": "default_user", "agent_id": "mn2_scout"}]

    catalog = _cheap_coin_items(max_coins=max_coins)
    out: Dict[str, Any] = {
        "success": True,
        "purchases": 0,
        "skipped": 0,
        "errors": [],
        "catalog_size": len(catalog),
        "results": [],
        "dry_run": dry_run,
    }
    if not catalog:
        out["skipped"] = len(targets)
        return out

    for i, tgt in enumerate(targets):
        if out["purchases"] >= max_purchases:
            break
        item = catalog[i % len(catalog)]
        iid = item.get("id")
        uid = tgt["user_id"]
        aid = tgt["agent_id"]
        if dry_run:
            out["results"].append({"user_id": uid, "item_id": iid, "dry_run": True})
            out["purchases"] += 1
            continue
        body, status = purchase_with_mn2_balance(uid, iid, 1, agent_id=aid)
        row = {"user_id": uid, "agent_id": aid, "item_id": iid, "http": status, "ok": bool(body.get("success"))}
        if not body.get("success"):
            row["error"] = body.get("error")
            out["errors"].append(f"{uid}:{body.get('error')}")
            out["skipped"] += 1
        else:
            out["purchases"] += 1
            try:
                agent_db_service.record_agent_activity(
                    user_id=uid,
                    agent_id=aid,
                    action="shop_finish_move",
                    skill="shop_purchase",
                    xp_gained=12,
                    metadata={"item_id": iid, "item_name": item.get("name")},
                )
            except Exception:
                pass
        out["results"].append(row)
    return out
