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

        from backend.services.mn2_wallet_service import get_address_to_user_map
        from backend.services.mn2_rpc_client import listtransactions
        from backend.services.mn2_ledger import append_entry, is_txid_processed
        from backend.services.unified_points_database import unified_points_db

        address_to_user = get_address_to_user_map()
        try:
            from backend.services.mn2_order_payment_service import get_address_to_order_map, confirm_and_fulfill
            address_to_order = get_address_to_order_map()
        except Exception:
            address_to_order = {}

        if not address_to_user and not address_to_order:
            _log_run(start, time.time(), 0, 0, 0, None)
            return result

        r = listtransactions(count=500, skip=0)
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
            if is_txid_processed(txid):
                continue
            address = (tx.get("address") or "").strip()
            if not address:
                continue
            confirmations = int(tx.get("confirmations") or 0)
            if confirmations < required_confirmations:
                continue
            try:
                amount = float(tx.get("amount") or 0)
            except (TypeError, ValueError):
                continue
            if amount <= 0:
                continue

            # Phase 8: order payment address takes precedence (on-chain checkout)
            if address in address_to_order:
                order = address_to_order[address]
                ref = order.get("payment_ref")
                if ref and abs(amount - float(order.get("amount_mn2", 0))) < 0.00000001:
                    fulfilled = confirm_and_fulfill(ref, txid)
                    if fulfilled and fulfilled.get("status") == "fulfilled":
                        orders_fulfilled += 1
                continue
            if address not in address_to_user:
                continue

            user_id = address_to_user[address]
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
