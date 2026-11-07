"""Rent pre-provisioned platform masternodes (inventory pool) for a flat monthly USD price."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

INVENTORY_HOST_PREFIX = "platform-mn"
PRODUCT_INVENTORY_LEASE = "masternode_inventory_lease"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime] = None) -> str:
    return (dt or _now()).isoformat().replace("+00:00", "Z")


def get_rental_config() -> Dict[str, Any]:
    from backend.services.mn2_masternode_service import get_config

    cfg = get_config()
    rental = cfg.get("rental") if isinstance(cfg.get("rental"), dict) else {}
    pp = cfg.get("paypal") if isinstance(cfg.get("paypal"), dict) else {}
    monthly = float(rental.get("price_usd_monthly") or pp.get("price_usd_per_slot") or 5.0)
    period = int(rental.get("billing_period_days") or cfg.get("min_hosting_term_days") or 30)
    return {
        "enabled": bool(rental.get("enabled", True) and cfg.get("enabled", True)),
        "price_usd_monthly": monthly,
        "billing_period_days": period,
        "currency": (pp.get("currency") or "USD").upper(),
        "billing_label": rental.get("billing_label") or "MN2 Masternode lease (30 days)",
        "max_slots_per_order": int(rental.get("max_slots_per_order") or pp.get("max_slots_per_order") or 5),
        "quote_ttl_seconds": int(rental.get("quote_ttl_seconds") or pp.get("quote_ttl_seconds") or 900),
        "collateral_mn2": float(cfg.get("collateral_mn2") or 5000),
        "inventory_prefix": str(rental.get("inventory_host_prefix") or INVENTORY_HOST_PREFIX),
        "model": "pre_provisioned",
        "description": (
            rental.get("description")
            or "Lease a pre-enabled platform masternode — when your node earns a masternode payout, "
            "we credit your in-app MN2 balance (tracked from on-chain lastpaid)."
        ),
    }


def _is_inventory_host(host: Dict[str, Any], *, prefix: str) -> bool:
    if not isinstance(host, dict):
        return False
    hid = str(host.get("id") or "").strip()
    if not hid.startswith(prefix):
        return False
    if str(host.get("owner_user_id") or "").strip():
        return False
    st = (host.get("status") or "").lower()
    if st == "active":
        return True
    if st == "provisioning" and host.get("collateral_txid"):
        return True
    if st in ("queued", "planned"):
        return True
    return False


def list_rental_inventory(*, limit: int = 500) -> Dict[str, Any]:
    """Hosts in the platform pool that are not assigned to a renter yet."""
    from backend.services.mn2_masternode_service import list_hosts

    rcfg = get_rental_config()
    prefix = rcfg["inventory_prefix"]
    cap = max(1, min(int(limit or 500), 2000))
    rows = list_hosts(include_internal=False)
    inventory: List[Dict[str, Any]] = []
    for h in rows:
        if not _is_inventory_host(h, prefix=prefix):
            continue
        inventory.append(
            {
                "host_id": h.get("id"),
                "status": h.get("status"),
                "label": h.get("label"),
                "collateral_txid": h.get("collateral_txid"),
                "collateral_vout": h.get("collateral_vout"),
                "broadcast_address": h.get("broadcast_address"),
                "updated_at": h.get("updated_at"),
            }
        )
        if len(inventory) >= cap:
            break
    active = sum(1 for x in inventory if (x.get("status") or "").lower() == "active")
    ready = sum(
        1
        for x in inventory
        if (x.get("status") or "").lower() == "active" or x.get("collateral_txid")
    )
    return {
        "success": True,
        "inventory_count": len(inventory),
        "active_count": active,
        "assignable_count": ready,
        "hosts": inventory,
        "pricing": get_rental_config(),
    }


def rental_catalog() -> Dict[str, Any]:
    """Public storefront payload for the lease / rent flow."""
    from backend.services import mn2_masternode_service as mn

    inv = list_rental_inventory(limit=500)
    st = mn.get_service_status()
    rcfg = get_rental_config()
    price = float(rcfg["price_usd_monthly"])
    return {
        "success": True,
        "enabled": rcfg["enabled"],
        "product": PRODUCT_INVENTORY_LEASE,
        "model": rcfg["model"],
        "price_usd_monthly": price,
        "billing_period_days": rcfg["billing_period_days"],
        "currency": rcfg["currency"],
        "description": rcfg["description"],
        "collateral_mn2": rcfg["collateral_mn2"],
        "inventory_available": int(inv.get("assignable_count") or 0),
        "inventory_active_on_chain": int(inv.get("active_count") or 0),
        "max_slots_per_order": rcfg["max_slots_per_order"],
        "legacy_checkout": {
            "slots_available": st.get("slots_available"),
            "checkout_open": st.get("checkout_open"),
            "note": "Legacy checkout provisions a fresh host when collateral is free.",
        },
        "checkout_paths": {
            "quote": "POST /api/mn2/masternode/rentals/quote",
            "paypal_order": "POST /api/mn2/masternode/rentals/order",
            "capture": "POST /api/mn2/masternode/checkout/capture",
            "pay_coins": "POST /api/mn2/masternode/checkout/pay-coins",
            "pay_mn2": "POST /api/mn2/masternode/checkout/pay-mn2",
            "subscribe": "POST /api/mn2/masternode/rentals/subscribe",
            "subscription_info": "GET /api/mn2/masternode/hosting/subscription",
        },
    }


def create_rental_quote(slots: int, user_id: str) -> Dict[str, Any]:
    """Quote leasing N inventory hosts (same order store as PayPal hosting checkout)."""
    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "Could not identify your account", "code": "auth_required"}

    rcfg = get_rental_config()
    if not rcfg.get("enabled"):
        return {"success": False, "error": "Masternode rental is disabled"}

    try:
        slots = int(slots or 1)
    except (TypeError, ValueError):
        return {"success": False, "error": "slots must be a number"}
    if slots < 1:
        return {"success": False, "error": "At least 1 slot required"}
    if slots > int(rcfg["max_slots_per_order"]):
        return {"success": False, "error": f"Maximum {rcfg['max_slots_per_order']} slots per order"}

    inv = list_rental_inventory(limit=500)
    avail = int(inv.get("assignable_count") or 0)
    if avail < slots:
        return {
            "success": False,
            "error": f"Only {avail} pre-provisioned masternode(s) available to lease (need {slots}).",
            "code": "inventory_exhausted",
            "inventory_available": avail,
        }

    from backend.services.mn2_masternode_hosting_service import (
        _audit,
        _data_path,
        _iso,
        _load_orders,
        _now,
        _save_orders,
        pricing_for_slots,
    )

    price = float(rcfg["price_usd_monthly"])
    usd_total = round(price * slots, 2)
    shop_prices = pricing_for_slots(slots)
    # Override USD pricing to rental monthly price while keeping coin/MN2 rails derived.
    shop_prices["usd_per_slot"] = price
    shop_prices["usd_total"] = usd_total

    quote_id = "mnr_" + uuid.uuid4().hex[:16]
    expires_at = _iso(_now() + timedelta(seconds=int(rcfg["quote_ttl_seconds"])))

    from backend.services.mn2_masternode_hosting_service import _LOCK

    with _LOCK:
        orders = _load_orders()
        orders[quote_id] = {
            "order_id": quote_id,
            "user_id": uid,
            "slots": slots,
            "product": PRODUCT_INVENTORY_LEASE,
            "usd_per_slot": price,
            "usd_total": usd_total,
            "coins_per_slot": shop_prices["coins_per_slot"],
            "coins_total": shop_prices["coins_total"],
            "mn2_total": shop_prices["mn2_total"],
            "currency": rcfg["currency"],
            "status": "quoted",
            "payment_method": None,
            "payment_ref": None,
            "paypal_order_id": None,
            "paypal_capture_id": None,
            "host_ids": [],
            "created_at": _iso(),
            "expires_at": expires_at,
            "billing_period_days": int(rcfg["billing_period_days"]),
        }
        _save_orders(orders)
    _audit(quote_id, "rental_quoted", {"slots": slots, "usd_total": usd_total, "product": PRODUCT_INVENTORY_LEASE})

    return {
        "success": True,
        "quote_id": quote_id,
        "product": PRODUCT_INVENTORY_LEASE,
        "slots": slots,
        "usd_per_slot": price,
        "usd_total": usd_total,
        "billing_period_days": rcfg["billing_period_days"],
        "coins_per_slot": shop_prices["coins_per_slot"],
        "coins_total": shop_prices["coins_total"],
        "mn2_total": shop_prices["mn2_total"],
        "payment_rails": shop_prices["payment_rails"],
        "currency": rcfg["currency"],
        "expires_at": expires_at,
        "inventory_reserved_note": "Payment assigns an on-chain-enabled platform node to your account.",
    }


def assign_rental_hosts(user_id: str, slots: int, order_id: str) -> Dict[str, Any]:
    """After payment: attach inventory hosts to the renter (no new collateral send)."""
    uid = str(user_id or "").strip()
    slots = max(1, int(slots or 1))
    inv = list_rental_inventory(limit=500)
    hosts = inv.get("hosts") or []
    # Prefer already-active nodes, then confirming inventory.
    ranked = sorted(
        hosts,
        key=lambda h: (
            0 if (h.get("status") or "").lower() == "active" else 1,
            str(h.get("host_id") or ""),
        ),
    )
    from backend.services.mn2_masternode_service import register_host

    assigned: List[str] = []
    period_days = int(get_rental_config().get("billing_period_days") or 30)
    lease_until = _iso(_now() + timedelta(days=period_days))
    for row in ranked:
        if len(assigned) >= slots:
            break
        hid = str(row.get("host_id") or "").strip()
        if not hid:
            continue
        label = f"Leased MN · {uid[:12]}"
        res = register_host(
            {
                "id": hid,
                "label": label,
                "status": row.get("status") or "active",
                "owner_user_id": uid,
                "collateral_txid": row.get("collateral_txid"),
                "collateral_vout": row.get("collateral_vout"),
                "broadcast_address": row.get("broadcast_address"),
                "notes": f"Lease {order_id[:16]} until {lease_until}",
            }
        )
        if res.get("success"):
            assigned.append(hid)
            try:
                from backend.services.mn2_masternode_hosting_rewards_service import seed_renter_reward_baseline

                seed_renter_reward_baseline(hid)
            except Exception:
                pass
    if len(assigned) < slots:
        return {
            "success": False,
            "error": f"Only assigned {len(assigned)}/{slots} inventory host(s)",
            "host_ids": assigned,
        }
    return {
        "success": True,
        "host_ids": assigned,
        "lease_until": lease_until,
        "message": f"{len(assigned)} masternode(s) assigned — already on the platform fleet.",
    }


def create_rental_subscription(
    user_id: str,
    *,
    return_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
    plan_id: Optional[str] = None,
) -> Dict[str, Any]:
    """PayPal billing subscription for recurring masternode lease (~$5/mo)."""
    uid = str(user_id or "").strip()
    if not uid or uid.lower() in ("default_user", "anon"):
        return {"success": False, "error": "ACCOUNT_REQUIRED", "code": "auth_required"}

    rcfg = get_rental_config()
    if not rcfg.get("enabled"):
        return {"success": False, "error": "Masternode rental is disabled"}

    inv = list_rental_inventory(limit=500)
    if int(inv.get("assignable_count") or 0) < 1:
        return {
            "success": False,
            "error": "No pre-enabled masternodes available to lease right now.",
            "code": "inventory_exhausted",
        }

    from backend.services.monetization_config_service import (
        get_subscription_plan,
        resolve_subscription_plan_id,
        subscription_plan_is_subscribable,
    )

    cfg = __import__("backend.services.mn2_masternode_service", fromlist=["get_config"]).get_config()
    monthly = cfg.get("paypal_monthly") if isinstance(cfg.get("paypal_monthly"), dict) else {}
    plan = (plan_id or monthly.get("subscription_plan_key") or "P-PLACEHOLDER-MN-HOST").strip()
    if not subscription_plan_is_subscribable(plan):
        return {
            "success": False,
            "error": "plan_not_live",
            "message": "Set a live PayPal billing plan id for MN2 hosting (P-PLACEHOLDER-MN-HOST).",
            "plan_id": plan,
        }
    plan = resolve_subscription_plan_id(plan)
    pinfo = get_subscription_plan(plan)
    if not pinfo:
        return {"success": False, "error": "unknown_plan_id", "plan_id": plan}

    import os
    import urllib.parse

    from backend.services.paypal_service import create_billing_subscription

    base = (os.environ.get("BASE_URL") or "").rstrip("/")
    if not return_url:
        if not base:
            return {"success": False, "error": "return_url required (or set BASE_URL on server)"}
        q = urllib.parse.urlencode({
            "paypal_subscription": "success",
            "plan_id": plan,
            "user_id": uid,
            "product": PRODUCT_INVENTORY_LEASE,
        })
        return_url = f"{base}/hosting/?{q}"
    if not cancel_url:
        if not base:
            return {"success": False, "error": "cancel_url required (or set BASE_URL on server)"}
        cancel_url = f"{base}/hosting/?paypal_subscription=cancel&plan_id={urllib.parse.quote(plan, safe='')}"

    result = create_billing_subscription(
        plan_id=plan,
        return_url=return_url,
        cancel_url=cancel_url,
        custom_id=uid,
    )
    if not result.get("success"):
        return result
    return {
        "success": True,
        "plan_id": plan,
        "plan_label": pinfo.get("label"),
        "price_usd_monthly": pinfo.get("price_usd_monthly") or rcfg.get("price_usd_monthly"),
        "approve_url": result.get("approve_url"),
        "subscription_id": result.get("subscription_id"),
        "product": PRODUCT_INVENTORY_LEASE,
    }


def ops_generate_enabled_masternode(*, host_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Ops: move one platform inventory host toward ENABLED (provision_host).

    If ``host_id`` is omitted, picks the next unassigned ``platform-mn-*`` row.
    """
    from backend.services import mn2_masternode_service as mn

    rcfg = get_rental_config()
    prefix = rcfg["inventory_prefix"]
    if host_id:
        hid = str(host_id).strip()
    else:
        hid = ""
        for h in mn.list_hosts(include_internal=True):
            if not isinstance(h, dict):
                continue
            if not str(h.get("id") or "").startswith(prefix):
                continue
            if h.get("owner_user_id"):
                continue
            st = (h.get("status") or "").lower()
            if st in ("queued", "planned", "provisioning"):
                hid = str(h["id"])
                break
        if not hid:
            return {"success": False, "error": "No platform inventory host pending provision"}

    out = mn.provision_host(hid, skip_explorer=True)
    return {"success": bool(out.get("success")), "host_id": hid, "provision": out}
