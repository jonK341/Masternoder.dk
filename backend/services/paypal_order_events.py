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

# create_order() also writes these rails into the shop pending file. Do not fulfill
# them as shop coins/points — dedicated collectors/webhooks own the grant.
_SHOP_FALLBACK_RAILS = {
    "exchange_mn2",
    "exchange_crypto",
    "exchange_controller",
    "camgirls",
    "casino",
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


def _rail_from_shop_row(row: Dict[str, Any]) -> str:
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    source = str(meta.get("source") or "").strip().lower()
    product = str(meta.get("product") or "").strip().lower()
    item = str(row.get("item_id") or meta.get("item_id") or "").strip()
    if meta.get("casino_deposit") or source == "casino":
        return "casino"
    if source in ("exchange", "exchange_mn2"):
        return "exchange_mn2"
    if source == "exchange_crypto" or item.startswith("crypto:"):
        return "exchange_crypto"
    if source == "exchange_controller":
        return "exchange_controller"
    if product == "camgirls" or source == "camgirls" or item.startswith("camgirls_"):
        return "camgirls"
    if product == "mn2_masternode_hosting":
        return "hosting"
    if item == "mn2_onramp" or meta.get("onramp_quote_id"):
        return "onramp"
    if item == "mn2_p2p" or meta.get("p2p_order_id"):
        return "p2p"
    return "shop"


def dispatch_order_webhook(event: Dict[str, Any], signature_ok: bool) -> Dict[str, Any]:
    """Send checkout/capture events to every PayPal rail. Signature already verified upstream."""
    event_type = str((event or {}).get("event_type") or "").upper()
    dispatched: Dict[str, Any] = {}

    if signature_ok and event_type == "CHECKOUT.ORDER.APPROVED":
        oid = _order_id_from_event(event or {})
        if oid:
            try:
                from backend.services.paypal_service import finish_checkout_order

                dispatched["immediate_capture"] = finish_checkout_order(oid)
            except Exception as exc:
                dispatched["immediate_capture"] = {"success": False, "error": str(exc)}

    handlers = (
        ("hosting", "backend.services.mn2_masternode_hosting_service"),
        ("onramp", "backend.services.mn2_onramp_service"),
        ("p2p", "backend.services.mn2_p2p_service"),
        ("camgirls", "backend.services.camgirls_paypal_service"),
        ("exchange", "backend.services.crypto_exchange_service"),
        ("exchange_controller", "backend.services.exchange_user_controller_service"),
        ("casino", "backend.services.casino_service"),
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
    if _rail_from_shop_row(pending) != "shop":
        return {"success": True, "ignored": True, "reason": "non_shop_rail"}
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

    # Dedicated rails first so shop remember_shop_order copies do not steal fulfillment.
    for spec in (
        ("backend.services.mn2_masternode_hosting_service", "list_pending_paypal_payments"),
        ("backend.services.mn2_onramp_service", "list_pending_paypal_payments"),
        ("backend.services.mn2_p2p_service", "list_pending_paypal_payments"),
        ("backend.services.camgirls_paypal_service", "list_pending_paypal_payments"),
        ("backend.services.casino_service", "list_pending_paypal_deposits"),
        ("backend.services.crypto_exchange_service", "list_pending_paypal_payments"),
        ("backend.services.exchange_user_controller_service", "list_pending_paypal_payments"),
    ):
        try:
            mod = __import__(spec[0], fromlist=[spec[1]])
            for job in getattr(mod, spec[1])() or []:
                if isinstance(job, dict):
                    _add(job)
        except Exception:
            pass

    try:
        from backend.services.paypal_service import list_pending_shop_orders

        for row in list_pending_shop_orders():
            if not isinstance(row, dict):
                continue
            oid = str(row.get("order_id") or "").strip()
            if not oid:
                continue
            rail = _rail_from_shop_row(row)
            if rail == "shop":
                _add({
                    "rail": "shop",
                    "local_id": oid,
                    "paypal_order_id": oid,
                    "user_id": row.get("user_id"),
                    "item_id": row.get("item_id"),
                    "item_name": row.get("item_name"),
                })
            elif rail in _SHOP_FALLBACK_RAILS:
                _add({
                    "rail": rail,
                    "local_id": oid,
                    "paypal_order_id": oid,
                    "user_id": row.get("user_id"),
                    "item_id": row.get("item_id"),
                    "item_name": row.get("item_name"),
                })
    except Exception:
        pass

    for raw in extra_order_ids or []:
        oid = str(raw or "").strip()
        if not oid or oid in seen:
            continue
        job = {
            "rail": "shop",
            "local_id": oid,
            "paypal_order_id": oid,
            "user_id": "",
            "item_id": "",
        }
        try:
            from backend.services.paypal_service import get_pending_shop_order

            row = get_pending_shop_order(oid) or {}
            if row:
                rail = _rail_from_shop_row(row)
                if rail == "shop" or rail in _SHOP_FALLBACK_RAILS:
                    job = {
                        "rail": rail,
                        "local_id": oid,
                        "paypal_order_id": oid,
                        "user_id": row.get("user_id") or "",
                        "item_id": row.get("item_id") or "",
                        "item_name": row.get("item_name") or "",
                    }
        except Exception:
            pass
        _add(job)

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
            return {**job, **cap, "fulfillment": ful, "success": bool(ful.get("success"))}
        if rail == "exchange_mn2":
            from backend.services.paypal_service import finish_checkout_order
            from backend.services.crypto_exchange_service import fulfill_paypal_mn2_order

            cap = finish_checkout_order(ppid)
            ful = fulfill_paypal_mn2_order(user_id, ppid, cap)
            return {**job, **cap, "fulfillment": ful, "success": bool(ful.get("success"))}
        if rail == "exchange_crypto":
            from backend.services.paypal_service import finish_checkout_order
            from backend.services.crypto_exchange_service import fulfill_paypal_crypto_order

            cap = finish_checkout_order(ppid)
            ful = fulfill_paypal_crypto_order(user_id, ppid, cap)
            return {**job, **cap, "fulfillment": ful, "success": bool(ful.get("success"))}
    except Exception as exc:
        return {**job, "success": False, "error": str(exc), "outcome": "fulfill_failed"}

    return _fulfill_shop_job(job)


_DEAD_PAYPAL = frozenset({"VOIDED", "EXPIRED", "DECLINED"})


def _prune_reason_from_lookup(lookup: Dict[str, Any]) -> Optional[str]:
    if not lookup.get("success"):
        err = str(lookup.get("error") or "")
        if "INVALID_RESOURCE_ID" in err or "RESOURCE_NOT_FOUND" in err:
            return "paypal_not_found"
        return None
    st = str(lookup.get("status") or "").upper()
    if st in _DEAD_PAYPAL:
        return f"paypal_{st.lower()}"
    return None


def expire_pending_paypal_job(job: Dict[str, Any], reason: str) -> Dict[str, Any]:
    """Remove a local pending row after PayPal checkout is gone or dead."""
    rail = str(job.get("rail") or "shop")
    local_id = str(job.get("local_id") or "").strip()
    ppid = str(job.get("paypal_order_id") or "").strip()
    if not ppid and not local_id:
        return {"success": False, "error": "missing_ids"}

    try:
        if rail == "shop" or rail in _SHOP_FALLBACK_RAILS:
            from backend.services.paypal_service import update_shop_order

            update_shop_order(ppid or local_id, status="expired", prune_reason=reason)
            return {"success": True, "rail": rail, "paypal_order_id": ppid}
        if rail == "hosting":
            from backend.services.mn2_masternode_hosting_service import abandon_pending_paypal_payment

            return abandon_pending_paypal_payment(local_id, reason=reason)
        if rail == "onramp":
            from backend.services.mn2_onramp_service import abandon_pending_paypal_payment

            return abandon_pending_paypal_payment(local_id, reason=reason)
        if rail == "p2p":
            from backend.services.mn2_p2p_service import abandon_pending_paypal_payment

            return abandon_pending_paypal_payment(local_id, reason=reason)
        if rail == "camgirls":
            from backend.services.camgirls_paypal_service import abandon_pending_paypal_payment

            return abandon_pending_paypal_payment(ppid, reason=reason)
        if rail == "casino":
            from backend.services.casino_service import abandon_pending_paypal_deposit

            return abandon_pending_paypal_deposit(ppid, reason=reason)
        if rail == "exchange_mn2":
            from backend.services import crypto_exchange_service as ex

            return _expire_exchange_paypal_pending(ex._PAYPAL_MN2_ORDERS_PATH, ppid, reason)
        if rail == "exchange_crypto":
            from backend.services import crypto_exchange_service as ex

            return _expire_exchange_paypal_pending(ex._PAYPAL_CRYPTO_ORDERS_PATH, ppid, reason)
        if rail == "exchange_controller":
            from backend.services.exchange_user_controller_service import abandon_pending_paypal_payment

            return abandon_pending_paypal_payment(ppid, reason=reason)
    except Exception as exc:
        return {"success": False, "error": str(exc), "rail": rail}

    return {"success": False, "error": "unknown_rail", "rail": rail}


def _expire_exchange_paypal_pending(path: str, paypal_order_id: str, reason: str) -> Dict[str, Any]:
    from backend.services import crypto_exchange_service as ex

    oid = str(paypal_order_id or "").strip()
    with ex._LOCK:
        rows = ex._read_json(path, {"pending": {}, "captured": {}, "expired": {}})
        pending = rows.get("pending") or {}
        row = pending.pop(oid, None)
        if not row:
            return {"success": False, "skipped": True, "reason": "not_found"}
        rows.setdefault("expired", {})[oid] = {
            **(row if isinstance(row, dict) else {}),
            "pruned_at": ex._iso(),
            "reason": reason,
        }
        ex._write_json(path, rows)
    return {"success": True, "order_id": oid}


def prune_stale_paypal_pending_orders(
    *,
    limit: int = 400,
    extra_order_ids: Optional[List[str]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Drop local pending rows when PayPal no longer has a live checkout."""
    from backend.services.paypal_service import get_checkout_order

    jobs = collect_pending_paypal_jobs(extra_order_ids)
    jobs = jobs[: max(1, int(limit or 400))]
    counts = {"scanned": len(jobs), "pruned": 0, "kept": 0, "skipped_lookup": 0}
    results: List[Dict[str, Any]] = []
    for job in jobs:
        ppid = str(job.get("paypal_order_id") or "").strip()
        if not ppid:
            counts["skipped_lookup"] += 1
            results.append({**job, "outcome": "no_paypal_id"})
            continue
        lookup = get_checkout_order(ppid)
        reason = _prune_reason_from_lookup(lookup)
        if not reason:
            counts["kept"] += 1
            results.append({
                **job,
                "outcome": "kept",
                "paypal_status": lookup.get("status"),
                "lookup_ok": lookup.get("success"),
            })
            continue
        if dry_run:
            results.append({**job, "outcome": "would_prune", "reason": reason})
            counts["pruned"] += 1
            continue
        expired = expire_pending_paypal_job(job, reason)
        if expired.get("success"):
            counts["pruned"] += 1
            results.append({**job, "outcome": "pruned", "reason": reason, "expire": expired})
        else:
            counts["skipped_lookup"] += 1
            results.append({**job, "outcome": "prune_failed", "reason": reason, "expire": expired})
    return {"success": True, "dry_run": dry_run, "counts": counts, "results": results}


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
            expire_pending_paypal_job(
                job,
                f"paypal_{str(lookup.get('paypal_status') or 'expired').lower()}",
            )
            results.append({**job, **lookup, "local_expired": True})
            continue
        if outcome == "missing":
            err = str(lookup.get("error") or "")
            if "INVALID_RESOURCE_ID" in err or "RESOURCE_NOT_FOUND" in err:
                counts["expired"] += 1
                expire_pending_paypal_job(job, "paypal_not_found")
                results.append({**job, **lookup, "local_expired": True})
            else:
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
