"""Camgirls Phase 1 — catalog, unlock, tip, age gate, chat."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services.studio_floor_service import performer_link

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PERFORMERS_FILE = os.path.join(_ROOT, "data", "camgirls_performers.json")
_UNLOCKS_FILE = os.path.join(_ROOT, "data", "camgirls_unlocks.json")
_AGE_FILE = os.path.join(_ROOT, "data", "camgirls_age_verified.json")
_TIPS_FILE = os.path.join(_ROOT, "data", "camgirls_tips.jsonl")
_CHAT_FILE = os.path.join(_ROOT, "data", "camgirls_chat.jsonl")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _append_jsonl(path: str, row: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def _points():
    from backend.services.unified_points_database import unified_points_db
    return unified_points_db


def _load_performers_from_json() -> List[Dict[str, Any]]:
    data = _read_json(_PERFORMERS_FILE, {"performers": []})
    rows = data.get("performers") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return []
    return [p for p in rows if isinstance(p, dict) and p.get("active", True)]


def _load_performers_raw() -> List[Dict[str, Any]]:
    from backend.services.camgirls_catalog_db_service import catalog_source_mode, load_performers_from_db

    json_rows = _load_performers_from_json()
    mode = catalog_source_mode()
    if mode == "json":
        return json_rows
    if mode == "db":
        db_rows = load_performers_from_db() or []
        return [p for p in db_rows if isinstance(p, dict) and p.get("active", True)] or json_rows
    if json_rows:
        return json_rows
    db_rows = load_performers_from_db() or []
    return [p for p in db_rows if isinstance(p, dict) and p.get("active", True)]


def _get_performer(performer_id: str) -> Optional[Dict[str, Any]]:
    return get_performer_row(performer_id)


def get_performer_row(performer_id: str) -> Optional[Dict[str, Any]]:
    for p in _load_performers_raw():
        if str(p.get("id")) == performer_id:
            return p
    return None


def _is_age_verified(user_id: str) -> bool:
    data = _read_json(_AGE_FILE, {})
    return bool(data.get(user_id))


def _is_unlocked(user_id: str, performer_id: str) -> bool:
    data = _read_json(_UNLOCKS_FILE, {})
    return performer_id in (data.get(user_id) or [])


def _debit_mn2(user_id: str, amount: float, source: str, meta: Optional[dict] = None) -> Dict[str, Any]:
    db = _points()
    if not db:
        return {"success": False, "error": "points unavailable"}
    bal = db.get_all_points(user_id)
    current = float((bal.get("points") or {}).get("mn2_balance") or 0)
    if current < amount:
        return {"success": False, "error": "insufficient_mn2", "code": "insufficient_mn2"}
    return db.add_points(user_id, "mn2_balance", -amount, source, meta or {})


def list_performers_catalog(user_id: str = "default_user", lite: bool = False) -> Dict[str, Any]:
    performers = []
    tech_ctx = None
    if not lite:
        try:
            from backend.services.camgirls_status_service import paypal_configured, studio_tech_for_performer
            from backend.services.camgirls_livekit_service import public_status as livekit_status

            tech_ctx = (livekit_status(), paypal_configured())
        except Exception:
            tech_ctx = None
    for p in _load_performers_raw():
        row = {
            "id": p.get("id"),
            "display_name": p.get("display_name"),
            "bio": p.get("bio"),
            "tagline": p.get("tagline"),
            "avatar_url": p.get("avatar_url"),
            "unlock_price_mn2": p.get("unlock_price_mn2", 10),
            "tip_min_mn2": p.get("tip_min_mn2", 5),
            "unlocked": _is_unlocked(user_id, str(p.get("id"))),
            "age_verified": _is_age_verified(user_id),
        }
        try:
            from backend.services.camgirls_social_service import is_fan_club_member

            row["fan_club"] = is_fan_club_member(user_id, str(p.get("id")))
        except Exception:
            row["fan_club"] = False
        if not lite:
            row["chat_price_mn2"] = p.get("chat_price_mn2", 2)
            row["goal_mn2"] = p.get("goal_mn2", 100)
            row["ai_enabled"] = bool(p.get("ai_enabled", True))
            try:
                from backend.services.camgirls_media_service import card_avatar_url

                row["avatar_url"] = card_avatar_url(
                    str(p.get("id") or ""),
                    str(p.get("avatar_url") or ""),
                )
            except Exception:
                pass
            if tech_ctx:
                livekit, paypal_on = tech_ctx
                row["tech"] = studio_tech_for_performer(p, livekit=livekit, paypal_on=paypal_on)
            else:
                row["tech"] = {"ai_enabled": row["ai_enabled"], "online": True}
        try:
            from backend.services.camgirls_media_service import attach_media_to_row

            row = attach_media_to_row(row, lite=lite)
        except Exception:
            pass
        media = row.get("media") if isinstance(row.get("media"), dict) else {}
        picture = str(
            (media or {}).get("picture_url")
            or row.get("icon_url")
            or row.get("avatar_url")
            or ""
        )
        row["floor"] = performer_link(str(p.get("id") or ""), picture_url=picture)
        performers.append(row)
    return {"success": True, "performers": performers, "count": len(performers)}


def list_active_performer_ids() -> List[str]:
    return [str(p.get("id")) for p in _load_performers_raw() if p.get("id")]


def get_performer_detail(performer_id: str, user_id: str = "default_user") -> Dict[str, Any]:
    pid = (performer_id or "").strip()
    if not pid:
        return {"success": False, "error": "performer_id_required"}
    catalog = list_performers_catalog(user_id=user_id, lite=False)
    for row in catalog.get("performers") or []:
        if str(row.get("id")) == pid:
            return {"success": True, "performer": row}
    if not _get_performer(pid):
        return {"success": False, "error": "performer_not_found"}
    return {"success": False, "error": "performer_not_found"}


def record_age_verification(user_id: str, birth_year: int) -> Dict[str, Any]:
    year = int(birth_year)
    age = datetime.now(timezone.utc).year - year
    if age < 18:
        return {"success": False, "error": "under_18", "code": "under_18"}
    data = _read_json(_AGE_FILE, {})
    data[user_id] = {"birth_year": year, "verified_at": _iso()}
    _write_json(_AGE_FILE, data)
    return {"success": True}


def unlock_performer(user_id: str, performer_id: str) -> Dict[str, Any]:
    if not _is_age_verified(user_id):
        return {"success": False, "code": "age_verification_required", "error": "18+ required"}
    p = _get_performer(performer_id)
    if not p:
        return {"success": False, "error": "performer_not_found"}
    if _is_unlocked(user_id, performer_id):
        return {"success": True, "already_unlocked": True, "amount_mn2": 0}
    price = float(p.get("unlock_price_mn2") or 10)
    debit = _debit_mn2(user_id, price, "camgirls_unlock", {"performer_id": performer_id})
    if not debit.get("success", True) and debit.get("error"):
        return debit
    data = _read_json(_UNLOCKS_FILE, {})
    data.setdefault(user_id, [])
    if performer_id not in data[user_id]:
        data[user_id].append(performer_id)
    _write_json(_UNLOCKS_FILE, data)
    return {"success": True, "amount_mn2": price, "performer_id": performer_id}


def tip_performer(
    user_id: str,
    performer_id: str,
    amount: float,
    *,
    gift_id: Optional[str] = None,
    dance_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not _is_age_verified(user_id):
        return {"success": False, "code": "age_verification_required"}
    p = _get_performer(performer_id)
    if not p:
        return {"success": False, "error": "performer_not_found"}
    amt = float(amount)
    if amt < float(p.get("tip_min_mn2") or 5):
        return {"success": False, "error": "below_minimum"}
    meta = {"performer_id": performer_id}
    if gift_id:
        meta["gift_id"] = gift_id
    if dance_id:
        meta["dance_id"] = dance_id
    debit = _debit_mn2(user_id, amt, "camgirls_tip", meta)
    if debit.get("error"):
        return debit
    from backend.services.camgirls_payout_service import get_payout_address
    payout = get_payout_address(performer_id)
    row = {"user_id": user_id, "performer_id": performer_id, "amount_mn2": amt, "created_at": _iso()}
    if gift_id:
        row["gift_id"] = gift_id
    if dance_id:
        row["dance_id"] = dance_id
    _append_jsonl(_TIPS_FILE, row)
    return {"success": True, "amount_mn2": amt, "payout_address": payout.get("address")}


def get_performer(performer_id: str) -> Optional[Dict[str, Any]]:
    return _get_performer(performer_id)


def user_has_unlock(user_id: str, performer_id: str) -> bool:
    return _is_unlocked(user_id, performer_id)


def chat_with_performer(user_id: str, performer_id: str, message: str) -> Dict[str, Any]:
    if not _is_age_verified(user_id):
        return {"success": False, "code": "age_verification_required"}
    if not _is_unlocked(user_id, performer_id):
        return {"success": False, "code": "unlock_required"}
    p = _get_performer(performer_id)
    if not p:
        return {"success": False, "error": "performer_not_found"}
    price = float(p.get("chat_price_mn2") or 2)
    debit = _debit_mn2(user_id, price, "camgirls_chat", {"performer_id": performer_id})
    if debit.get("error"):
        return debit
    from backend.services.camgirls_agents_service import persona_system_prompt
    system, task_kind = persona_system_prompt(p)
    reply = "Thanks for chatting!"
    try:
        from backend.services import agent_ai_router
        resp, _trace = agent_ai_router.routed_chat(
            [{"role": "system", "content": system}, {"role": "user", "content": message}],
            task_kind,
            user_id,
        )
        if getattr(resp, "content", None):
            reply = resp.content
        elif isinstance(resp, dict):
            reply = resp.get("content") or reply
    except Exception:
        reply = f"Hey! {p.get('display_name', 'I')} heard: {message[:120]}"
    _append_jsonl(_CHAT_FILE, {
        "user_id": user_id,
        "performer_id": performer_id,
        "message": message,
        "reply": reply,
        "amount_mn2": price,
        "created_at": _iso(),
    })
    return {"success": True, "reply": reply, "amount_mn2": price}


def iter_chat_stream(user_id: str, performer_id: str, message: str):
    """SSE-friendly chunks after a single billed chat_with_performer call."""
    result = chat_with_performer(user_id, performer_id, message)
    if not result.get("success"):
        yield {
            "type": "error",
            "error": result.get("error"),
            "code": result.get("code"),
        }
        return
    reply = str(result.get("reply") or "")
    yield {"type": "start", "amount_mn2": result.get("amount_mn2")}
    for part in reply.split():
        yield {"type": "token", "text": part + " "}
    yield {"type": "done", "reply": reply, "amount_mn2": result.get("amount_mn2")}


def get_chat_history(user_id: str, performer_id: str, limit: int = 30) -> Dict[str, Any]:
    if not os.path.isfile(_CHAT_FILE):
        return {"success": True, "messages": []}
    rows = []
    with open(_CHAT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if row.get("user_id") == user_id and row.get("performer_id") == performer_id:
                rows.append(row)
    return {"success": True, "messages": rows[-limit:]}


def upsert_performer(row: Dict[str, Any]) -> Dict[str, Any]:
    """Merge one performer into camgirls_performers.json (ops onboarding)."""
    if not isinstance(row, dict):
        return {"success": False, "error": "invalid_row"}
    pid = str(row.get("id") or "").strip()
    if not pid:
        return {"success": False, "error": "id_required"}
    data = _read_json(_PERFORMERS_FILE, {"performers": []})
    performers = data.get("performers") if isinstance(data, dict) else []
    if not isinstance(performers, list):
        performers = []
    merged = None
    out: List[Dict[str, Any]] = []
    for p in performers:
        if not isinstance(p, dict):
            continue
        if str(p.get("id")) == pid:
            merged = {**p, **row, "id": pid}
            out.append(merged)
        else:
            out.append(p)
    if merged is None:
        merged = dict(row)
        merged["id"] = pid
        out.append(merged)
    _write_json(_PERFORMERS_FILE, {"performers": out})
    db_synced = False
    try:
        from backend.services.camgirls_catalog_sync_service import upsert_performer_db

        db_synced = upsert_performer_db(merged or dict(row))
    except Exception:
        db_synced = False
    payout_hint: Dict[str, Any] = {"catalog_db_synced": db_synced}
    try:
        from backend.services.camgirls_payout_service import get_payout_address, provision_paypal_for_performers

        provision_paypal_for_performers(performer_ids=[pid])
        pa = get_payout_address(pid)
        if pa.get("address"):
            payout_hint["payout_address"] = pa.get("address")
        elif pa.get("paypal_checkout_enabled"):
            payout_hint["payout_warning"] = "mn2_address_pending"
    except Exception:
        pass
    return {"success": True, "performer_id": pid, **payout_hint}


def deactivate_demo_performers() -> Dict[str, Any]:
    data = _read_json(_PERFORMERS_FILE, {"performers": []})
    rows = data.get("performers") if isinstance(data, dict) else []
    count = 0
    for p in rows:
        pid = str(p.get("id") or "")
        if pid.startswith("performer_demo_") and p.get("active", True):
            p["active"] = False
            count += 1
    _write_json(_PERFORMERS_FILE, data if isinstance(data, dict) else {"performers": rows})
    return {"success": True, "count": count}


# Restored from pre-merge branch so both APIs stay callable.
def fulfill_external_payment(
    user_id: str,
    performer_id: str,
    action: str,
    amount_mn2: float,
    *,
    payment_ref: str = "",
    gift_id: Optional[str] = None,
    minutes: Optional[int] = None,
) -> Dict[str, Any]:
    """Grant unlock/tip/gift/fan club/private after PayPal capture (no MN2 debit)."""
    if not _is_age_verified(user_id):
        return {"success": False, "code": "age_verification_required"}
    p = _get_performer(performer_id)
    if not p:
        return {"success": False, "error": "performer_not_found"}
    action = (action or "unlock").strip().lower()
    meta = {"performer_id": performer_id, "payment_ref": payment_ref, "method": "paypal"}
    if action == "unlock":
        if _is_unlocked(user_id, performer_id):
            return {"success": True, "already_unlocked": True}
        data = _read_json(_UNLOCKS_FILE, {})
        data.setdefault(user_id, [])
        if performer_id not in data[user_id]:
            data[user_id].append(performer_id)
        _write_json(_UNLOCKS_FILE, data)
        return {"success": True, "action": "unlock", "performer_id": performer_id}
    if action in ("tip", "gift"):
        amt = float(amount_mn2 or 0)
        _append_jsonl(_TIPS_FILE, {
            "user_id": user_id,
            "performer_id": performer_id,
            "amount_mn2": amt,
            "gift_id": gift_id,
            "payment_method": "paypal",
            "payment_ref": payment_ref,
            "created_at": _iso(),
        })
        return {"success": True, "action": action, "amount_mn2": amt, **meta}
    if action == "fan_club":
        from backend.services.camgirls_social_service import grant_fan_club

        out = grant_fan_club(user_id, performer_id)
        if out.get("success"):
            out["payment_method"] = "paypal"
            out["payment_ref"] = payment_ref
        return out
    if action in ("private_show", "private"):
        from backend.services.camgirls_social_service import grant_private_show

        out = grant_private_show(user_id, performer_id, int(minutes or 5))
        if out.get("success"):
            out["payment_method"] = "paypal"
            out["payment_ref"] = payment_ref
        return out
    return {"success": False, "error": "invalid_action"}

