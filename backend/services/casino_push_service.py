"""
Casino Web Push — free daily flip reminders + jackpot spikes.

Subscriptions stored under logs/casino_social/push_subscriptions.json.
Uses pywebpush when installed; otherwise generates VAPID keys and dry-runs sends.
"""
from __future__ import annotations

import base64
import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SUBS_PATH = os.path.join(_BASE, "logs", "casino_social", "push_subscriptions.json")
_VAPID_PATH = os.path.join(_BASE, "data", "casino_vapid_keys.json")
_LOG_PATH = os.path.join(_BASE, "logs", "casino_social", "push_sent.jsonl")


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


def _append_log(row: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    with _LOCK:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def ensure_vapid_keys() -> Dict[str, str]:
    """Return VAPID public/private keys — env wins, else generate once to data/."""
    pub = (os.environ.get("VAPID_PUBLIC_KEY") or "").strip()
    priv = (os.environ.get("VAPID_PRIVATE_KEY") or "").strip()
    subject = (os.environ.get("VAPID_SUBJECT") or "mailto:ops@masternoder.dk").strip()
    if pub and priv:
        return {"public_key": pub, "private_key": priv, "subject": subject, "source": "env"}

    stored = _load_json(_VAPID_PATH, {})
    if isinstance(stored, dict) and stored.get("public_key") and stored.get("private_key"):
        return {
            "public_key": stored["public_key"],
            "private_key": stored["private_key"],
            "subject": stored.get("subject") or subject,
            "source": "file",
        }

    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization

    key = ec.generate_private_key(ec.SECP256R1())
    priv_bytes = key.private_numbers().private_value.to_bytes(32, "big")
    pub_numbers = key.public_key().public_numbers()
    pub_bytes = b"\x04" + pub_numbers.x.to_bytes(32, "big") + pub_numbers.y.to_bytes(32, "big")
    row = {
        "public_key": _b64url(pub_bytes),
        "private_key": _b64url(priv_bytes),
        "subject": subject,
        "created_at": _iso(),
    }
    _save_json(_VAPID_PATH, row)
    return {**row, "source": "generated"}


def get_vapid_public_key() -> Dict[str, Any]:
    keys = ensure_vapid_keys()
    return {
        "success": True,
        "public_key": keys["public_key"],
        "subject": keys.get("subject"),
        "configured": True,
    }


def _subs_store() -> Dict[str, Any]:
    data = _load_json(_SUBS_PATH, {"subscriptions": {}})
    if not isinstance(data.get("subscriptions"), dict):
        data["subscriptions"] = {}
    return data


def subscribe(user_id: str, subscription: Dict[str, Any]) -> Dict[str, Any]:
    uid = (user_id or "").strip() or "anonymous"
    if not isinstance(subscription, dict):
        return {"success": False, "error": "subscription required"}
    endpoint = (subscription.get("endpoint") or "").strip()
    keys = subscription.get("keys") if isinstance(subscription.get("keys"), dict) else {}
    if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
        return {"success": False, "error": "invalid_subscription"}
    with _LOCK:
        store = _subs_store()
        by_user = store["subscriptions"].setdefault(uid, [])
        by_user = [s for s in by_user if isinstance(s, dict) and s.get("endpoint") != endpoint]
        by_user.append({
            "endpoint": endpoint,
            "keys": {"p256dh": keys["p256dh"], "auth": keys["auth"]},
            "expirationTime": subscription.get("expirationTime"),
            "subscribed_at": _iso(),
        })
        store["subscriptions"][uid] = by_user[-8:]
        # endpoint index for broadcasts
        endpoints = store.setdefault("by_endpoint", {})
        endpoints[endpoint] = uid
        _save_json(_SUBS_PATH, store)
    return {"success": True, "user_id": uid, "endpoint_count": len(store["subscriptions"][uid])}


def unsubscribe(user_id: str, endpoint: Optional[str] = None) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    with _LOCK:
        store = _subs_store()
        if not uid:
            return {"success": False, "error": "user_id required"}
        rows = store["subscriptions"].get(uid) or []
        if endpoint:
            kept = [s for s in rows if s.get("endpoint") != endpoint]
            store["subscriptions"][uid] = kept
            (store.get("by_endpoint") or {}).pop(endpoint, None)
        else:
            for s in rows:
                (store.get("by_endpoint") or {}).pop(s.get("endpoint"), None)
            store["subscriptions"].pop(uid, None)
        _save_json(_SUBS_PATH, store)
    return {"success": True, "user_id": uid}


def _webpush_send(subscription: Dict[str, Any], payload: str) -> Dict[str, Any]:
    keys = ensure_vapid_keys()
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        return {"ok": False, "error": "pywebpush_missing", "dry_run": True}

    try:
        webpush(
            subscription_info={
                "endpoint": subscription["endpoint"],
                "keys": subscription["keys"],
            },
            data=payload,
            vapid_private_key=keys["private_key"],
            vapid_claims={"sub": keys.get("subject") or "mailto:ops@masternoder.dk"},
            vapid_public_key=keys["public_key"],
        )
        return {"ok": True}
    except Exception as exc:  # includes WebPushException
        return {"ok": False, "error": str(exc)[:300]}


def send_to_user(
    user_id: str,
    *,
    title: str,
    body: str,
    url: str = "/casino/",
    tag: str = "casino",
) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    store = _subs_store()
    rows = list(store.get("subscriptions", {}).get(uid) or [])
    if not rows:
        return {"success": True, "delivered": 0, "reason": "no_subscriptions", "user_id": uid}
    payload = json.dumps({"title": title, "body": body, "url": url, "tag": tag})
    delivered = 0
    errors: List[str] = []
    dry = False
    for sub in rows:
        out = _webpush_send(sub, payload)
        if out.get("ok"):
            delivered += 1
        else:
            if out.get("dry_run"):
                dry = True
            errors.append(out.get("error") or "send_failed")
    _append_log({
        "at": _iso(),
        "user_id": uid,
        "title": title,
        "delivered": delivered,
        "attempted": len(rows),
        "dry_run": dry,
        "tag": tag,
    })
    return {
        "success": True,
        "user_id": uid,
        "delivered": delivered,
        "attempted": len(rows),
        "dry_run": dry,
        "errors": errors[:5],
    }


def broadcast(
    *,
    title: str,
    body: str,
    url: str = "/casino/",
    tag: str = "casino",
    prefer_pref: Optional[str] = None,
) -> Dict[str, Any]:
    """Send to all subscribers; optional prefer_pref filters casino social prefs."""
    from backend.services import casino_social_service

    store = _subs_store()
    delivered = attempted = 0
    dry = False
    for uid, rows in (store.get("subscriptions") or {}).items():
        if prefer_pref:
            prefs = casino_social_service.get_preferences(uid)
            if not prefs.get(prefer_pref):
                continue
        out = send_to_user(uid, title=title, body=body, url=url, tag=tag)
        delivered += int(out.get("delivered") or 0)
        attempted += int(out.get("attempted") or 0)
        dry = dry or bool(out.get("dry_run"))
    return {
        "success": True,
        "delivered": delivered,
        "attempted": attempted,
        "dry_run": dry,
        "title": title,
        "tag": tag,
    }


def notify_free_daily_available() -> Dict[str, Any]:
    return broadcast(
        title="Free daily flip is ready",
        body="Claim your free coin flip in the casino lounge.",
        url="/casino/?tab=home&utm_source=push&utm_medium=free_daily&utm_campaign=casino_traffic#casino-daily",
        tag="free-daily",
        prefer_pref="push_free_daily",
    )


def notify_jackpot_spike(
    *,
    currency: str,
    amount: float,
    reason: str = "jackpot",
) -> Dict[str, Any]:
    label = f"{amount:g} {currency.upper()}"
    return broadcast(
        title=f"Jackpot spike — {label}",
        body=f"A progressive pool just moved ({reason}). Jump in.",
        url="/casino/?tab=slots&utm_source=push&utm_medium=jackpot&utm_campaign=casino_traffic",
        tag="jackpot",
        prefer_pref="push_jackpot",
    )


def on_jackpot_push_hook(
    *,
    user_id: str,
    currency: str,
    amount: float,
    reason: str,
) -> None:
    """Best-effort hook from on_jackpot_win — broadcast + winner ping."""
    try:
        notify_jackpot_spike(currency=currency, amount=amount, reason=reason)
    except Exception:
        pass
    try:
        send_to_user(
            user_id,
            title="You hit a jackpot!",
            body=f"{amount:g} {currency.upper()} credited — share the win.",
            url="/casino/?utm_source=push&utm_medium=jackpot_win&utm_campaign=casino_traffic",
            tag="jackpot-win",
        )
    except Exception:
        pass
