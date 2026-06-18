"""Camgirls directory — performer catalog, MN2 unlock/tip (Phase 1)."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PERFORMERS_FILE = os.path.join(_BASE, "data", "camgirls_performers.json")
_UNLOCKS_FILE = os.path.join(_BASE, "data", "camgirls_unlocks.json")
_AGE_FILE = os.path.join(_BASE, "data", "camgirls_age_verified.json")
_TIPS_FILE = os.path.join(_BASE, "data", "camgirls_tips.jsonl")
_CHAT_FILE = os.path.join(_BASE, "data", "camgirls_chat.jsonl")
_DEFAULT_CHAT_PRICE_MN2 = 2.0


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if data is not None else default
    except Exception:
        return default


def _write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _append_jsonl(path: str, row: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_performers_raw() -> List[Dict[str, Any]]:
    data = _read_json(_PERFORMERS_FILE, {"performers": []})
    rows = data.get("performers") if isinstance(data, dict) else []
    if not isinstance(rows, list):
        return []
    out = []
    for row in rows:
        if isinstance(row, dict) and row.get("active", True):
            out.append(row)
    return out


def _public_performer(row: Dict[str, Any], *, unlocked: bool = False) -> Dict[str, Any]:
    agent_id = (row.get("agent_id") or "").strip()
    ai_agent = None
    if not agent_id:
        try:
            from backend.services.camgirls_agents_service import agent_for_performer
            ai_agent = agent_for_performer(str(row.get("id") or ""))
            if ai_agent:
                agent_id = (ai_agent.get("agent_id") or "").strip()
        except Exception:
            pass
    pub = {
        "id": row.get("id"),
        "display_name": row.get("display_name"),
        "tagline": row.get("tagline"),
        "avatar_url": row.get("avatar_url"),
        "unlock_price_mn2": float(row.get("unlock_price_mn2") or 0),
        "tip_min_mn2": float(row.get("tip_min_mn2") or 1),
        "featured": bool(row.get("featured")),
        "unlocked": unlocked,
        "ai_enabled": bool(row.get("ai_enabled", True)),
        "agent_id": agent_id or None,
        "ai_persona": (ai_agent or {}).get("name") or row.get("ai_persona"),
    }
    if unlocked and row.get("preview_url"):
        pub["preview_url"] = row.get("preview_url")
    if unlocked:
        pub["chat_price_mn2"] = float(row.get("chat_price_mn2") or _DEFAULT_CHAT_PRICE_MN2)
    return pub


def get_performer(performer_id: str) -> Optional[Dict[str, Any]]:
    pid = (performer_id or "").strip()
    for row in _load_performers_raw():
        if (row.get("id") or "").strip() == pid:
            return row
    return None


def list_performers_catalog(*, user_id: Optional[str] = None) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    unlocks = _user_unlocks(uid) if uid else {}
    performers = []
    for row in _load_performers_raw():
        pid = (row.get("id") or "").strip()
        performers.append(_public_performer(row, unlocked=bool(unlocks.get(pid))))
    performers.sort(key=lambda p: (not p.get("featured"), p.get("display_name") or ""))
    return {"success": True, "performers": performers, "count": len(performers)}


def get_performer_detail(performer_id: str, *, user_id: str) -> Dict[str, Any]:
    row = get_performer(performer_id)
    if not row:
        return {"success": False, "error": "performer_not_found"}
    uid = (user_id or "").strip()
    unlocked = bool(_user_unlocks(uid).get((row.get("id") or "").strip()))
    detail = _public_performer(row, unlocked=unlocked)
    detail["bio"] = row.get("bio") or ""
    if unlocked:
        detail["content_url"] = row.get("content_url") or row.get("preview_url")
    return {
        "success": True,
        "performer": detail,
        "age_verified": is_age_verified(uid),
    }


def _user_unlocks(user_id: str) -> Dict[str, Any]:
    if not user_id:
        return {}
    data = _read_json(_UNLOCKS_FILE, {})
    block = data.get(user_id) if isinstance(data, dict) else {}
    return block if isinstance(block, dict) else {}


def is_age_verified(user_id: str) -> bool:
    uid = (user_id or "").strip()
    if not uid:
        return False
    data = _read_json(_AGE_FILE, {})
    rec = data.get(uid) if isinstance(data, dict) else None
    return isinstance(rec, dict) and bool(rec.get("verified_at"))


def record_age_verification(user_id: str, *, birth_year: Optional[int] = None) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_required"}
    if birth_year is not None:
        year = int(birth_year)
        if year > datetime.now(timezone.utc).year - 18:
            return {"success": False, "error": "must_be_18_plus"}
    with _LOCK:
        data = _read_json(_AGE_FILE, {})
        if not isinstance(data, dict):
            data = {}
        data[uid] = {"verified_at": _iso(), "birth_year": birth_year}
        _write_json(_AGE_FILE, data)
    return {"success": True, "verified_at": data[uid]["verified_at"]}


def _require_age(user_id: str) -> Optional[Dict[str, Any]]:
    if is_age_verified(user_id):
        return None
    return {"success": False, "error": "age_verification_required", "code": "age_verification_required"}


def _debit_mn2(user_id: str, amount: float, *, source: str, metadata: dict) -> Dict[str, Any]:
    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry

    amt = round(float(amount or 0), 8)
    if amt <= 0:
        return {"success": False, "error": "amount_must_be_positive"}
    pts = unified_points_db.get_all_points(user_id).get("points") or {}
    bal = float(pts.get("mn2_balance") or 0)
    if bal == 0 and isinstance(pts.get("systems"), dict):
        bal = float(pts["systems"].get("mn2_balance") or 0)
    if bal < amt:
        return {"success": False, "error": "insufficient_mn2", "mn2_balance": bal, "required": amt}
    r = unified_points_db.add_points(user_id, "mn2_balance", -amt, source=source, metadata=metadata)
    if not r.get("success", True):
        return {"success": False, "error": "debit_failed"}
    try:
        append_entry(user_id=user_id, entry_type=metadata.get("ledger_type", source), amount=amt, metadata=metadata)
    except Exception:
        pass
    return {"success": True, "amount_mn2": amt}


def unlock_performer(user_id: str, performer_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    gate = _require_age(uid)
    if gate:
        return gate
    row = get_performer(performer_id)
    if not row:
        return {"success": False, "error": "performer_not_found"}
    pid = (row.get("id") or "").strip()
    if _user_unlocks(uid).get(pid):
        return {"success": True, "already_unlocked": True, "performer_id": pid}
    price = float(row.get("unlock_price_mn2") or 0)
    if price <= 0:
        return {"success": False, "error": "unlock_not_for_sale"}
    meta = {
        "ledger_type": "camgirl_unlock",
        "performer_id": pid,
        "display_name": row.get("display_name"),
    }
    debit = _debit_mn2(uid, price, source="camgirl_unlock", metadata=meta)
    if not debit.get("success"):
        return debit
    with _LOCK:
        data = _read_json(_UNLOCKS_FILE, {})
        if not isinstance(data, dict):
            data = {}
        data.setdefault(uid, {})[pid] = {"unlocked_at": _iso(), "amount_mn2": price}
        _write_json(_UNLOCKS_FILE, data)
    try:
        from backend.services.activity_events_service import emit
        emit("camgirl_unlock", channel="camgirls", user_id=uid, payload={"performer_id": pid, "amount_mn2": price})
    except Exception:
        pass
    return {"success": True, "performer_id": pid, "amount_mn2": price, "unlocked_at": data[uid][pid]["unlocked_at"]}


def tip_performer(user_id: str, performer_id: str, amount_mn2: float) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    gate = _require_age(uid)
    if gate:
        return gate
    row = get_performer(performer_id)
    if not row:
        return {"success": False, "error": "performer_not_found"}
    pid = (row.get("id") or "").strip()
    amt = round(float(amount_mn2 or 0), 8)
    tip_min = float(row.get("tip_min_mn2") or 1)
    if amt < tip_min:
        return {"success": False, "error": "below_tip_minimum", "tip_min_mn2": tip_min}
    meta = {
        "ledger_type": "camgirl_tip",
        "performer_id": pid,
        "display_name": row.get("display_name"),
    }
    from backend.services.camgirls_payout_service import get_or_create_payout_address
    payout = get_or_create_payout_address(pid)
    if not payout.get("success"):
        return {
            "success": False,
            "error": payout.get("error") or "payout_address_unavailable",
            "code": "payout_address_unavailable",
        }
    payout_addr = payout.get("payout_address")
    meta["payout_address"] = payout_addr
    debit = _debit_mn2(uid, amt, source="camgirl_tip", metadata=meta)
    if not debit.get("success"):
        return debit
    tip_row = {
        "ts": _iso(),
        "user_id": uid,
        "performer_id": pid,
        "amount_mn2": amt,
        "payout_address": payout_addr,
    }
    with _LOCK:
        _append_jsonl(_TIPS_FILE, tip_row)
    try:
        from backend.services.activity_events_service import emit
        emit("camgirl_tip", channel="camgirls", user_id=uid, payload=tip_row)
    except Exception:
        pass
    return {"success": True, **tip_row}


def deactivate_demo_performers(*, prefix: str = "performer_demo_") -> Dict[str, Any]:
    """Phase 1c — hide demo catalog rows before production go-live."""
    pref = (prefix or "performer_demo_").strip()
    deactivated: List[str] = []
    with _LOCK:
        data = _read_json(_PERFORMERS_FILE, {"performers": []})
        if not isinstance(data, dict):
            data = {"performers": []}
        rows = data.get("performers") if isinstance(data.get("performers"), list) else []
        for row in rows:
            if not isinstance(row, dict):
                continue
            pid = (row.get("id") or "").strip()
            if pid.startswith(pref):
                row["active"] = False
                deactivated.append(pid)
        data["performers"] = rows
        _write_json(_PERFORMERS_FILE, data)
    return {"success": True, "deactivated": deactivated, "count": len(deactivated)}


def upsert_performer(body: Dict[str, Any]) -> Dict[str, Any]:
    pid = (body.get("id") or "").strip()
    if not pid:
        return {"success": False, "error": "id_required"}
    payload = dict(body)
    payload.pop("payout_address", None)
    with _LOCK:
        data = _read_json(_PERFORMERS_FILE, {"performers": []})
        if not isinstance(data, dict):
            data = {"performers": []}
        rows = data.get("performers") if isinstance(data.get("performers"), list) else []
        found = False
        for i, row in enumerate(rows):
            if (row.get("id") or "").strip() == pid:
                merged = {**row, **payload, "id": pid}
                merged.pop("payout_address", None)
                rows[i] = merged
                found = True
                break
        if not found:
            new_row = {**payload, "id": pid, "active": payload.get("active", True)}
            new_row.pop("payout_address", None)
            rows.append(new_row)
        data["performers"] = rows
        _write_json(_PERFORMERS_FILE, data)
    try:
        from backend.services.camgirls_payout_service import get_or_create_payout_address
        payout = get_or_create_payout_address(pid)
    except Exception:
        payout = {"success": False}
    out = {"success": True, "performer_id": pid}
    if payout.get("success"):
        out["payout_address"] = payout.get("payout_address")
        out["payout_created"] = bool(payout.get("created"))
    elif payout.get("error"):
        out["payout_warning"] = payout.get("error")
    return out


def chat_with_performer(user_id: str, performer_id: str, message: str) -> Dict[str, Any]:
    """Phase 2 — text chat with performer persona; debits MN2 per message."""
    uid = (user_id or "").strip()
    msg = (message or "").strip()
    if not uid:
        return {"success": False, "error": "user_required"}
    if not msg:
        return {"success": False, "error": "message_required"}
    if len(msg) > 2000:
        return {"success": False, "error": "message_too_long"}
    gate = _require_age(uid)
    if gate:
        return gate
    row = get_performer(performer_id)
    if not row:
        return {"success": False, "error": "performer_not_found"}
    pid = (row.get("id") or "").strip()
    if not _user_unlocks(uid).get(pid):
        return {"success": False, "error": "unlock_required", "code": "unlock_required"}
    price = float(row.get("chat_price_mn2") or _DEFAULT_CHAT_PRICE_MN2)
    meta = {
        "ledger_type": "camgirl_chat",
        "performer_id": pid,
        "display_name": row.get("display_name"),
        "message_preview": msg[:120],
    }
    debit = _debit_mn2(uid, price, source="camgirl_chat", metadata=meta)
    if not debit.get("success"):
        return debit

    name = row.get("display_name") or pid
    try:
        from backend.services.camgirls_agents_service import persona_system_prompt
        system, llm_task = persona_system_prompt(row)
    except Exception:
        bio = row.get("bio") or row.get("tagline") or ""
        system = (
            f"You are {name}, a performer on MasterNoder.dk camgirls catalog. "
            f"Stay in character. Bio: {bio}. "
            "Reply in 1-3 short sentences. Be warm and playful; no explicit content."
        )
        llm_task = "speed"
    reply = ""
    try:
        from backend.services.llm_service import chat
        resp = chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": msg},
            ],
            task_type=llm_task,
            max_tokens=180,
            temperature=0.85,
        )
        if resp.success:
            reply = (resp.content or "").strip()
    except Exception:
        pass
    if not reply:
        reply = f"Hey! Thanks for the message. I'm {name} — more chat features coming soon."

    chat_row = {
        "ts": _iso(),
        "user_id": uid,
        "performer_id": pid,
        "message": msg,
        "reply": reply,
        "amount_mn2": price,
    }
    with _LOCK:
        _append_jsonl(_CHAT_FILE, chat_row)
    try:
        from backend.services.activity_events_service import emit
        emit("camgirl_chat", channel="camgirls", user_id=uid, payload={"performer_id": pid, "amount_mn2": price})
    except Exception:
        pass
    linked_agent_id = (row.get("agent_id") or "").strip()
    if not linked_agent_id:
        try:
            from backend.services.camgirls_agents_service import agent_for_performer
            linked_agent_id = (agent_for_performer(pid) or {}).get("agent_id") or ""
        except Exception:
            linked_agent_id = ""
    return {
        "success": True,
        "performer_id": pid,
        "reply": reply,
        "amount_mn2": price,
        "chat_price_mn2": price,
        "agent_id": linked_agent_id or None,
        "ai_powered": True,
    }
