"""Ledger coin sales — agents/camgirls offer MN2 via PayPal, USDT, USDC."""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SALES_FILE = os.path.join(_BASE, "data", "ledger_coin_sales.json")
_ASSIGNMENT_FILE = os.path.join(_BASE, "data", "ledger_sales_assignments.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_sales() -> Dict[str, Any]:
    if not os.path.isfile(_SALES_FILE):
        return {"version": 1, "offers": [], "updated_at": None}
    try:
        with open(_SALES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("offers", [])
            return data
    except Exception:
        pass
    return {"version": 1, "offers": [], "updated_at": None}


def _save_sales(doc: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_SALES_FILE), exist_ok=True)
    doc["updated_at"] = _iso()
    tmp = _SALES_FILE + ".tmp"
    with _LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        os.replace(tmp, _SALES_FILE)


def _load_assignments() -> Dict[str, Any]:
    if not os.path.isfile(_ASSIGNMENT_FILE):
        return {"version": 1, "round_robin_index": 0, "by_row": {}}
    try:
        with open(_ASSIGNMENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("by_row", {})
            return data
    except Exception:
        pass
    return {"version": 1, "round_robin_index": 0, "by_row": {}}


def _save_assignments(doc: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_ASSIGNMENT_FILE), exist_ok=True)
    tmp = _ASSIGNMENT_FILE + ".tmp"
    with _LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        os.replace(tmp, _ASSIGNMENT_FILE)


def _camgirl_performers() -> List[Dict[str, Any]]:
    path = os.path.join(_BASE, "data", "camgirls_catalog.json")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
        return [p for p in (doc.get("performers") or []) if isinstance(p, dict)]
    except Exception:
        return []


def _assign_camgirl(ledger_row_id: str, performer_id: Optional[str] = None) -> Optional[str]:
    doc = _load_assignments()
    by_row = doc.get("by_row") or {}
    if ledger_row_id in by_row:
        return by_row[ledger_row_id].get("camgirl_id")
    performers = _camgirl_performers()
    if not performers:
        return None
    if performer_id:
        chosen = performer_id
    else:
        idx = int(doc.get("round_robin_index") or 0) % len(performers)
        chosen = str(performers[idx].get("id") or "")
        doc["round_robin_index"] = idx + 1
    agent_id = None
    try:
        from backend.services.camgirls_agents_service import list_agent_models

        agents = list_agent_models() or []
        if agents:
            agent_id = agents[int(doc.get("round_robin_index") or 0) % len(agents)].get("id")
    except Exception:
        pass
    by_row[ledger_row_id] = {
        "camgirl_id": chosen,
        "agent_id": agent_id,
        "assigned_at": _iso(),
    }
    doc["by_row"] = by_row
    _save_assignments(doc)
    return chosen


def get_sales_queue(limit: int = 50) -> Dict[str, Any]:
    from backend.services.discord_fulfillment_ledger_service import get_order_list

    listing = get_order_list()
    orders = listing.get("orders") or []
    assignments = _load_assignments().get("by_row") or {}
    sales_doc = _load_sales()
    pending_offers = {o.get("ledger_row_id"): o for o in sales_doc.get("offers") or [] if o.get("status") == "pending"}

    queue: List[Dict[str, Any]] = []
    for row in orders:
        if row.get("fulfillment_status") == "fulfilled" and not row.get("buyer_signal"):
            continue
        lid = str(row.get("ledger_row_id") or row.get("discord_id") or "")
        if not lid:
            continue
        camgirl_id = _assign_camgirl(lid)
        assign = assignments.get(lid) or _load_assignments().get("by_row", {}).get(lid) or {}
        queue.append(
            {
                "ledger_row_id": lid,
                "ledger_rank": row.get("ledger_rank"),
                "discord_id": row.get("discord_id"),
                "youtube_id": row.get("youtube_id"),
                "facebook_id": row.get("facebook_id"),
                "user_id": row.get("user_id"),
                "display_name": row.get("display_name") or row.get("discord_username"),
                "priority_score": row.get("priority_score"),
                "buyer_score": row.get("buyer_score"),
                "sources": row.get("sources"),
                "mn2_coin_offer_status": row.get("mn2_coin_offer_status"),
                "assigned_camgirl_id": camgirl_id or assign.get("camgirl_id"),
                "assigned_agent_id": assign.get("agent_id"),
                "pending_offer": pending_offers.get(lid),
            }
        )
        if len(queue) >= limit:
            break

    return {"success": True, "total": len(queue), "queue": queue}


def create_offer(
    *,
    ledger_row_id: str,
    mn2_amount: float,
    price_usd: float,
    rail: str = "paypal",
    performer_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    operator: Optional[str] = None,
) -> Dict[str, Any]:
    from backend.services.discord_fulfillment_ledger_service import get_row_by_id

    lid = (ledger_row_id or "").strip()
    if not lid:
        return {"success": False, "error": "ledger_row_id required"}
    row = get_row_by_id(lid)
    if not row:
        return {"success": False, "error": "ledger_row_not_found", "ledger_row_id": lid}

    rail_norm = (rail or "paypal").strip().lower()
    if rail_norm not in ("paypal", "usdt", "usdc"):
        return {"success": False, "error": "invalid_rail", "allowed": ["paypal", "usdt", "usdc"]}
    if mn2_amount <= 0 or price_usd <= 0:
        return {"success": False, "error": "mn2_amount and price_usd must be positive"}

    camgirl_id = performer_id or _assign_camgirl(lid)
    offer_id = f"offer_{uuid.uuid4().hex[:12]}"
    offer = {
        "offer_id": offer_id,
        "ledger_row_id": lid,
        "user_id": row.get("user_id"),
        "discord_id": row.get("discord_id"),
        "mn2_amount": float(mn2_amount),
        "price_usd": float(price_usd),
        "rail": rail_norm,
        "status": "pending",
        "camgirl_id": camgirl_id,
        "agent_id": agent_id,
        "operator": operator,
        "created_at": _iso(),
        "payment_ref": None,
    }
    doc = _load_sales()
    doc.setdefault("offers", []).append(offer)
    _save_sales(doc)
    return {"success": True, "offer": offer}


def fulfill_offer(
    offer_id: str,
    *,
    payment_ref: Optional[str] = None,
    capture: Optional[Dict[str, Any]] = None,
    operator: Optional[str] = None,
) -> Dict[str, Any]:
    doc = _load_sales()
    offers = doc.get("offers") or []
    target = next((o for o in offers if o.get("offer_id") == offer_id), None)
    if not target:
        return {"success": False, "error": "offer_not_found", "offer_id": offer_id}
    if target.get("status") == "fulfilled":
        return {"success": True, "already_fulfilled": True, "offer": target}

    user_id = target.get("user_id")
    discord_id = target.get("discord_id")
    rail = str(target.get("rail") or "paypal")
    mn2_amount = float(target.get("mn2_amount") or 0)
    errors: List[str] = []

    if rail == "paypal" and capture and user_id:
        try:
            from backend.services.crypto_exchange_service import fulfill_paypal_mn2_order

            pack = {
                "id": f"ledger-offer-{offer_id}",
                "price_usd": target.get("price_usd"),
                "mn2_amount": mn2_amount,
            }
            result = fulfill_paypal_mn2_order(user_id, payment_ref or offer_id, capture)
            if not result.get("success"):
                errors.append(result.get("error") or "paypal_fulfill_failed")
        except Exception as exc:
            errors.append(f"paypal: {exc}")
    elif rail in ("usdt", "usdc") and user_id:
        try:
            from backend.services.unified_points_database import unified_points_db

            ref = f"ledger_sale:{offer_id}:{rail}"
            unified_points_db.add_points(
                user_id,
                "mn2_balance",
                mn2_amount,
                source=f"ledger_coin_sale_{rail}",
                metadata={"offer_id": offer_id, "rail": rail, "reference": ref, "operator": operator},
            )
            try:
                from backend.services.mn2_ledger import append_entry

                append_entry(user_id, "deposit", mn2_amount, metadata={"source": f"ledger_sale_{rail}", "offer_id": offer_id})
            except Exception:
                pass
        except Exception as exc:
            errors.append(f"{rail}: {exc}")
    elif user_id and mn2_amount > 0:
        try:
            from backend.services.unified_points_database import unified_points_db

            unified_points_db.add_points(
                user_id,
                "mn2_balance",
                mn2_amount,
                source="ledger_coin_sale",
                metadata={"offer_id": offer_id, "operator": operator},
            )
        except Exception as exc:
            errors.append(str(exc))

    if discord_id and not errors:
        try:
            from backend.services.discord_fulfillment_ledger_service import fulfill_order

            fulfill_order(discord_id, ["coin_pack_offer", "mn2_credit"], operator=operator or "ledger_sales")
        except Exception:
            pass

    if errors:
        return {"success": False, "errors": errors, "offer_id": offer_id}

    target["status"] = "fulfilled"
    target["fulfilled_at"] = _iso()
    target["payment_ref"] = payment_ref
    target["operator"] = operator
    _save_sales(doc)
    return {"success": True, "offer": target, "mn2_credited": mn2_amount}


def list_offers(ledger_row_id: Optional[str] = None) -> Dict[str, Any]:
    doc = _load_sales()
    offers = doc.get("offers") or []
    if ledger_row_id:
        offers = [o for o in offers if o.get("ledger_row_id") == ledger_row_id]
    return {"success": True, "offers": offers, "total": len(offers)}
