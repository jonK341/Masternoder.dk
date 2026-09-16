"""Facebook Messenger casino bot — webhook verify, FAQ replies, Graph API send."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import urllib.error
import urllib.request
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "facebook_casino_bot_config.json")
_BASE_URL = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")

_last_event: Dict[str, Any] = {"processed": 0, "last_sender": None, "last_text": None}


def _app_secret() -> str:
    return (
        os.environ.get("FACEBOOK_APP_SECRET")
        or os.environ.get("FACEBOOK_CLIENT_SECRET")
        or ""
    ).strip()


def _page_token() -> str:
    return (os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN") or "").strip()


def _verify_token() -> str:
    return (os.environ.get("FACEBOOK_VERIFY_TOKEN") or "").strip()


@lru_cache(maxsize=1)
def _load_config() -> Dict[str, Any]:
    if not os.path.isfile(_CONFIG_PATH):
        return {}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def reload_config() -> None:
    _load_config.cache_clear()


def public_status() -> Dict[str, Any]:
    cfg = _load_config()
    secret = _app_secret()
    token = _page_token()
    vtoken = _verify_token()
    return {
        "success": True,
        "bot_name": cfg.get("name") or "MasterNoder Casino Bot",
        "config_present": bool(cfg),
        "page_token_configured": bool(token),
        "app_secret_configured": bool(secret),
        "verify_token_configured": bool(vtoken),
        "webhook_url": f"{_BASE_URL}/api/facebook/casino/webhook",
        "graph_api_version": cfg.get("graph_api_version") or "v21.0",
        "use_llm": bool(cfg.get("use_llm", True)),
        "last_event": dict(_last_event),
    }


def verify_webhook(mode: str, token: str, challenge: str) -> Optional[str]:
    """Return hub.challenge when Meta verifies the webhook subscription."""
    expected = _verify_token()
    if not expected:
        return None
    if (mode or "").strip() == "subscribe" and (token or "").strip() == expected:
        return (challenge or "").strip()
    return None


def verify_signature(raw_body: bytes, signature_header: str) -> Tuple[bool, Optional[str]]:
    secret = _app_secret()
    if not secret:
        return True, None
    header = (signature_header or "").strip()
    if not header.startswith("sha256="):
        return False, "missing_signature"
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    supplied = header[7:]
    if not hmac.compare_digest(expected, supplied):
        return False, "invalid_signature"
    return True, None


def _command_reply(text: str) -> Optional[str]:
    cfg = _load_config()
    commands = cfg.get("commands") or {}
    t = (text or "").strip().lower()
    if not t:
        return None
    if t.startswith("faq "):
        query = text.strip()[4:].strip()
        if not query:
            return commands.get("help") or "Ask faq deposit, faq shop, faq casino, etc."
        try:
            from backend.services.support_faq_service import faq_answer

            use_llm = bool(cfg.get("use_llm", True))
            out = faq_answer(query, use_llm=use_llm, channel="facebook")
            return out.get("answer") or commands.get("help")
        except Exception:
            return "Visit Profile on masternoder.dk for account help."
    first = t.split()[0]
    if first in commands:
        return str(commands[first])
    for key, answer in commands.items():
        if key in t:
            return str(answer)
    return None


def build_reply(text: str, *, postback_payload: Optional[str] = None) -> str:
    cfg = _load_config()
    payload = (postback_payload or "").strip().lower()
    if payload:
        hit = _command_reply(payload)
        if hit:
            return hit
    hit = _command_reply(text)
    if hit:
        return hit
    welcome = (cfg.get("welcome_message") or "").strip()
    help_line = (cfg.get("commands") or {}).get("help") or "Type help, casino, shop, or faq <question>."
    if len((text or "").strip()) > 12 and cfg.get("use_llm", True):
        try:
            from backend.services.support_faq_service import faq_answer

            out = faq_answer(text.strip(), use_llm=True, channel="facebook")
            if out.get("answer"):
                return str(out["answer"])
        except Exception:
            pass
    if welcome:
        return f"{welcome}\n\n{help_line}"
    return help_line


def send_message(recipient_id: str, text: str) -> Dict[str, Any]:
    token = _page_token()
    if not token:
        return {"success": False, "error": "page_token_missing"}
    cfg = _load_config()
    version = cfg.get("graph_api_version") or "v21.0"
    url = f"https://graph.facebook.com/{version}/me/messages?access_token={token}"
    body = json.dumps(
        {
            "recipient": {"id": recipient_id},
            "message": {"text": (text or "")[:2000]},
            "messaging_type": "RESPONSE",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw or "{}")
        return {"success": True, "response": data}
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")[:400]
        return {"success": False, "error": f"graph_http_{exc.code}", "detail": err_body}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _handle_messaging_event(event: Dict[str, Any]) -> Dict[str, Any]:
    sender_id = ((event.get("sender") or {}).get("id") or "").strip()
    if not sender_id:
        return {"success": False, "error": "missing_sender"}

    text = ""
    postback = None
    if "message" in event:
        msg = event.get("message") or {}
        text = (msg.get("text") or "").strip()
    elif "postback" in event:
        postback = ((event.get("postback") or {}).get("payload") or "").strip()
        text = postback

    reply = build_reply(text, postback_payload=postback)
    send_result = send_message(sender_id, reply)

    _last_event["processed"] = int(_last_event.get("processed") or 0) + 1
    _last_event["last_sender"] = sender_id
    _last_event["last_text"] = text or postback

    return {
        "success": send_result.get("success", False),
        "sender_id": sender_id,
        "reply_preview": reply[:120],
        "send": send_result,
    }


def handle_webhook_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process Meta webhook JSON — messaging events only."""
    if payload.get("object") != "page":
        return {"success": True, "skipped": True, "reason": "not_page_object"}

    results: List[Dict[str, Any]] = []
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for event in entry.get("messaging") or []:
            if not isinstance(event, dict):
                continue
            if event.get("message", {}).get("is_echo"):
                continue
            results.append(_handle_messaging_event(event))

    return {"success": True, "handled": len(results), "results": results}
