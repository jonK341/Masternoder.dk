"""Unified customer directory — identity, balances, participation across domains."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_POINTS_DIR = os.path.join(_BASE, "logs", "unified_points")
_IDENT_DIR = os.path.join(_BASE, "logs", "user_identifiers")


def _avatar_url(user_id: str) -> str:
    svg = os.path.join(_BASE, "static", "img", "customers", f"{user_id}.svg")
    if os.path.isfile(svg):
        return f"/static/img/customers/{user_id}.svg"
    return f"/static/img/agents/default.svg"


def _load_identifiers(user_id: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if not os.path.isdir(_IDENT_DIR):
        return out
    for name in os.listdir(_IDENT_DIR):
        if not name.endswith(".json"):
            continue
        path = os.path.join(_IDENT_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                row = json.load(f)
            if row.get("user_id") == user_id:
                out[name.replace(".json", "")] = row
        except Exception:
            pass
    return out


def _load_control_index() -> Dict[str, Dict[str, Any]]:
    try:
        from backend.services.ledger_customer_control_service import _load_store

        return dict((_load_store().get("assignments") or {}))
    except Exception:
        return {}


def _control_for_user(
    user_id: str,
    control_index: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    if control_index is not None:
        return control_index.get(user_id)
    try:
        from backend.services.ledger_customer_control_service import get_assignment

        return get_assignment(user_id)
    except Exception:
        return None


def _load_ledger_index(limit: int = 20000) -> Dict[str, Dict[str, Any]]:
    try:
        from backend.services.ledger_customer_aggregator_service import load_ledger_customer_rows

        rows = load_ledger_customer_rows()[: max(1, int(limit or 20000))]
        return {
            str(row.get("user_id")): row
            for row in rows
            if row.get("user_id")
        }
    except Exception:
        return {}


def _ledger_summary_for_user(
    user_id: str,
    ledger_index: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    if ledger_index is not None:
        return ledger_index.get(user_id)
    return _load_ledger_index().get(user_id)


def _discord_index_by_user() -> Dict[str, Dict[str, Any]]:
    try:
        from backend.services.discord_customer_ingest_service import _load_index

        index = _load_index()
        out: Dict[str, Dict[str, Any]] = {}
        for row in (index.get("customers") or {}).values():
            uid = row.get("user_id")
            if uid:
                out[str(uid)] = row
        return out
    except Exception:
        return {}


def _discord_meta_for_user(
    user_id: str,
    discord_index: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    if discord_index is not None:
        return discord_index.get(user_id)
    return _discord_index_by_user().get(user_id)


def _customer_row(
    user_id: str,
    raw: dict,
    *,
    ledger_index: Optional[Dict[str, Dict[str, Any]]] = None,
    control_index: Optional[Dict[str, Dict[str, Any]]] = None,
    discord_index: Optional[Dict[str, Dict[str, Any]]] = None,
    include_identifiers: bool = True,
) -> Dict[str, Any]:
    systems = raw.get("systems") if isinstance(raw.get("systems"), dict) else {}
    discord = raw.get("discord") if isinstance(raw.get("discord"), dict) else _discord_meta_for_user(user_id, discord_index)
    ledger = raw.get("ledger") if isinstance(raw.get("ledger"), dict) else None
    if not ledger:
        ledger = _ledger_summary_for_user(user_id, ledger_index)
    source = raw.get("source") or ("discord_channel" if discord else ("ledger" if ledger else "site"))
    control = _control_for_user(user_id, control_index)
    return {
        "user_id": user_id,
        "level": int(raw.get("level") or 1),
        "xp_total": float(raw.get("xp_total") or raw.get("xp") or 0),
        "coins": float(raw.get("coins") or systems.get("coins") or 0),
        "mn2_balance": float(
            raw.get("mn2_balance")
            or systems.get("mn2_balance")
            or (ledger or {}).get("ledger_net_mn2")
            or 0
        ),
        "last_active": raw.get("updated_at") or raw.get("last_source") or (ledger or {}).get("last_activity"),
        "avatar_url": _avatar_url(user_id),
        "identifiers": _load_identifiers(user_id) if include_identifiers else {},
        "source": source,
        "discord": discord,
        "ledger": ledger,
        "control": control,
    }


def list_customers(
    *,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    q = (search or "").strip().lower()
    src = (source or "").strip().lower()
    control_index = _load_control_index()
    discord_index = _discord_index_by_user() if src in ("", "discord", "discord_channel") else {}
    ledger_index: Dict[str, Dict[str, Any]] = {}
    if src in ("", "ledger"):
        ledger_index = _load_ledger_index()

    if src != "ledger" and os.path.isdir(_POINTS_DIR):
        for name in os.listdir(_POINTS_DIR):
            if not name.endswith(".json"):
                continue
            uid = name[:-5]
            if q and q not in uid.lower():
                continue
            path = os.path.join(_POINTS_DIR, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw = json.load(f) or {}
                row = _customer_row(
                    uid,
                    raw,
                    ledger_index=ledger_index,
                    control_index=control_index,
                    discord_index=discord_index,
                    include_identifiers=False,
                )
                if src and str(row.get("source") or "").lower() != src:
                    continue
                rows.append(row)
            except Exception:
                continue

    if src in ("", "discord", "discord_channel"):
        try:
            from backend.services.discord_customer_ingest_service import list_discord_customers

            dlist = list_discord_customers(limit=1000, offset=0).get("customers") or []
            seen = {r.get("user_id") for r in rows}
            for drow in dlist:
                uid = drow.get("user_id")
                if not uid or uid in seen:
                    continue
                if q and q not in str(uid).lower() and q not in str(drow.get("username") or "").lower():
                    continue
                rows.append({
                    "user_id": uid,
                    "level": 1,
                    "xp_total": 0,
                    "coins": 0,
                    "mn2_balance": 0,
                    "last_active": drow.get("last_seen_at"),
                    "avatar_url": _avatar_url(uid),
                    "identifiers": _load_identifiers(uid),
                    "source": "discord_channel",
                    "discord": drow,
                    "ledger": None,
                    "control": _control_for_user(uid, control_index),
                })
                seen.add(uid)
        except Exception:
            pass

    if src in ("", "ledger"):
        seen = {r.get("user_id") for r in rows}
        for uid, lrow in ledger_index.items():
            if uid in seen:
                continue
            if q and q not in str(uid).lower():
                continue
            rows.append({
                "user_id": uid,
                "level": 1,
                "xp_total": 0,
                "coins": 0,
                "mn2_balance": float(lrow.get("ledger_net_mn2") or 0),
                "last_active": lrow.get("last_activity"),
                "avatar_url": _avatar_url(uid),
                "identifiers": _load_identifiers(uid),
                "source": "ledger",
                "discord": None,
                "ledger": lrow,
                "control": _control_for_user(uid, control_index),
            })
            seen.add(uid)

    rows.sort(key=lambda r: str(r.get("last_active") or ""), reverse=True)
    total = len(rows)
    page = rows[offset: offset + limit]
    return {"success": True, "customers": page, "total": total, "limit": limit, "offset": offset}


def get_customer(user_id: str) -> Dict[str, Any]:
    path = os.path.join(_POINTS_DIR, f"{user_id}.json")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f) or {}
        customer = _customer_row(user_id, raw)
    else:
        discord = _discord_meta_for_user(user_id)
        ledger = _ledger_summary_for_user(user_id)
        if not discord and not ledger:
            return {"success": False, "error": "not_found"}
        customer = {
            "user_id": user_id,
            "level": 1,
            "xp_total": 0,
            "coins": 0,
            "mn2_balance": float((ledger or {}).get("ledger_net_mn2") or 0),
            "last_active": (discord or {}).get("last_seen_at") or (ledger or {}).get("last_activity"),
            "avatar_url": _avatar_url(user_id),
            "identifiers": _load_identifiers(user_id),
            "source": "discord_channel" if discord else "ledger",
            "discord": discord,
            "ledger": ledger,
            "control": _control_for_user(user_id),
        }

    control = {}
    fulfillment = None
    try:
        from backend.services.ledger_customer_control_service import get_assignment

        control = get_assignment(user_id) or {}
    except Exception:
        pass
    try:
        from backend.services.encoder_customer_fulfillment_service import fulfillment_record

        fulfillment = fulfillment_record(user_id)
    except Exception:
        pass

    return {
        "success": True,
        "customer": customer,
        "control": control,
        "fulfillment": fulfillment,
    }


def stats() -> Dict[str, Any]:
    """Fast stats — avoid scanning the full customer directory."""
    points_count = 0
    with_mn2 = 0
    if os.path.isdir(_POINTS_DIR):
        for name in os.listdir(_POINTS_DIR):
            if not name.endswith(".json"):
                continue
            points_count += 1
            if with_mn2 < 250:
                try:
                    with open(os.path.join(_POINTS_DIR, name), "r", encoding="utf-8") as f:
                        raw = json.load(f) or {}
                    bal = float(raw.get("mn2_balance") or (raw.get("systems") or {}).get("mn2_balance") or 0)
                    if bal > 0:
                        with_mn2 += 1
                except Exception:
                    pass

    discord_stats: Dict[str, Any] = {}
    try:
        from backend.services.discord_customer_ingest_service import discord_customer_stats

        discord_stats = discord_customer_stats()
    except Exception:
        discord_stats = {}

    fulfillment_stats: Dict[str, Any] = {}
    try:
        from backend.services.encoder_customer_fulfillment_service import fulfillment_stats as enc_stats

        fulfillment_stats = enc_stats()
    except Exception:
        fulfillment_stats = {}

    discord_total = int(discord_stats.get("total") or 0)
    ledger_total = 0
    try:
        from backend.services.ledger_customer_aggregator_service import ledger_customer_index_meta

        ledger_total = int(ledger_customer_index_meta().get("total") or 0)
    except Exception:
        pass

    control_stats: Dict[str, Any] = {}
    try:
        from backend.services.ledger_customer_control_service import control_stats as ctrl_stats

        control_stats = ctrl_stats()
    except Exception:
        pass

    total = max(points_count, discord_total, ledger_total)
    return {
        "success": True,
        "total": total,
        "points_files": points_count,
        "active_today": int(discord_stats.get("total") or 0),
        "with_mn2": with_mn2,
        "discord": discord_stats,
        "discord_sourced": discord_total,
        "ledger_total": ledger_total,
        "control": control_stats,
        "fulfillment": fulfillment_stats,
    }
