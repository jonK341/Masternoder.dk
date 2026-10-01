"""On-chain MN2 reward payouts to user deposit addresses (treasury -> user wallet)."""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, Optional

_LOCK = threading.Lock()


def _config() -> Dict[str, Any]:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base, "data", "mn2_config.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if isinstance(cfg, dict):
                    return cfg
        except Exception:
            pass
    return {}


def chain_payouts_enabled() -> bool:
    payouts = (_config().get("chain_reward_payouts") or {})
    return bool(payouts.get("enabled", False))


def _min_payout() -> float:
    payouts = (_config().get("chain_reward_payouts") or {})
    try:
        return float(payouts.get("min_amount_mn2") or 0.0001)
    except (TypeError, ValueError):
        return 0.0001


def payout_reward_on_chain(
    user_id: str,
    amount: float,
    *,
    source: str,
    reference: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Send MN2 from treasury to the user's primary deposit address when chain payouts are enabled.
    Returns {success, skipped?, txid?, error?}. Skips silently when disabled or RPC unavailable.
    """
    amt = float(amount or 0)
    if amt <= 0:
        return {"success": False, "error": "amount_must_be_positive"}
    if not chain_payouts_enabled():
        return {"success": True, "skipped": True, "reason": "chain_payouts_disabled"}
    if amt < _min_payout():
        return {"success": True, "skipped": True, "reason": "below_min_payout"}

    from backend.services.mn2_wallet_service import get_or_create_deposit_address
    from backend.services.mn2_ledger import is_txid_processed

    ref_key = f"chain-reward:{reference}"
    if is_txid_processed(ref_key):
        return {"success": True, "duplicate": True, "reference": reference}

    addr_res = get_or_create_deposit_address(str(user_id).strip())
    if not addr_res.get("success"):
        return {"success": False, "error": addr_res.get("error") or "no_deposit_address"}
    address = (addr_res.get("deposit_address") or "").strip()
    if not address:
        return {"success": False, "error": "no_deposit_address"}

    if not _LOCK.acquire(blocking=False):
        return {"success": False, "error": "chain_payout_busy"}

    try:
        from backend.services.mn2_rpc_client import sendtoaddress

        send = sendtoaddress(address, round(amt, 8))
        if send.get("error"):
            return {"success": False, "error": send.get("error")}
        txid = (send.get("result") or "").strip()
        if not txid:
            return {"success": False, "error": "rpc_no_txid"}
        return {"success": True, "txid": txid, "address": address, "amount": amt}
    finally:
        _LOCK.release()
