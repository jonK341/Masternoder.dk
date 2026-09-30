"""
MN2 ledger (Phase 3): append-only log of deposits, withdrawals, shop payments.
Idempotency: deposit entries include txid; scanner checks is_txid_processed before crediting.
See docs/MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md Phase 3.
"""
import os
import json
import threading
from datetime import datetime, timedelta, date
from typing import Dict, Any, List

_LEDGER_LOCK = threading.Lock()
_LEDGER_FILENAME = "mn2_ledger.json"
_SUMMARY_CACHE: Dict[str, Any] = {"mtime": None, "rows": []}


def _data_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "data")


def _ledger_path() -> str:
    return os.path.join(_data_dir(), _LEDGER_FILENAME)


def _load_entries() -> List[Dict[str, Any]]:
    path = _ledger_path()
    with _LEDGER_LOCK:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict) and "entries" in data:
                        return list(data["entries"])
                    if isinstance(data, list):
                        return data
            except Exception:
                pass
        return []


def _save_entries(entries: List[Dict[str, Any]]) -> None:
    path = _ledger_path()
    os.makedirs(_data_dir(), exist_ok=True)
    with _LEDGER_LOCK:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"entries": entries}, f, indent=2)


def append_entry(
    user_id: str,
    entry_type: str,
    amount: float,
    txid: str = None,
    address: str = None,
    metadata: Dict[str, Any] = None,
) -> None:
    """Append a ledger entry. entry_type: deposit | withdrawal | shop_payment | stake | unstake | staking_reward | onramp_purchase | onramp_clawback."""
    entries = _load_entries()
    entries.append({
        "user_id": str(user_id),
        "type": str(entry_type),
        "amount": float(amount),
        "txid": txid,
        "address": address,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "metadata": metadata or {},
    })
    _save_entries(entries)


def _apply_entry_to_summary_row(row: Dict[str, Any], entry: Dict[str, Any]) -> None:
    from backend.services.ledger_buy_potential_service import BUY_SPEND_TYPES, FUNDING_INFLOW_TYPES

    row["entry_count"] += 1
    ca = str(entry.get("created_at") or "")
    if ca > str(row.get("last_activity") or ""):
        row["last_activity"] = ca
    t = str(entry.get("type") or "").strip()
    row["entry_types"].add(t)
    try:
        amt = float(entry.get("amount") or 0)
    except (TypeError, ValueError):
        amt = 0.0
    if t in ("deposit", "staking_reward", "onramp_purchase", "aggregator_mn2_earn", "encoder_payment"):
        row["ledger_in_mn2"] += amt
    elif t in ("withdrawal", "shop_payment", "onramp_clawback", "encoder_payment"):
        if t == "encoder_payment" and amt > 0:
            row["ledger_out_mn2"] += amt
        elif t != "encoder_payment":
            row["ledger_out_mn2"] += abs(amt)
    if t in BUY_SPEND_TYPES and amt > 0:
        row["buy_spend_mn2"] += amt
        row["buy_count"] += 1
        row["has_bought"] = True
        row["buy_channels"].add(t)
        if ca > str(row.get("last_buy_at") or ""):
            row["last_buy_at"] = ca
    if t in FUNDING_INFLOW_TYPES and amt > 0:
        row["has_funding"] = True


def _new_summary_row(user_id: str) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "entry_count": 0,
        "last_activity": "",
        "last_buy_at": "",
        "ledger_in_mn2": 0.0,
        "ledger_out_mn2": 0.0,
        "buy_spend_mn2": 0.0,
        "buy_count": 0,
        "has_bought": False,
        "has_funding": False,
        "buy_channels": set(),
        "entry_types": set(),
    }


def _finalize_summary_row(row: Dict[str, Any]) -> Dict[str, Any]:
    from backend.services.ledger_buy_potential_service import enrich_ledger_summary

    base = {
        "user_id": row["user_id"],
        "entry_count": row["entry_count"],
        "last_activity": row["last_activity"],
        "last_buy_at": row.get("last_buy_at") or "",
        "ledger_in_mn2": round(float(row["ledger_in_mn2"] or 0), 8),
        "ledger_out_mn2": round(float(row["ledger_out_mn2"] or 0), 8),
        "ledger_net_mn2": round(float(row["ledger_in_mn2"] or 0) - float(row["ledger_out_mn2"] or 0), 8),
        "buy_spend_mn2": round(float(row.get("buy_spend_mn2") or 0), 8),
        "buy_count": int(row.get("buy_count") or 0),
        "has_bought": bool(row.get("has_bought")),
        "has_funding": bool(row.get("has_funding")),
        "buy_channels": sorted(row.get("buy_channels") or []),
        "entry_types": sorted(row["entry_types"]),
    }
    return enrich_ledger_summary(base)


def _summarize_entries_for_user(user_id: str, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    row = _new_summary_row(str(user_id))
    for entry in entries:
        _apply_entry_to_summary_row(row, entry)
    return _finalize_summary_row(row)


def _build_ledger_user_summaries() -> List[Dict[str, Any]]:
    """Build distinct ledger customer summaries (uncached)."""
    by_user: Dict[str, Dict[str, Any]] = {}
    for e in _load_entries():
        uid = str(e.get("user_id") or "").strip()
        if not uid or uid.lower() in ("", "default_user", "anon", "anonymous"):
            continue
        row = by_user.setdefault(uid, _new_summary_row(uid))
        _apply_entry_to_summary_row(row, e)

    rows = [_finalize_summary_row(row) for row in by_user.values()]
    rows.sort(key=lambda r: str(r.get("last_activity") or ""), reverse=True)
    return rows


def list_ledger_user_summaries(*, limit: int = 5000) -> List[Dict[str, Any]]:
    """Distinct ledger customers with activity summary, newest activity first."""
    path = _ledger_path()
    mtime = os.path.getmtime(path) if os.path.exists(path) else None
    with _LEDGER_LOCK:
        if _SUMMARY_CACHE.get("mtime") == mtime and _SUMMARY_CACHE.get("rows") is not None:
            rows = list(_SUMMARY_CACHE["rows"])
        else:
            rows = _build_ledger_user_summaries()
            _SUMMARY_CACHE["mtime"] = mtime
            _SUMMARY_CACHE["rows"] = rows
    lim = max(1, min(int(limit or 5000), 20000))
    return rows[:lim]


def count_ledger_users() -> int:
    """Fast count of distinct ledger users (reads persisted index when available)."""
    try:
        from backend.services.ledger_customer_aggregator_service import ledger_customer_index_meta

        return int(ledger_customer_index_meta().get("total") or 0)
    except Exception:
        return 0


def get_entries_by_user(user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Return ledger entries for the user, newest first. limit caps the count."""
    entries = _load_entries()
    user_entries = [e for e in entries if (e.get("user_id") or "").strip() == str(user_id).strip()]
    user_entries.sort(key=lambda e: e.get("created_at") or "", reverse=True)
    return user_entries[:limit]


def is_txid_processed(txid: str) -> bool:
    """True if this txid was already credited via deposit or treasury_deposit."""
    if not (txid or "").strip():
        return False
    txid = str(txid).strip()
    entries = _load_entries()
    credited_types = ("deposit", "treasury_deposit")
    return any(
        (e.get("type") in credited_types and (e.get("txid") or "").strip() == txid)
        for e in entries
    )
def is_treasury_deposit_recorded(txid: str) -> bool:
    """True if treasury_deposit ledger row exists for txid."""
    if not (txid or "").strip():
        return False
    txid = str(txid).strip()
    return any(
        e.get("type") == "treasury_deposit" and (e.get("txid") or "").strip() == txid
        for e in _load_entries()
    )


def count_withdrawals_since(user_id: str, since_iso: str) -> int:
    """Number of withdrawal entries for user with created_at >= since_iso (for rate limiting)."""
    entries = _load_entries()
    uid = str(user_id).strip()
    return sum(
        1 for e in entries
        if (e.get("user_id") or "").strip() == uid
        and e.get("type") == "withdrawal"
        and (e.get("created_at") or "") >= since_iso
    )


def get_wallet_activity_days(user_id: str, days: int = 5) -> List[Dict[str, Any]]:
    """
    Per-calendar-day (UTC) aggregates for profile 5-day monitor.
    deposits_mn2 = sum of receive amounts; out_mn2 = withdrawals + shop payments (absolute).
    """
    days = max(1, min(int(days or 5), 31))
    uid = str(user_id).strip()
    end_d: date = datetime.utcnow().date()
    day_keys = [(end_d - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]
    buckets: Dict[str, Dict[str, Any]] = {
        k: {
            "date": k,
            "deposits_mn2": 0.0,
            "out_mn2": 0.0,
            "net_mn2": 0.0,
            "events": 0,
        }
        for k in day_keys
    }
    for e in _load_entries():
        if (e.get("user_id") or "").strip() != uid:
            continue
        ca = (e.get("created_at") or "").strip()
        if len(ca) < 10:
            continue
        day = ca[:10]
        if day not in buckets:
            continue
        t = (e.get("type") or "").strip()
        try:
            amt = float(e.get("amount") or 0)
        except (TypeError, ValueError):
            continue
        buckets[day]["events"] += 1
        if t in ("deposit", "staking_reward", "onramp_purchase"):
            buckets[day]["deposits_mn2"] += amt
        elif t in ("withdrawal", "shop_payment", "onramp_clawback"):
            buckets[day]["out_mn2"] += abs(amt)
        # stake / unstake are internal balance<->staked moves: neutral (counted as events only)
    for k in day_keys:
        b = buckets[k]
        b["net_mn2"] = round(b["deposits_mn2"] - b["out_mn2"], 8)
        b["deposits_mn2"] = round(b["deposits_mn2"], 8)
        b["out_mn2"] = round(b["out_mn2"], 8)
    return [buckets[k] for k in day_keys]


def sum_withdrawals_since(user_id: str, since_iso: str) -> float:
    """Total withdrawal amount for user with created_at >= since_iso (Phase 9: daily amount cap)."""
    entries = _load_entries()
    uid = str(user_id).strip()
    return sum(
        float(e.get("amount") or 0)
        for e in entries
        if (e.get("user_id") or "").strip() == uid
        and e.get("type") == "withdrawal"
        and (e.get("created_at") or "") >= since_iso
    )
