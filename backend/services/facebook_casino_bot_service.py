"""Facebook Casino Bot — Messenger controller + play-to-earn for linked Facebook users."""
from __future__ import annotations

import json
import os
import secrets
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "facebook_casino_bot_config.json")
_STATE_DIR = os.path.join(_BASE, "logs", "facebook_casino")
_USERS_PATH = os.path.join(_STATE_DIR, "users.json")
_CODES_PATH = os.path.join(_STATE_DIR, "link_codes.json")
_BASE_URL = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> str:
    return _utcnow().strftime("%Y%m%d")


def _load_json(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with _LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)


def _config() -> Dict[str, Any]:
    return _load_json(_CONFIG_PATH)


def _earn_cfg() -> Dict[str, Any]:
    return _config().get("earn") if isinstance(_config().get("earn"), dict) else {}


def _facebook_row(psid: str) -> Dict[str, Any]:
    pid = (psid or "").strip()
    data = _load_json(_USERS_PATH)
    users = data.setdefault("users", {})
    row = users.setdefault(pid, {})
    row.setdefault("facebook_psid", pid)
    row.setdefault("lifetime_coins", 0)
    row.setdefault("lifetime_mn2", 0.0)
    row.setdefault("today_coins", 0)
    row.setdefault("today_date", _today())
    row.setdefault("daily_claimed_at", None)
    row.setdefault("referrals", 0)
    if row.get("today_date") != _today():
        row["today_date"] = _today()
        row["today_coins"] = 0
    _save_json(_USERS_PATH, data)
    return row


def _user_id_for_facebook(psid: str) -> Optional[str]:
    pid = (psid or "").strip()
    if not pid:
        return None
    ident = os.path.join(_BASE, "logs", "user_identifiers", f"facebook_{pid}.json")
    if os.path.isfile(ident):
        try:
            with open(ident, "r", encoding="utf-8") as f:
                row = json.load(f)
            if row.get("linked"):
                return row.get("user_id")
        except Exception:
            pass
    row = _load_json(_USERS_PATH).get("users", {}).get(pid) or {}
    return row.get("user_id")


def get_bot_config() -> Dict[str, Any]:
    cfg = _config()
    return {
        "success": True,
        "bot_name": cfg.get("bot_name"),
        "page_username": cfg.get("page_username"),
        "commands": cfg.get("messenger_commands") or [],
        "money_makers": cfg.get("money_makers") or [],
        "earn": _earn_cfg(),
        "compliance": cfg.get("compliance_note"),
        "casino_href": f"{_BASE_URL}/casino/?tab=multiplay",
        "multiplay_href": f"{_BASE_URL}/casino/?tab=multiplay",
        "shop_href": f"{_BASE_URL}/shop/",
    }


def get_facebook_status(*, user_id: Optional[str] = None, facebook_psid: Optional[str] = None) -> Dict[str, Any]:
    uid = (user_id or "").strip() or None
    pid = (facebook_psid or "").strip() or None
    if uid and not pid:
        data = _load_json(_USERS_PATH).get("users") or {}
        for k, v in data.items():
            if isinstance(v, dict) and v.get("user_id") == uid:
                pid = k
                break
    if pid and not uid:
        uid = _user_id_for_facebook(pid)
    linked = bool(uid and pid and _user_id_for_facebook(pid) == uid)
    row = _facebook_row(pid) if pid else {}
    earn = _earn_cfg()
    mp_stats = {}
    try:
        from backend.services.casino_multiplay_service import get_multiplay_catalog
        mp_stats = (get_multiplay_catalog().get("stats") or {})
    except Exception:
        pass
    return {
        "success": True,
        "linked": linked,
        "user_id": uid,
        "facebook_psid": pid,
        "earn": {
            "lifetime_coins": int(row.get("lifetime_coins") or 0),
            "today_coins": int(row.get("today_coins") or 0),
            "daily_cap": int(earn.get("daily_play_cap_coins") or 400),
            "daily_claim_coins": int(earn.get("daily_claim_coins") or 50),
            "daily_claimed_today": row.get("daily_claimed_at") == _today(),
            "referrals": int(row.get("referrals") or 0),
        },
        "money_makers": _config().get("money_makers") or [],
        "multiplay_stats": mp_stats,
        "messenger_deep_link": f"https://m.me/{cfg.get('page_username') or 'MasterNoderCasino'}" if (cfg := _config()) else None,
    }


def create_link_code(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    code = secrets.token_hex(3).upper()
    data = _load_json(_CODES_PATH)
    codes = data.setdefault("codes", {})
    codes[code] = {"user_id": uid, "created_at": _utcnow().isoformat(), "expires_at": _utcnow().timestamp() + 900}
    data["codes"] = codes
    _save_json(_CODES_PATH, data)
    return {
        "success": True,
        "code": code,
        "expires_in_sec": 900,
        "messenger_hint": f"Send LINK {code} to the Facebook Casino bot",
    }


def complete_link_with_code(facebook_psid: str, code: str) -> Dict[str, Any]:
    pid = (facebook_psid or "").strip()
    c = (code or "").strip().upper()
    if not pid or not c:
        return {"success": False, "error": "facebook_psid and code required"}
    data = _load_json(_CODES_PATH)
    row = (data.get("codes") or {}).get(c)
    if not row:
        return {"success": False, "error": "invalid_code"}
    if _utcnow().timestamp() > float(row.get("expires_at") or 0):
        return {"success": False, "error": "expired_code"}
    uid = row.get("user_id")
    ident_dir = os.path.join(_BASE, "logs", "user_identifiers")
    os.makedirs(ident_dir, exist_ok=True)
    ident_path = os.path.join(ident_dir, f"facebook_{pid}.json")
    with open(ident_path, "w", encoding="utf-8") as f:
        json.dump({"linked": True, "user_id": uid, "facebook_psid": pid, "linked_at": _utcnow().isoformat()}, f)
    fb_row = _facebook_row(pid)
    fb_row["user_id"] = uid
    all_users = _load_json(_USERS_PATH)
    all_users.setdefault("users", {})[pid] = fb_row
    _save_json(_USERS_PATH, all_users)
    del data["codes"][c]
    _save_json(_CODES_PATH, data)
    return {"success": True, "user_id": uid, "facebook_psid": pid}


def _grant_earn(user_id: str, psid: str, coins: int, mn2: float, *, source: str) -> Dict[str, Any]:
    if coins <= 0 and mn2 <= 0:
        return {"granted_coins": 0, "granted_mn2": 0.0}
    try:
        from backend.services.unified_points_database import unified_points_db
        if coins > 0:
            unified_points_db.add_points(user_id, "coins", float(coins), source=source, metadata={"facebook_psid": psid})
        if mn2 > 0:
            unified_points_db.add_points(user_id, "mn2_balance", mn2, source=source, metadata={"facebook_psid": psid})
    except Exception:
        return {"granted_coins": 0, "granted_mn2": 0.0}
    row = _facebook_row(psid)
    row["lifetime_coins"] = int(row.get("lifetime_coins") or 0) + coins
    row["lifetime_mn2"] = float(row.get("lifetime_mn2") or 0) + mn2
    row["today_coins"] = int(row.get("today_coins") or 0) + coins
    data = _load_json(_USERS_PATH)
    data.setdefault("users", {})[psid] = row
    _save_json(_USERS_PATH, data)
    return {"granted_coins": coins, "granted_mn2": mn2}


def record_facebook_play_earn(
    user_id: str,
    *,
    game: str,
    outcome: str,
    net: float,
    currency: str = "coins",
) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return {"success": False, "skipped": "anonymous"}
    data = _load_json(_USERS_PATH).get("users") or {}
    pid = None
    for k, v in data.items():
        if isinstance(v, dict) and v.get("user_id") == uid:
            pid = k
            break
    if not pid:
        ident_dir = os.path.join(_BASE, "logs", "user_identifiers")
        if os.path.isdir(ident_dir):
            for name in os.listdir(ident_dir):
                if name.startswith("facebook_") and name.endswith(".json"):
                    try:
                        with open(os.path.join(ident_dir, name), "r", encoding="utf-8") as f:
                            row = json.load(f)
                        if row.get("linked") and row.get("user_id") == uid:
                            pid = row.get("facebook_psid") or name.replace("facebook_", "").replace(".json", "")
                            break
                    except Exception:
                        pass
    if not pid:
        return {"success": False, "skipped": "not_linked"}
    earn = _earn_cfg()
    row = _facebook_row(pid)
    cap = int(earn.get("daily_play_cap_coins") or 400)
    if int(row.get("today_coins") or 0) >= cap:
        return {"success": True, "capped": True}
    coins = 0
    mn2 = 0.0
    if currency == "coins":
        coins += int(earn.get("coins_per_bet") or 3)
        if outcome in ("win", "jackpot", "payout") and net > 0:
            coins += int(earn.get("coins_per_win") or 12)
        if net >= float(earn.get("big_win_net_threshold_coins") or 80):
            mn2 = float(earn.get("mn2_per_big_win") or 0.002)
    remaining = max(0, cap - int(row.get("today_coins") or 0))
    coins = min(coins, remaining)
    granted = _grant_earn(uid, pid, coins, mn2, source="facebook_casino_play")
    return {"success": True, "facebook_psid": pid, **granted}


def claim_facebook_daily(*, user_id: Optional[str] = None, facebook_psid: Optional[str] = None) -> Dict[str, Any]:
    st = get_facebook_status(user_id=user_id, facebook_psid=facebook_psid)
    if not st.get("linked"):
        return {"success": False, "error": "link_required"}
    pid = st.get("facebook_psid")
    uid = st.get("user_id")
    row = _facebook_row(pid)
    if row.get("daily_claimed_at") == _today():
        return {"success": False, "error": "already_claimed_today"}
    earn = _earn_cfg()
    coins = int(earn.get("daily_claim_coins") or 50)
    mn2 = float(earn.get("daily_claim_mn2") or 0.008)
    granted = _grant_earn(uid, pid, coins, mn2, source="facebook_daily_claim")
    row["daily_claimed_at"] = _today()
    data = _load_json(_USERS_PATH)
    data.setdefault("users", {})[pid] = row
    _save_json(_USERS_PATH, data)
    return {"success": True, **granted}


def handle_messenger_text(facebook_psid: str, text: str) -> Dict[str, Any]:
    """Return Messenger send API payload messages list."""
    pid = (facebook_psid or "").strip()
    raw = (text or "").strip()
    upper = raw.upper()
    parts = upper.split()
    cmd = parts[0] if parts else "HELP"
    cfg = get_bot_config()
    makers = cfg.get("money_makers") or []
    mp = cfg.get("multiplay_stats") or {}

    def reply(body: str) -> Dict[str, Any]:
        return {"success": True, "messages": [{"text": body[:2000]}]}

    if cmd == "LINK" and len(parts) > 1:
        out = complete_link_with_code(pid, parts[1])
        if out.get("success"):
            return reply(f"✅ Linked! Play 30+ MultiPlay games: {cfg['multiplay_href']}")
        return reply(f"Link failed: {out.get('error')}")

    if cmd in ("CASINO", "PLAY"):
        return reply(
            f"🎰 MasterNoder Casino\n"
            f"30+ MultiPlay rooms · {mp.get('players_online', 0)} players online\n"
            f"Community pot: {mp.get('community_pot_coins', 0)} coins\n"
            f"{cfg['multiplay_href']}\n"
            f"Shop packs from ${makers[0].get('price_usd', 0.99) if makers else 0.99}"
        )

    if cmd == "MULTIPLAY":
        try:
            from backend.services.casino_multiplay_service import get_multiplay_catalog
            cat = get_multiplay_catalog()
            games = cat.get("games") or []
            lines = [f"• {g.get('icon', '🎲')} {g.get('title')}" for g in games[:8]]
            return reply(
                f"🎉 MultiPlay — {len(games)} games\n" + "\n".join(lines) +
                f"\n…and {max(0, len(games) - 8)} more!\n{cfg['multiplay_href']}"
            )
        except Exception:
            return reply(f"MultiPlay lounge: {cfg['multiplay_href']}")

    if cmd == "BALANCE":
        st = get_facebook_status(facebook_psid=pid)
        if not st.get("linked"):
            return reply("Link first — get a code on the casino Facebook tab, then send: LINK YOURCODE")
        try:
            from backend.services import casino_service
            bal = casino_service.get_balance(st["user_id"])
            return reply(
                f"💰 Balances\nCoins: {bal.get('coins', 0)}\n"
                f"MN2: {bal.get('mn2_balance', 0)}\nUSD: ${bal.get('fiat_balance', 0)}"
            )
        except Exception:
            return reply(f"View balances: {_BASE_URL}/profile/")

    if cmd == "DEPOSIT":
        return reply(
            f"💳 Deposits (on-site)\nPayPal USD · MN2 wallet · on-chain MN2\n{_BASE_URL}/casino/"
        )

    if cmd == "SHOP":
        packs = "\n".join(
            f"• {m.get('title')} ${m.get('price_usd', '—')}" for m in makers[:4] if m.get("price_usd")
        )
        return reply(f"🛒 Facebook seller packs\n{packs}\n{cfg['shop_href']}")

    if cmd == "REFERRAL":
        earn = _earn_cfg()
        return reply(
            f"👥 Invite friends to play MultiPlay!\n"
            f"You earn {earn.get('referral_coins', 100)} coins per linked friend.\n"
            f"Share: {cfg['multiplay_href']}"
        )

    if cmd == "EARN":
        out = claim_facebook_daily(facebook_psid=pid)
        if out.get("success"):
            return reply(f"Daily claim +{out.get('granted_coins', 0)} coins · +{out.get('granted_mn2', 0)} MN2")
        return reply(f"Earn: {out.get('error', 'link required')}")

    return reply(
        "🎰 MasterNoder Facebook Casino\n"
        "CASINO · MULTIPLAY · PLAY · LINK CODE · BALANCE · DEPOSIT · SHOP · REFERRAL · EARN\n"
        f"{cfg['multiplay_href']}"
    )


def verify_webhook(mode: str, token: str, challenge: str) -> Optional[str]:
    expected = os.environ.get("FACEBOOK_VERIFY_TOKEN", "").strip()
    if mode == "subscribe" and expected and token == expected:
        return challenge
    return None


def parse_messenger_webhook(body: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse webhook body → list of {psid, text} messages."""
    out: List[Dict[str, Any]] = []
    for entry in body.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for item in entry.get("messaging") or []:
            if not isinstance(item, dict):
                continue
            sender = (item.get("sender") or {}).get("id")
            msg = item.get("message") or {}
            text = msg.get("text")
            if sender and text:
                out.append({"psid": str(sender), "text": str(text)})
    return out


def process_webhook(body: Dict[str, Any]) -> Dict[str, Any]:
    replies: List[Dict[str, Any]] = []
    for item in parse_messenger_webhook(body):
        handled = handle_messenger_text(item["psid"], item["text"])
        replies.append({"psid": item["psid"], **handled})
    return {"success": True, "replies": replies}
