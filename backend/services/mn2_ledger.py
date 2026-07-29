"""
MN2 ledger (Phase 3): append-only log of deposits, withdrawals, shop payments.
Idempotency: deposit entries include txid; scanner checks is_txid_processed before crediting.
Gate S: load+append+save under one lock; deposit/treasury_deposit txids are unique.

See docs/MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md Phase 3.
"""
import os
import json
import threading
from datetime import datetime, timedelta, date
from typing import Dict, Any, List

_LEDGER_LOCK = threading.RLock()
_LEDGER_FILENAME = "mn2_ledger.json"
_CREDIT_TYPES = frozenset(("deposit", "treasury_deposit"))


def _data_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "data")


def _ledger_path() -> str:
    return os.path.join(_data_dir(), _LEDGER_FILENAME)


def _read_entries_unlocked() -> List[Dict[str, Any]]:
    path = _ledger_path()
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


def _write_entries_unlocked(entries: List[Dict[str, Any]]) -> None:
    path = _ledger_path()
    os.makedirs(_data_dir(), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"entries": entries}, f, indent=2)
    os.replace(tmp, path)


def _load_entries() -> List[Dict[str, Any]]:
    with _LEDGER_LOCK:
        return _read_entries_unlocked()


def _save_entries(entries: List[Dict[str, Any]]) -> None:
    with _LEDGER_LOCK:
        _write_entries_unlocked(entries)


def _txid_credited_unlocked(entries: List[Dict[str, Any]], txid: str) -> bool:
    tid = (txid or "").strip()
    if not tid:
        return False
    return any(
        (e.get("type") in _CREDIT_TYPES and (e.get("txid") or "").strip() == tid)
        for e in entries
    )


def append_entry(
    user_id: str,
    entry_type: str,
    amount: float,
    txid: str = None,
    address: str = None,
    metadata: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Append a ledger entry under one lock (no lost updates under concurrency).

    For deposit / treasury_deposit with a txid, skip if that txid was already credited
    (Gate S deposit idempotency). Returns ``{success, duplicate?}``.
    """
    etype = str(entry_type)
    tid = (txid or "").strip() or None
    row = {
        "user_id": str(user_id),
        "type": etype,
        "amount": float(amount),
        "txid": tid,
        "address": address,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "metadata": metadata or {},
    }
    with _LEDGER_LOCK:
        entries = _read_entries_unlocked()
        if etype in _CREDIT_TYPES and tid and _txid_credited_unlocked(entries, tid):
            return {"success": True, "duplicate": True, "txid": tid}
        entries.append(row)
        _write_entries_unlocked(entries)
    return {"success": True, "duplicate": False, "txid": tid}


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
    with _LEDGER_LOCK:
        return _txid_credited_unlocked(_read_entries_unlocked(), str(txid).strip())


def is_treasury_deposit_recorded(txid: str) -> bool:
    """True if treasury_deposit ledger row exists for txid."""
    if not (txid or "").strip():
        return False
    txid = str(txid).strip()
    with _LEDGER_LOCK:
        return any(
            e.get("type") == "treasury_deposit" and (e.get("txid") or "").strip() == txid
            for e in _read_entries_unlocked()
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


def ledger_entry_count() -> int:
    """Ops/tests helper: total ledger rows under lock."""
    with _LEDGER_LOCK:
        return len(_read_entries_unlocked())
