"""
User ↔ MN2 wallet directory: clone/copy detection, bulk provisioning, table export.
"""
from __future__ import annotations

import os
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_POINTS_DIR = os.path.join(_BASE, "logs", "unified_points")


def _is_system_user(user_id: str) -> bool:
    uid = (user_id or "").strip()
    if not uid or uid.startswith("pool_"):
        return True
    if uid.startswith("agent:") or uid in ("platform_treasury", "agent_treasury", "@agent_treasury"):
        return True
    return False


def _load_db_users_meta(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load user_accounts rows with fields used for clone detection."""
    try:
        from sqlalchemy import text
        from backend.services.user_db_service import _in_app_context, _get_db

        def _run():
            db = _get_db()
            sql = (
                "SELECT user_id, username, email, device_fingerprint, last_ip, "
                "last_login, created_at, role FROM user_accounts ORDER BY created_at DESC"
            )
            if limit:
                sql += f" LIMIT {int(limit)}"
            rows = db.session.execute(text(sql)).fetchall()
            return [
                {
                    "user_id": r[0],
                    "username": r[1],
                    "email": r[2],
                    "device_fingerprint": r[3],
                    "last_ip": r[4],
                    "last_login": str(r[5]) if r[5] else None,
                    "created_at": str(r[6]) if r[6] else None,
                    "role": r[7],
                    "source": "db",
                }
                for r in rows
            ]

        return _in_app_context(_run) or []
    except Exception:
        return []


def _load_points_user_ids() -> Set[str]:
    out: Set[str] = set()
    if not os.path.isdir(_POINTS_DIR):
        return out
    for name in os.listdir(_POINTS_DIR):
        if name.endswith(".json"):
            out.add(name[:-5])
    return out


def _load_wallet_user_ids() -> Set[str]:
    from backend.services.mn2_wallet_service import _load_addresses, _entry_primary

    addresses = _load_addresses()
    out: Set[str] = set()
    for uid, entry in addresses.items():
        if _is_system_user(uid):
            continue
        if _entry_primary(entry):
            out.add(uid)
    return out


def collect_all_user_ids(
    *,
    db_limit: Optional[int] = None,
    include_points: bool = True,
) -> Set[str]:
    """Union of DB accounts, unified_points files, and wallet assignments."""
    uids: Set[str] = set()
    for row in _load_db_users_meta(limit=db_limit):
        uid = (row.get("user_id") or "").strip()
        if uid and not _is_system_user(uid):
            uids.add(uid)
    if include_points:
        uids |= _load_points_user_ids()
    uids |= _load_wallet_user_ids()
    return {u for u in uids if u and not _is_system_user(u)}


def detect_clone_groups(db_rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Map user_id -> clone metadata. Clones/copies share fingerprint, email, or username.
    Each clone is listed separately (doubled in the table, not merged).
    """
    by_fp: Dict[str, List[str]] = defaultdict(list)
    by_email: Dict[str, List[str]] = defaultdict(list)
    by_username: Dict[str, List[str]] = defaultdict(list)
    by_ip: Dict[str, List[str]] = defaultdict(list)

    for row in db_rows:
        uid = (row.get("user_id") or "").strip()
        if not uid:
            continue
        fp = (row.get("device_fingerprint") or "").strip()
        email = (row.get("email") or "").strip().lower()
        uname = (row.get("username") or "").strip().lower()
        ip = (row.get("last_ip") or "").strip()
        if fp and len(fp) > 8:
            by_fp[fp].append(uid)
        if email and "@" in email:
            by_email[email].append(uid)
        if uname and uname != uid.lower():
            by_username[uname].append(uid)
        if ip and ip not in ("127.0.0.1", "unknown"):
            by_ip[ip].append(uid)

    meta: Dict[str, Dict[str, Any]] = {}

    def _apply(groups: Dict[str, List[str]], kind: str) -> None:
        for key, members in groups.items():
            if len(members) < 2:
                continue
            members = sorted(set(members))
            group_id = f"{kind}:{key[:48]}"
            for uid in members:
                row = meta.setdefault(uid, {
                    "is_clone_copy": False,
                    "clone_group": None,
                    "clone_siblings": 0,
                    "clone_reasons": [],
                })
                row["is_clone_copy"] = True
                row["clone_group"] = row["clone_group"] or group_id
                row["clone_siblings"] = max(row["clone_siblings"], len(members))
                if kind not in row["clone_reasons"]:
                    row["clone_reasons"].append(kind)

    _apply(by_fp, "fingerprint")
    _apply(by_email, "email")
    _apply(by_username, "username")
    _apply(by_ip, "ip")

    return meta


def provision_wallets_batch(user_ids: List[str], *, limit: int = 200) -> Dict[str, Any]:
    """Assign full wallet records to users missing one (up to limit per call)."""
    from backend.services.mn2_wallet_service import ensure_user_wallet, _load_addresses, _entry_primary

    cap = max(1, min(int(limit), 500))
    addresses = _load_addresses()
    provisioned = 0
    skipped = 0
    failed = 0
    errors: List[str] = []

    for uid in user_ids[:cap]:
        if _is_system_user(uid):
            skipped += 1
            continue
        entry = addresses.get(uid)
        if entry and _entry_primary(entry):
            skipped += 1
            continue
        res = ensure_user_wallet(uid)
        if res.get("success") and res.get("deposit_address"):
            provisioned += 1
            addresses = _load_addresses()
        else:
            failed += 1
            err = (res.get("error") or "unknown")[:120]
            if len(errors) < 5:
                errors.append(f"{uid}: {err}")

    return {
        "success": True,
        "provisioned": provisioned,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
    }


def build_user_wallet_table(
    *,
    limit: int = 200,
    offset: int = 0,
    search: Optional[str] = None,
    provision: bool = False,
    db_limit: Optional[int] = 20000,
) -> Dict[str, Any]:
    """Table rows: every user (including clone copies) with wallet status."""
    from backend.services.mn2_wallet_service import (
        _load_addresses,
        _entry_primary,
        _all_addresses_for_entry,
    )
    from backend.services.unified_points_database import unified_points_db

    db_rows = _load_db_users_meta(limit=db_limit)
    db_by_id = {r["user_id"]: r for r in db_rows if r.get("user_id")}
    clone_meta = detect_clone_groups(db_rows)

    all_uids = sorted(collect_all_user_ids(db_limit=db_limit), reverse=True)
    q = (search or "").strip().lower()
    if q:
        all_uids = [u for u in all_uids if q in u.lower()]

    total = len(all_uids)
    page_ids = all_uids[offset: offset + limit]

    if provision and page_ids:
        provision_wallets_batch(page_ids, limit=len(page_ids))

    addresses = _load_addresses()
    addr_map = {}
    for uid, entry in addresses.items():
        primary = _entry_primary(entry)
        if primary:
            addr_map[uid] = primary

    rows: List[Dict[str, Any]] = []
    for uid in page_ids:
        db = db_by_id.get(uid) or {}
        cm = clone_meta.get(uid) or {}
        entry = addresses.get(uid)
        primary = _entry_primary(entry) if entry else addr_map.get(uid)
        wallet_ready = bool(primary)
        wallet_type = None
        address_count = 0
        if wallet_ready and isinstance(entry, dict):
            wallet_type = entry.get("wallet_type") or "core"
            address_count = len(_all_addresses_for_entry(entry))
        elif wallet_ready:
            wallet_type = "core"
            address_count = 1

        bal = 0.0
        try:
            raw = unified_points_db._load_file_store(uid)
            systems = raw.get("systems") if isinstance(raw.get("systems"), dict) else {}
            bal = float(systems.get("mn2_balance", 0) or raw.get("mn2_balance", 0) or 0)
        except Exception:
            pass

        sources = []
        if uid in db_by_id:
            sources.append("db")
        if os.path.isfile(os.path.join(_POINTS_DIR, f"{uid}.json")):
            sources.append("points")
        if wallet_ready:
            sources.append("wallet")

        rows.append({
            "user_id": uid,
            "username": db.get("username"),
            "email": db.get("email"),
            "wallet_ready": wallet_ready,
            "wallet_type": wallet_type or ("core" if wallet_ready else None),
            "deposit_address": primary,
            "address_count": address_count,
            "mn2_balance": round(bal, 8),
            "is_clone_copy": bool(cm.get("is_clone_copy")),
            "clone_group": cm.get("clone_group"),
            "clone_siblings": cm.get("clone_siblings") or 0,
            "clone_reasons": cm.get("clone_reasons") or [],
            "sources": sources,
            "last_login": db.get("last_login"),
            "created_at": db.get("created_at"),
        })

    clone_rows = sum(1 for r in rows if r.get("is_clone_copy"))
    wallet_ready_count = sum(1 for r in rows if r.get("wallet_ready"))

    return {
        "success": True,
        "total": total,
        "offset": offset,
        "limit": limit,
        "count": len(rows),
        "clone_copy_count": clone_rows,
        "wallet_ready_count": wallet_ready_count,
        "wallet_missing_count": len(rows) - wallet_ready_count,
        "users": rows,
    }
