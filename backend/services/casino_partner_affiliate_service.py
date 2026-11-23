"""
Partner / streamer affiliate codes for casino traffic.

Named codes (e.g. TWITCH-NOVA) map onto Invite Party referrer accounts + UTM.
Clicks and signups tracked without changing RTP.
"""
from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PARTNERS_PATH = os.path.join(_BASE, "data", "casino_partner_affiliates.json")
_STATS_PATH = os.path.join(_BASE, "logs", "casino_social", "partner_affiliate_stats.json")

_CODE_RE = re.compile(r"^[A-Z0-9][A-Z0-9\-_]{1,31}$")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else _BASE, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _empty_catalog() -> Dict[str, Any]:
    return {
        "version": 1,
        "updated_at": None,
        "partners": [],
    }


def _empty_stats() -> Dict[str, Any]:
    return {"clicks": {}, "signups": {}, "events": []}


def load_catalog() -> Dict[str, Any]:
    data = _load_json(_PARTNERS_PATH, _empty_catalog())
    if not isinstance(data.get("partners"), list):
        data["partners"] = []
    return data


def save_catalog(data: Dict[str, Any]) -> None:
    data["updated_at"] = _iso()
    _save_json(_PARTNERS_PATH, data)


def normalize_code(code: str) -> str:
    return (code or "").strip().upper().replace(" ", "")


def get_partner(code: str) -> Optional[Dict[str, Any]]:
    clean = normalize_code(code)
    if not clean:
        return None
    for row in load_catalog().get("partners") or []:
        if not isinstance(row, dict):
            continue
        if normalize_code(row.get("code") or "") == clean and row.get("active", True):
            return row
    return None


def list_partners(*, include_inactive: bool = False) -> Dict[str, Any]:
    rows = []
    for row in load_catalog().get("partners") or []:
        if not isinstance(row, dict):
            continue
        if not include_inactive and not row.get("active", True):
            continue
        rows.append(row)
    return {"success": True, "partners": rows, "count": len(rows)}


def upsert_partner(
    *,
    code: str,
    partner_id: str,
    display_name: str,
    referrer_user_id: str,
    utm_source: str = "partner",
    utm_medium: str = "streamer",
    utm_campaign: str = "casino_traffic",
    active: bool = True,
    notes: str = "",
) -> Dict[str, Any]:
    clean = normalize_code(code)
    if not _CODE_RE.match(clean):
        return {"success": False, "error": "invalid_code"}
    if not (referrer_user_id or "").strip():
        return {"success": False, "error": "referrer_user_id required"}
    if not (partner_id or "").strip():
        partner_id = clean.lower()
    with _LOCK:
        cat = load_catalog()
        partners = cat.setdefault("partners", [])
        found = None
        for row in partners:
            if normalize_code(row.get("code") or "") == clean:
                found = row
                break
        payload = {
            "code": clean,
            "partner_id": (partner_id or "").strip(),
            "display_name": (display_name or clean).strip(),
            "referrer_user_id": referrer_user_id.strip(),
            "utm_source": (utm_source or "partner").strip(),
            "utm_medium": (utm_medium or "streamer").strip(),
            "utm_campaign": (utm_campaign or "casino_traffic").strip(),
            "active": bool(active),
            "notes": (notes or "").strip(),
            "updated_at": _iso(),
        }
        if found:
            found.update(payload)
        else:
            payload["created_at"] = _iso()
            partners.append(payload)
        # Keep Invite Party codes map in sync
        try:
            from backend.services.casino_social_service import (
                _CASINO_REFERRALS_PATH,
                _empty_referral_store,
                _load_json_store,
                _save_json_store,
            )

            store = _load_json_store(_CASINO_REFERRALS_PATH, _empty_referral_store())
            codes = store.setdefault("codes", {})
            codes[clean] = referrer_user_id.strip()
            _save_json_store(_CASINO_REFERRALS_PATH, store)
        except Exception:
            pass
        save_catalog(cat)
    return {"success": True, "partner": payload}


def resolve_code(code: str) -> Dict[str, Any]:
    """Resolve partner or fall through to Invite Party MN- codes."""
    clean = normalize_code(code)
    partner = get_partner(clean)
    if partner:
        return {
            "success": True,
            "kind": "partner",
            "code": clean,
            "partner": partner,
            "referrer_user_id": partner.get("referrer_user_id"),
            "utm": {
                "utm_source": partner.get("utm_source") or "partner",
                "utm_medium": partner.get("utm_medium") or "streamer",
                "utm_campaign": partner.get("utm_campaign") or "casino_traffic",
                "utm_content": partner.get("partner_id") or clean,
            },
            "cta_url": (
                f"/casino/?ref={clean}"
                f"&utm_source={partner.get('utm_source') or 'partner'}"
                f"&utm_medium={partner.get('utm_medium') or 'streamer'}"
                f"&utm_campaign={partner.get('utm_campaign') or 'casino_traffic'}"
                f"&utm_content={partner.get('partner_id') or clean}"
                f"#casino-fund-play"
            ),
        }
    return {
        "success": True,
        "kind": "referral" if clean.startswith("MN-") or clean else "unknown",
        "code": clean or None,
        "partner": None,
        "referrer_user_id": None,
        "utm": {
            "utm_source": "referral",
            "utm_medium": "invite_party",
            "utm_campaign": "casino_traffic",
        },
    }


def track_click(code: str, *, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    clean = normalize_code(code)
    if not clean:
        return {"success": False, "error": "code required"}
    with _LOCK:
        stats = _load_json(_STATS_PATH, _empty_stats())
        clicks = stats.setdefault("clicks", {})
        clicks[clean] = int(clicks.get(clean) or 0) + 1
        events = stats.setdefault("events", [])
        events.append({
            "type": "click",
            "code": clean,
            "at": _iso(),
            "meta": meta or {},
        })
        stats["events"] = events[-500:]
        _save_json(_STATS_PATH, stats)
    return {"success": True, "code": clean, "clicks": clicks[clean]}


def track_signup(code: str, *, referred_user_id: str) -> Dict[str, Any]:
    clean = normalize_code(code)
    if not clean:
        return {"success": False, "error": "code required"}
    with _LOCK:
        stats = _load_json(_STATS_PATH, _empty_stats())
        signups = stats.setdefault("signups", {})
        signups[clean] = int(signups.get(clean) or 0) + 1
        events = stats.setdefault("events", [])
        events.append({
            "type": "signup",
            "code": clean,
            "referred_user_id": referred_user_id,
            "at": _iso(),
        })
        stats["events"] = events[-500:]
        _save_json(_STATS_PATH, stats)
    return {"success": True, "code": clean, "signups": signups[clean]}


def partner_stats(code: str) -> Dict[str, Any]:
    clean = normalize_code(code)
    partner = get_partner(clean)
    stats = _load_json(_STATS_PATH, _empty_stats())
    return {
        "success": True,
        "code": clean,
        "partner": partner,
        "clicks": int((stats.get("clicks") or {}).get(clean) or 0),
        "signups": int((stats.get("signups") or {}).get(clean) or 0),
        "invite_path": f"/r/{clean}",
    }


def enrich_referral_landing(payload: Dict[str, Any], code: str) -> Dict[str, Any]:
    """Merge partner metadata into Invite Party landing response."""
    resolved = resolve_code(code)
    out = dict(payload or {})
    if resolved.get("kind") == "partner" and resolved.get("partner"):
        p = resolved["partner"]
        out["partner"] = {
            "code": p.get("code"),
            "partner_id": p.get("partner_id"),
            "display_name": p.get("display_name"),
        }
        out["utm"] = resolved.get("utm")
        out["cta_url"] = resolved.get("cta_url") or out.get("cta_url")
        if not out.get("valid"):
            out["valid"] = True
        if not out.get("referrer_display"):
            out["referrer_display"] = p.get("display_name") or "Partner host"
        track_click(code, meta={"source": "landing"})
    return out
