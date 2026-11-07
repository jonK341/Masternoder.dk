"""Camgirls performer payout addresses."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PAYOUT_FILE = os.path.join(_ROOT, "data", "camgirls_payout_addresses.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read() -> dict:
    if not os.path.isfile(_PAYOUT_FILE):
        return {"performers": {}}
    try:
        with open(_PAYOUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"performers": {}}
    except Exception:
        return {"performers": {}}


def _write(data: dict) -> None:
    os.makedirs(os.path.dirname(_PAYOUT_FILE), exist_ok=True)
    with open(_PAYOUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _default_paypal_email() -> str:
    return (
        os.environ.get("CAMGIRLS_PAYOUT_PAYPAL_EMAIL")
        or os.environ.get("EXCHANGE_PAYOUT_PAYPAL_EMAIL")
        or os.environ.get("PAYPAL_BUSINESS_EMAIL")
        or ""
    ).strip()


def paypal_checkout_available() -> bool:
    return bool(
        (os.environ.get("PAYPAL_CLIENT_ID") or "").strip()
        and (os.environ.get("PAYPAL_CLIENT_SECRET") or "").strip()
    )


def get_payout_address(performer_id: str) -> Dict[str, Any]:
    data = _read()
    row = (data.get("performers") or {}).get(performer_id) or {}
    return {
        "address": row.get("address"),
        "success": bool(row.get("address")),
        "paypal_email": row.get("paypal_email"),
        "paypal_checkout_enabled": bool(row.get("paypal_checkout_enabled")),
    }


def list_payout_addresses() -> Dict[str, Any]:
    data = _read()
    performers = data.get("performers") or {}
    rows = [
        {
            "performer_id": pid,
            "payout_address": (row or {}).get("address"),
            "created_at": (row or {}).get("created_at"),
            "paypal_email": (row or {}).get("paypal_email"),
            "paypal_checkout_enabled": (row or {}).get("paypal_checkout_enabled"),
        }
        for pid, row in performers.items()
        if isinstance(row, dict)
    ]
    return {"success": True, "count": len(rows), "performers": rows}


def provision_paypal_for_performers(performer_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Tag each performer for site PayPal checkout + optional payout email metadata."""
    from backend.services.camgirls_service import _get_performer, _load_performers_raw

    targets = performer_ids or [str(p.get("id")) for p in _load_performers_raw() if p.get("id")]
    targets = [t for t in targets if t]
    checkout_on = paypal_checkout_available()
    fallback_email = _default_paypal_email()
    data = _read()
    bucket = data.setdefault("performers", {})
    results: List[Dict[str, Any]] = []
    for pid in targets:
        row = bucket.get(pid)
        if not isinstance(row, dict):
            row = {}
            bucket[pid] = row
        performer = _get_performer(pid) or {}
        email = (performer.get("paypal_email") or "").strip() or fallback_email
        row["paypal_checkout_enabled"] = checkout_on
        if email:
            row["paypal_email"] = email
        row["paypal_provisioned_at"] = _iso()
        results.append({
            "success": True,
            "performer_id": pid,
            "paypal_checkout_enabled": checkout_on,
            "paypal_email": email or None,
        })
    data.setdefault("platform", {})["paypal_checkout"] = checkout_on
    data["platform"]["paypal_provisioned_at"] = _iso()
    _write(data)
    return {
        "success": True,
        "paypal_checkout_enabled": checkout_on,
        "provisioned": len(results),
        "total": len(targets),
        "results": results,
    }


def provision_payout_rails(performer_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """MN2 daemon addresses + PayPal checkout metadata for all targets."""
    mn2 = provision_payout_addresses(performer_ids=performer_ids)
    paypal = provision_paypal_for_performers(performer_ids=performer_ids)
    return {
        "success": bool(mn2.get("success")) and bool(paypal.get("success")),
        "mn2": mn2,
        "paypal": paypal,
        "provisioned_mn2": mn2.get("provisioned"),
        "provisioned_paypal": paypal.get("provisioned"),
        "total": mn2.get("total"),
    }


def validate_payout_address_on_chain(address: str) -> Dict[str, Any]:
    addr = (address or "").strip()
    if not addr:
        return {"checked": False, "address": None, "isvalid": False, "error": "empty_address"}
    try:
        from backend.services.mn2_rpc_client import validateaddress

        r = validateaddress(addr)
    except Exception as exc:
        return {"checked": False, "address": addr, "error": str(exc)}
    if r.get("error"):
        return {"checked": False, "address": addr, "error": r.get("error")}
    res = r.get("result") if isinstance(r.get("result"), dict) else {}
    out = {
        "checked": True,
        "address": addr,
        "isvalid": bool(res.get("isvalid")),
    }
    if "ismine" in res:
        out["ismine"] = bool(res.get("ismine"))
    return out


def audit_performer_wallets(
    performer_ids: Optional[List[str]] = None,
    *,
    check_rpc: bool = True,
    sync_catalog: bool = True,
) -> Dict[str, Any]:
    """Report MN2 payout address coverage and optional daemon validateaddress per profile."""
    from backend.services.camgirls_service import list_active_performer_ids, get_performer_row

    targets = performer_ids or list_active_performer_ids()
    data = _read()
    bucket = data.get("performers") or {}
    rows: List[Dict[str, Any]] = []
    missing = 0
    invalid = 0
    for pid in targets:
        row = bucket.get(pid) if isinstance(bucket.get(pid), dict) else {}
        addr = (row.get("address") or "").strip() or None
        perf = get_performer_row(pid) or {}
        entry: Dict[str, Any] = {
            "performer_id": pid,
            "display_name": perf.get("display_name"),
            "payout_address": addr,
            "has_address": bool(addr),
            "paypal_checkout_enabled": bool(row.get("paypal_checkout_enabled")),
        }
        if not addr:
            missing += 1
        elif check_rpc:
            v = validate_payout_address_on_chain(addr)
            entry["on_chain"] = v
            if v.get("checked") and not v.get("isvalid"):
                invalid += 1
        rows.append(entry)
        if sync_catalog and addr and perf:
            merged = {**perf, "payout_address": addr}
            try:
                from backend.services.camgirls_catalog_sync_service import upsert_performer_db

                upsert_performer_db(merged)
            except Exception:
                pass
    return {
        "success": True,
        "total": len(targets),
        "with_address": len(targets) - missing,
        "missing_address": missing,
        "invalid_on_chain": invalid,
        "rpc_checked": bool(check_rpc),
        "performers": rows,
    }


def payout_performer_reward_on_chain(
    performer_id: str,
    amount: float,
    *,
    source: str,
    reference: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Treasury sendtoaddress to the performer's daemon payout address (not in-app balance)."""
    amt = float(amount or 0)
    if amt <= 0:
        return {"success": False, "error": "amount_must_be_positive"}
    pa = get_payout_address(performer_id)
    address = (pa.get("address") or "").strip()
    if not address:
        return {"success": False, "error": "no_payout_address", "performer_id": performer_id}

    ref = (reference or f"camgirl-reward:{performer_id}").strip()
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "performer_id": performer_id,
            "address": address,
            "amount": amt,
            "reference": ref,
        }

    from backend.services.mn2_chain_rewards_service import chain_payouts_enabled, _min_payout

    if not chain_payouts_enabled():
        return {"success": True, "skipped": True, "reason": "chain_payouts_disabled"}
    if amt < _min_payout():
        return {"success": True, "skipped": True, "reason": "below_min_payout"}

    from backend.services.mn2_ledger import append_entry, is_txid_processed

    ref_key = f"chain-reward:{ref}"
    if is_txid_processed(ref_key):
        return {"success": True, "duplicate": True, "reference": ref}

    from backend.services.mn2_rpc_client import sendtoaddress

    send = sendtoaddress(address, round(amt, 8))
    if send.get("error"):
        return {"success": False, "error": send.get("error"), "reference": ref, "address": address}
    txid = (send.get("result") or "").strip()
    if not txid:
        return {"success": False, "error": "rpc_no_txid", "reference": ref}

    meta = {
        "reference": ref,
        "performer_id": performer_id,
        "source": source,
        "chain_paid": True,
        "chain_txid": txid,
    }
    append_entry(
        user_id=f"camgirl:{performer_id}",
        entry_type="camgirls_chain_reward",
        amount=amt,
        txid=txid,
        address=address,
        metadata=meta,
    )
    return {
        "success": True,
        "txid": txid,
        "address": address,
        "amount": amt,
        "reference": ref,
        "performer_id": performer_id,
    }


def provision_payout_addresses(performer_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    from backend.services.camgirls_service import _load_performers_raw
    from backend.services.mn2_wallet_service import generate_daemon_address

    targets = performer_ids or [str(p.get("id")) for p in _load_performers_raw() if p.get("id")]
    targets = [t for t in targets if t]
    data = _read()
    bucket = data.setdefault("performers", {})
    results: List[Dict[str, Any]] = []
    ok_count = 0
    for pid in targets:
        existing = bucket.get(pid) if isinstance(bucket.get(pid), dict) else None
        if existing and existing.get("address"):
            results.append({
                "success": True,
                "performer_id": pid,
                "payout_address": existing.get("address"),
                "created": False,
            })
            ok_count += 1
            continue
        gen = generate_daemon_address()
        if not gen.get("success"):
            results.append({
                "success": False,
                "performer_id": pid,
                "error": gen.get("error") or "address_failed",
            })
            continue
        addr = gen.get("address") or gen.get("deposit_address")
        bucket[pid] = {"address": addr, "created_at": _iso(), "source": "mn2_daemon"}
        results.append({
            "success": True,
            "performer_id": pid,
            "payout_address": addr,
            "created": True,
        })
        ok_count += 1
    _write(data)
    return {
        "success": ok_count == len(targets) if targets else True,
        "provisioned": ok_count,
        "total": len(targets),
        "results": results,
    }
