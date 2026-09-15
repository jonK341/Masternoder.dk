"""
Fan-out PayPal Checkout / Capture webhooks and finish APPROVED orders.

PayPal does not pay the merchant until an Orders v2 CAPTURE intent is captured.
CHECKOUT.ORDER.APPROVED must capture immediately; a sweeper finishes stored pending
orders when the browser return URL never called /capture.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

_ORDER_EVENTS = {
    "CHECKOUT.ORDER.APPROVED",
    "CHECKOUT.ORDER.COMPLETED",
    "PAYMENT.CAPTURE.COMPLETED",
    "PAYMENT.CAPTURE.PENDING",
    "PAYMENT.CAPTURE.DENIED",
    "PAYMENT.CAPTURE.REFUNDED",
    "PAYMENT.CAPTURE.REVERSED",
}


def is_order_event(event_type: str) -> bool:
    return str(event_type or "").strip().upper() in _ORDER_EVENTS


def _order_id_from_event(event: Dict[str, Any]) -> str:
    resource = event.get("resource") if isinstance(event.get("resource"), dict) else {}
    related = ((resource.get("supplementary_data") or {}).get("related_ids") or {})
    if not isinstance(related, dict):
        related = {}
    for candidate in (
        related.get("order_id"),
        resource.get("id") if str(event.get("event_type") or "").upper().startswith("CHECKOUT.ORDER.") else None,
        resource.get("custom_id"),
    ):
        val = str(candidate or "").strip()
        if val:
            return val
    return ""


def dispatch_order_webhook(event: Dict[str, Any], signature_ok: bool) -> Dict[str, Any]:
    """Send checkout/capture events to every PayPal rail. Signature already verified upstream."""
    event_type = str((event or {}).get("event_type") or "").upper()
    dispatched: Dict[str, Any] = {}

    handlers = (
        ("hosting", "backend.services.mn2_masternode_hosting_service"),
        ("onramp", "backend.services.mn2_onramp_service"),
        ("p2p", "backend.services.mn2_p2p_service"),
        ("camgirls", "backend.services.camgirls_paypal_service"),
    )
    for name, mod_name in handlers:
        try:
            mod = __import__(mod_name, fromlist=["handle_webhook"])
            dispatched[name] = mod.handle_webhook(event or {}, signature_ok)
        except Exception as exc:
            dispatched[name] = {"success": False, "error": str(exc)}

    shop_out = _finish_shop_from_event(event or {}, event_type)
    if shop_out:
        dispatched["shop"] = shop_out

    return {"success": True, "dispatched": dispatched, "event_type": event_type}


def _finish_shop_from_event(event: Dict[str, Any], event_type: str) -> Optional[Dict[str, Any]]:
    oid = _order_id_from_event(event)
    if not oid:
        return None
    try:
        from backend.services.paypal_service import get_pending_shop_order
    except Exception:
        return None
    pending = get_pending_shop_order(oid)
    if not pending:
        return {"success": True, "ignored": True, "reason": "no_shop_pending"}
    if str(pending.get("status") or "").lower() in ("captured", "fulfilled"):
        return {"success": True, "already_fulfilled": True, "order_id": oid}
    if event_type in ("CHECKOUT.ORDER.APPROVED", "CHECKOUT.ORDER.COMPLETED", "PAYMENT.CAPTURE.COMPLETED"):
        return _fulfill_shop_job({
            "rail": "shop",
            "local_id": oid,
            "paypal_order_id": oid,
            "user_id": pending.get("user_id"),
            "item_id": pending.get("item_id"),
            "item_name": pending.get("item_name"),
        })
    return None


def collect_pending_paypal_jobs(extra_order_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    seen = set()

    def _add(job: Dict[str, Any]) -> None:
        ppid = str(job.get("paypal_order_id") or "").strip()
        if not ppid or ppid in seen:
            return
        seen.add(ppid)
        jobs.append(job)

    try:
        from backend.services.paypal_service import list_pending_shop_orders

        for row in list_pending_shop_orders():
            _add({
                "rail": "shop",
                "local_id": row.get("order_id"),
                "paypal_order_id": row.get("order_id"),
                "user_id": row.get("user_id"),
                "item_id": row.get("item_id"),
                "item_name": row.get("item_name"),
            })
    except Exception:
        pass

    for spec in (
        ("backend.services.mn2_masternode_hosting_service", "list_pending_paypal_payments"),
        ("backend.services.mn2_onramp_service", "list_pending_paypal_payments"),
        ("backend.services.mn2_p2p_service", "list_pending_paypal_payments"),
        ("backend.services.camgirls_paypal_service", "list_pending_paypal_payments"),
        ("backend.services.casino_service", "list_pending_paypal_deposits"),
    ):
        try:
            mod = __import__(spec[0], fromlist=[spec[1]])
            for job in getattr(mod, spec[1])() or []:
                if isinstance(job, dict):
                    _add(job)
        except Exception:
            pass

    try:
        from backend.services.exchange_user_controller_service import _PAYPAL_ORDERS
        from backend.services import crypto_exchange_service as ex

        rows = ex._read_json(_PAYPAL_ORDERS, {"pending": {}, "captured": {}})
        for oid, row in (rows.get("pending") or {}).items():
            if isinstance(row, dict):
                _add({
                    "rail": "exchange_controller",
                    "local_id": oid,
                    "paypal_order_id": str(row.get("order_id") or oid),
                    "user_id": row.get("user_id"),
                })
    except Exception:
        pass

    for raw in extra_order_ids or []:
        oid = str(raw or "").strip()
        if oid and oid not in seen:
            _add({"rail": "shop", "local_id": oid, "paypal_order_id": oid, "user_id": "", "item_id": ""})

    return jobs


def _fulfill_shop_job(job: Dict[str, Any]) -> Dict[str, Any]:
    from backend.services.paypal_service import finish_checkout_order, get_pending_shop_order

    oid = str(job.get("paypal_order_id") or "").strip()
    cap = finish_checkout_order(oid)
    if not cap.get("success"):
        return {**job, **cap}
    pending = get_pending_shop_order(oid) or {}
    user_id = str(job.get("user_id") or pending.get("user_id") or "").strip()
    item_id = str(job.get("item_id") or pending.get("item_id") or "").strip()
    item_name = str(job.get("item_name") or pending.get("item_name") or "").strip()
    try:
        from backend.routes.paypal_routes import fulfill_captured_shop_payment

        ful = fulfill_captured_shop_payment(
            order_id=oid,
            user_id=user_id,
            item_id=item_id,
            item_name=item_name,
            capture=cap,
        )
    except Exception as exc:
        ful = {"success": False, "error": str(exc)}
    return {**job, **cap, "fulfillment": ful}


def _fulfill_job(job: Dict[str, Any]) -> Dict[str, Any]:
    rail = str(job.get("rail") or "shop")
    local_id = str(job.get("local_id") or "").strip()
    user_id = str(job.get("user_id") or "").strip()
    ppid = str(job.get("paypal_order_id") or "").strip()

    try:
        if rail == "hosting":
            from backend.services.mn2_masternode_hosting_service import capture as hosting_capture

            return {**job, **hosting_capture(local_id, user_id)}
        if rail == "onramp":
            from backend.services.mn2_onramp_service import capture as onramp_capture

            return {**job, **onramp_capture(local_id, user_id)}
        if rail == "p2p":
            from backend.services.mn2_p2p_service import capture as p2p_capture

            return {**job, **p2p_capture(local_id, user_id)}
        if rail == "camgirls":
            from backend.services.camgirls_paypal_service import fulfill_capture

            return {**job, **fulfill_capture(ppid, user_id=user_id)}
        if rail == "casino":
            from backend.services.casino_service import capture_paypal_deposit

            return {**job, **capture_paypal_deposit(user_id, ppid, job.get("pack_id"))}
        if rail == "exchange_controller":
            from backend.services.paypal_service import finish_checkout_order
            from backend.services.exchange_user_controller_service import fulfill_paypal_order

            cap = finish_checkout_order(ppid)
            ful = fulfill_paypal_order(user_id, ppid, cap)
            return {**job, **cap, "fulfillment": ful}
    except Exception as exc:
        return {**job, "success": False, "error": str(exc), "outcome": "fulfill_failed"}

    return _fulfill_shop_job(job)


def finish_pending_paypal_orders(
    *,
    limit: int = 400,
    extra_order_ids: Optional[List[str]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Capture APPROVED (and recover COMPLETED) pending checkouts across rails."""
    from backend.services.paypal_service import finish_checkout_order

    jobs = collect_pending_paypal_jobs(extra_order_ids)
    jobs = jobs[: max(1, int(limit or 400))]
    counts = {
        "pending_found": len(jobs),
        "captured": 0,
        "awaiting_payer": 0,
        "expired": 0,
        "failed": 0,
        "skipped": 0,
    }
    results: List[Dict[str, Any]] = []
    if dry_run:
        for job in jobs:
            results.append({**job, "outcome": "dry_run"})
        return {"success": True, "dry_run": True, "counts": counts, "results": results}

    for job in jobs:
        lookup = finish_checkout_order(job["paypal_order_id"])
        outcome = str(lookup.get("outcome") or "")
        if outcome == "awaiting_payer":
            counts["awaiting_payer"] += 1
            results.append({**job, **lookup})
            continue
        if outcome == "expired":
            counts["expired"] += 1
            results.append({**job, **lookup})
            continue
        if outcome == "missing":
            counts["skipped"] += 1
            results.append({**job, **lookup})
            continue
        if not lookup.get("success") and outcome not in ("captured", "capture_failed"):
            counts["failed"] += 1
            results.append({**job, **lookup})
            continue
        done = _fulfill_job(job)
        ok = bool(done.get("success"))
        if ok:
            counts["captured"] += 1
            done.setdefault("outcome", "captured")
        else:
            counts["failed"] += 1
            done.setdefault("outcome", "failed")
        results.append(done)

    return {
        "success": True,
        "counts": counts,
        "results": results,
    }
