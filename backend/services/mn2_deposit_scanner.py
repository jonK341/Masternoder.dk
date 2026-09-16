"""
MN2 deposit scanner (Phase 3): listtransactions → match our addresses → credit after N confirmations.
Single process + lock; idempotency by txid. Logs to logs/mn2_deposit_scanner.jsonl when enabled.
See docs/MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md Phase 3.
"""
import os
import json
import threading
from typing import Dict, Any, List

_SCANNER_LOCK = threading.Lock()


def _load_config() -> Dict[str, Any]:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "data", "mn2_config.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"confirmations": 6, "explorer_base_url": "https://chainz.cryptoid.info/mn2/"}


def _log_run(start_ts: float, end_ts: float, txs_checked: int, credits_applied: int, orders_fulfilled: int = 0, error: str = None) -> None:
    try:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_dir = os.path.join(base, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "mn2_deposit_scanner.jsonl")
        payload = {
            "start": start_ts,
            "end": end_ts,
            "duration_s": round(end_ts - start_ts, 2),
            "txs_checked": txs_checked,
            "credits_applied": credits_applied,
            "orders_fulfilled": orders_fulfilled,
        }
        if error:
            payload["error"] = error
        line = json.dumps(payload) + "\n"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def _mn2_balance(points_db, user_id: str) -> float:
    """Read a user's in-app MN2 balance via the unified points DB. Best-effort -> 0.0."""
    try:
        data = points_db.get_all_points(user_id) or {}
        return float((data.get("points") or {}).get("mn2_balance") or 0)
    except Exception:
        return 0.0


def apply_order_payment(
    order: Dict[str, Any],
    amount: float,
    confirmations: int,
    txid: str,
    *,
    required_confirmations: int,
    match_tol: float,
    overpay_credit: bool,
    underpay_credit: bool,
    combined_fulfill: bool,
    points_db,
    append_entry,
    confirm_and_fulfill,
    record_order_seen=None,
    mark_underpaid=None,
    get_mn2_balance=None,
) -> Dict[str, Any]:
    """Resolve a single on-chain payment seen for an order address.

    Policy (V9.2): the on-chain daemon payment should complete the transaction
    end-to-end without the user returning to the interface.
      - confirming: tx seen but < N confirmations -> record progress only.
      - exact/overpay: fulfil; refund any excess to the buyer's MN2 balance.
      - underpay: credit what arrived to the buyer's MN2 balance, then (if
        `combined_fulfill`) auto-complete the order from their combined balance
        so the purchase still goes through. Excess shortfall stays as credit.

    Returns a small action descriptor. Idempotency is the caller's job (txid is
    marked processed once any ledger entry is appended for it).
    """
    ref = (order.get("payment_ref") or "").strip()
    required = float(order.get("amount_mn2", 0) or 0)
    user = (order.get("user_id") or "").strip()
    address = order.get("address")
    if not ref or required <= 0:
        return {"action": "skip"}

    # Still confirming -> record progress, don't credit or mark the txid processed.
    if confirmations < int(required_confirmations):
        if record_order_seen:
            try:
                record_order_seen(ref, txid, confirmations, amount_received=amount)
            except Exception:
                pass
        return {"action": "confirming"}

    meta = {"txid": txid, "address": address, "payment_ref": ref,
            "required_mn2": required, "paid_mn2": amount}

    # Paid in full or overpaid.
    if amount + match_tol >= required:
        fulfilled = confirm_and_fulfill(ref, txid, amount_received=amount)
        ok = bool(fulfilled and fulfilled.get("status") == "fulfilled")
        overpay = amount - required
        if ok and overpay_credit and user and overpay > match_tol:
            try:
                points_db.add_points(user, "mn2_balance", round(overpay, 8),
                                     source="mn2_order_overpay_change", metadata=meta)
                append_entry(user_id=user, entry_type="order_overpay_change",
                             amount=round(overpay, 8), txid=txid, address=address, metadata=meta)
            except Exception:
                pass
        return {"action": "fulfilled" if ok else "fulfill_failed", "overpay": max(0.0, overpay)}

    # Underpaid.
    if not (underpay_credit and user):
        return {"action": "underpaid_uncredited"}
    try:
        points_db.add_points(user, "mn2_balance", round(amount, 8),
                             source="mn2_order_underpaid_credit", metadata=meta)
        append_entry(user_id=user, entry_type="order_underpaid_credit",
                     amount=round(amount, 8), txid=txid, address=address, metadata=meta)
    except Exception:
        return {"action": "underpaid_credit_failed"}

    # Daemon completes the transaction: auto-fulfil from the buyer's combined balance.
    if combined_fulfill and get_mn2_balance is not None:
        try:
            bal = float(get_mn2_balance(user) or 0)
        except Exception:
            bal = 0.0
        if bal + match_tol >= required:
            try:
                points_db.add_points(user, "mn2_balance", -round(required, 8),
                                     source="mn2_order_combined_fulfill", metadata=meta)
                fulfilled = confirm_and_fulfill(ref, txid, amount_received=amount)
                if fulfilled and fulfilled.get("status") == "fulfilled":
                    return {"action": "fulfilled_from_balance", "debited": required}
                # Fulfilment failed after debiting -> refund so funds are never lost.
                points_db.add_points(user, "mn2_balance", round(required, 8),
                                     source="mn2_order_combined_refund", metadata=meta)
            except Exception:
                pass

    if mark_underpaid:
        try:
            mark_underpaid(ref, txid, amount)
        except Exception:
            pass
    return {"action": "underpaid_credited"}


def run_scanner() -> Dict[str, Any]:
    """
    Scan wallet listtransactions for receives to our deposit addresses; credit mn2_balance
    and append ledger for each new deposit with >= N confirmations. Thread-safe (one at a time).
    """
    import time
    start = time.time()
    result = {"success": True, "txs_checked": 0, "credits_applied": 0, "orders_fulfilled": 0, "error": None}

    if not _SCANNER_LOCK.acquire(blocking=False):
        result["success"] = False
        result["error"] = "Scanner already running"
        return result

    try:
        config = _load_config()
        required_confirmations = int(config.get("confirmations") or 6)
        match_tol = float(config.get("order_payment_match_tolerance") or 0.00000001)
        overpay_credit = bool(config.get("order_payment_overpay_credit", True))
        underpay_credit = bool(config.get("order_payment_underpay_credit", True))
        combined_fulfill = bool(config.get("order_payment_combined_fulfill", True))

        from backend.services.mn2_wallet_service import get_address_to_user_map
        from backend.services.mn2_rpc_client import listtransactions
        from backend.services.mn2_ledger import append_entry, is_txid_processed, is_treasury_deposit_recorded
        from backend.services.unified_points_database import unified_points_db

        address_to_user = get_address_to_user_map()
        treasury_addr = ""
        try:
            from backend.services.agent_wallet_service import get_treasury
            treasury_addr = (get_treasury().get("address") or "").strip()
        except Exception:
            pass
        try:
            from backend.services.mn2_order_payment_service import (
                get_address_to_order_map,
                confirm_and_fulfill,
                record_order_seen,
                mark_underpaid,
            )
            address_to_order = get_address_to_order_map()
        except Exception:
            address_to_order = {}
            record_order_seen = None
            mark_underpaid = None

        if not address_to_user and not address_to_order:
            _log_run(start, time.time(), 0, 0, 0, None)
            return result

        r = listtransactions(count=1000, skip=0)
        if r.get("error"):
            result["success"] = False
            result["error"] = r["error"]
            _log_run(start, time.time(), 0, 0, 0, r["error"])
            return result

        txs = r.get("result")
        if not isinstance(txs, list):
            _log_run(start, time.time(), 0, 0, 0, None)
            return result

        result["txs_checked"] = len(txs)
        credits = 0
        orders_fulfilled = 0

        for tx in txs:
            category = (tx.get("category") or tx.get("type") or "").strip().lower()
            if category not in ("receive", "recv"):
                continue
            txid = (tx.get("txid") or "").strip()
            if not txid:
                continue
            address = (tx.get("address") or "").strip()
            if not address:
                continue
            if address == treasury_addr and treasury_addr:
                if is_treasury_deposit_recorded(txid):
                    continue
            elif is_txid_processed(txid):
                continue
            confirmations = int(tx.get("confirmations") or 0)
            try:
                amount = float(tx.get("amount") or 0)
            except (TypeError, ValueError):
                continue
            if amount <= 0:
                continue

            # Phase 8 / V9.2: order payment address takes precedence (on-chain checkout).
            # Handled before the confirmation gate so we can surface "confirming"
            # progress and tolerate over/under payment instead of stranding funds.
            if address in address_to_order:
                try:
                    res = apply_order_payment(
                        address_to_order[address], amount, confirmations, txid,
                        required_confirmations=required_confirmations, match_tol=match_tol,
                        overpay_credit=overpay_credit, underpay_credit=underpay_credit,
                        combined_fulfill=combined_fulfill, points_db=unified_points_db,
                        append_entry=append_entry, confirm_and_fulfill=confirm_and_fulfill,
                        record_order_seen=record_order_seen, mark_underpaid=mark_underpaid,
                        get_mn2_balance=lambda uid: _mn2_balance(unified_points_db, uid),
                    )
                    if (res or {}).get("action") in ("fulfilled", "fulfilled_from_balance"):
                        orders_fulfilled += 1
                except Exception:
                    pass
                continue

            if confirmations < required_confirmations:
                continue
            if address not in address_to_user:
                continue

            user_id = address_to_user[address]
            if user_id == "@agent_treasury":
                try:
                    from backend.services.activity_events_service import emit
                    emit("agent_treasury_deposit", channel="agents", payload={"amount": amount, "txid": txid, "address": address})
                    from backend.services.admin_audit_service import log_action
                    log_action("treasury_onchain_deposit", actor="scanner", payload={"amount": amount, "txid": txid})
                except Exception:
                    pass
                unified_points_db.add_points(
                    "agent_treasury",
                    "mn2_balance",
                    amount,
                    source="mn2_treasury_deposit",
                    metadata={
                        "reference": f"treasury-deposit:{txid}",
                        "txid": txid,
                        "address": address,
                        "confirmations": confirmations,
                    },
                )
                append_entry(
                    user_id="agent_treasury",
                    entry_type="treasury_deposit",
                    amount=amount,
                    txid=txid,
                    address=address,
                    metadata={"confirmations": confirmations},
                )
                credits += 1
                continue

            unified_points_db.add_points(
                user_id,
                "mn2_balance",
                amount,
                source="mn2_deposit",
                metadata={"txid": txid, "address": address, "confirmations": confirmations},
            )
            append_entry(
                user_id=user_id,
                entry_type="deposit",
                amount=amount,
                txid=txid,
                address=address,
                metadata={"confirmations": confirmations},
            )
            credits += 1

        result["credits_applied"] = credits
        result["orders_fulfilled"] = orders_fulfilled
        _log_run(start, time.time(), len(txs), credits, orders_fulfilled, None)
        return result
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
        _log_run(start, time.time(), result.get("txs_checked", 0), result.get("credits_applied", 0), result.get("orders_fulfilled", 0), str(e))
        return result
    finally:
        _SCANNER_LOCK.release()
