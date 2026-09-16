"""Encoder-driven fulfillment — sync Discord prospects into the customer aggregator."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_FULFILLMENT_FILE = os.path.join(_BASE, "data", "encoder_customer_fulfillment.json")
_LOCK = threading.RLock()


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _config() -> Dict[str, Any]:
    try:
        with open(os.path.join(_BASE, "data", "mn2_config.json"), "r", encoding="utf-8") as f:
            root = json.load(f)
        block = root.get("encoder_customer_fulfillment") if isinstance(root, dict) else {}
        return block if isinstance(block, dict) else {}
    except Exception:
        return {}


def fulfillment_enabled() -> bool:
    return bool(_config().get("enabled", True))


def _load_store() -> Dict[str, Any]:
    if not os.path.isfile(_FULFILLMENT_FILE):
        return {"version": 1, "fulfilled": {}}
    try:
        with open(_FULFILLMENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("fulfilled", {})
            return data
    except Exception:
        pass
    return {"version": 1, "fulfilled": {}}


def _save_store(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_FULFILLMENT_FILE), exist_ok=True)
    tmp = _FULFILLMENT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _FULFILLMENT_FILE)


def is_fulfilled(user_id: str) -> bool:
    uid = str(user_id or "").strip()
    return uid in (_load_store().get("fulfilled") or {})


def fulfillment_record(user_id: str) -> Optional[Dict[str, Any]]:
    uid = str(user_id or "").strip()
    return (_load_store().get("fulfilled") or {}).get(uid)


def _mark_fulfilled(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    with _LOCK:
        store = _load_store()
        fulfilled = store.setdefault("fulfilled", {})
        row = {
            "user_id": uid,
            "fulfilled_at": _iso(),
            **payload,
        }
        fulfilled[uid] = row
        store["last_batch_at"] = _iso()
        _save_store(store)
    return row


def fulfill_single_customer(
    user_id: str,
    *,
    discord_meta: Optional[Dict[str, Any]] = None,
    skip_if_done: bool = True,
) -> Dict[str, Any]:
    """Onboard a Discord prospect into the aggregator via encoder fulfillment."""
    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id_required"}

    if not fulfillment_enabled():
        return {"success": False, "error": "fulfillment_disabled"}

    if skip_if_done and is_fulfilled(uid):
        return {"success": True, "skipped": True, "user_id": uid, "record": fulfillment_record(uid)}

    cfg = _config()
    actions: List[str] = []

    # Ensure points stub exists for discord prospects
    if discord_meta:
        try:
            from backend.services.discord_customer_ingest_service import _ensure_points_stub

            _ensure_points_stub(uid, discord_meta)
            actions.append("points_stub")
        except Exception:
            pass

    # AI agent onboarding for new prospects
    username = str((discord_meta or {}).get("username") or (discord_meta or {}).get("display_name") or uid)
    try:
        from backend.services.ai_user_controller import onboard_new_user

        onboard = onboard_new_user(uid, username=username)
        if onboard.get("success"):
            actions.append("ai_onboard")
    except Exception:
        pass

    # Aggregator MN2 welcome credit
    award_action = str(cfg.get("aggregator_action") or "discord_welcome")
    award_meta = {"source": "encoder_customer_fulfillment", "discord_id": (discord_meta or {}).get("discord_id")}
    try:
        from backend.services.aggregator_mn2_service import award_for_action

        award = award_for_action(uid, award_action, meta=award_meta)
        if award.get("mn2_awarded", 0) > 0:
            actions.append("aggregator_award")
    except Exception:
        award = {"success": False}

    # Promote customer row metadata
    try:
        _promote_customer_row(uid, discord_meta=discord_meta)
        actions.append("customer_promoted")
    except Exception:
        pass

    record = _mark_fulfilled(uid, {
        "actions": actions,
        "discord_id": (discord_meta or {}).get("discord_id"),
        "username": username,
        "aggregator_award": award if isinstance(award, dict) else {},
    })
    return {"success": True, "user_id": uid, "fulfillment": record, "actions": actions}


def _promote_customer_row(user_id: str, *, discord_meta: Optional[Dict[str, Any]] = None) -> None:
    from backend.services.customer_aggregator_service import _POINTS_DIR

    path = os.path.join(_POINTS_DIR, f"{user_id}.json")
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f) or {}
    raw["source"] = "discord_channel"
    raw["fulfilled_via_encoder"] = True
    raw["fulfilled_at"] = _iso()
    if discord_meta:
        raw["discord"] = {
            "discord_id": discord_meta.get("discord_id"),
            "username": discord_meta.get("username"),
            "display_name": discord_meta.get("display_name"),
            "channel_id": discord_meta.get("channel_id"),
        }
    raw["updated_at"] = _iso()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2)


def fulfill_discord_customers_via_encoder(
    *,
    sync_first: bool = True,
    include_guild_members: bool = False,
    message_limit: int = 100,
    limit: int = 50,
    force: bool = False,
) -> Dict[str, Any]:
    """Sync Discord channel, then encoder-fulfill prospects into the aggregator."""
    if not fulfillment_enabled():
        return {"success": False, "error": "fulfillment_disabled"}

    sync_result: Dict[str, Any] = {}
    if sync_first:
        from backend.services.discord_customer_ingest_service import sync_customers_from_channel

        sync_result = sync_customers_from_channel(
            include_guild_members=include_guild_members,
            message_limit=message_limit,
        )
        if not sync_result.get("success"):
            return sync_result

    from backend.services.discord_customer_ingest_service import list_discord_customers

    dlist = list_discord_customers(limit=1000, offset=0)
    customers = dlist.get("customers") or []
    cfg = _config()
    batch_limit = max(1, min(int(limit or cfg.get("batch_limit") or 50), 500))

    results: List[Dict[str, Any]] = []
    fulfilled_count = 0
    skipped_count = 0
    error_count = 0

    for row in customers[:batch_limit]:
        uid = str(row.get("user_id") or "").strip()
        if not uid:
            continue
        if not force and is_fulfilled(uid):
            skipped_count += 1
            results.append({"user_id": uid, "skipped": True})
            continue

        # Create encoder order (free) when encoder orders are enabled
        order_result: Dict[str, Any] = {}
        try:
            from backend.services.encoder_order_service import create_balance_order, encoder_orders_enabled

            if encoder_orders_enabled():
                order_result = create_balance_order(
                    uid,
                    "customer_fulfillment",
                    {"discord_id": row.get("discord_id"), "source": "discord_channel"},
                    auto_fulfill=True,
                )
        except Exception as exc:
            order_result = {"success": False, "error": str(exc)[:120]}

        if order_result.get("success"):
            fulfilled_count += 1
            results.append({
                "user_id": uid,
                "order_id": (order_result.get("order") or {}).get("order_id"),
                "fulfillment": order_result.get("fulfillment"),
            })
            continue

        # Fallback: direct fulfillment without encoder order
        direct = fulfill_single_customer(uid, discord_meta=row, skip_if_done=not force)
        if direct.get("success"):
            fulfilled_count += 1
            results.append({"user_id": uid, "direct": True, "fulfillment": direct.get("fulfillment")})
        else:
            error_count += 1
            results.append({"user_id": uid, "error": direct.get("error") or order_result.get("error")})

    store = _load_store()
    return {
        "success": True,
        "sync": sync_result,
        "fulfilled_count": fulfilled_count,
        "skipped_count": skipped_count,
        "error_count": error_count,
        "total_indexed": dlist.get("total", 0),
        "total_fulfilled_ever": len(store.get("fulfilled") or {}),
        "results_preview": results[:20],
    }


def fulfillment_stats() -> Dict[str, Any]:
    store = _load_store()
    fulfilled = store.get("fulfilled") or {}
    return {
        "success": True,
        "enabled": fulfillment_enabled(),
        "total_fulfilled": len(fulfilled),
        "last_batch_at": store.get("last_batch_at"),
        "config": _config(),
    }
