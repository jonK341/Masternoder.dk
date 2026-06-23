"""Casino social layer — platform news, activity events, opt-in win sharing."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PREFS_DIR = os.path.join(_BASE, "logs", "casino_social_prefs")
_PROMOS_PATH = os.path.join(_BASE, "logs", "casino_discord_promos.json")

_RG_FOOTER = (
    "Play responsibly. Set deposit and loss limits in your profile. "
    "18+ only where online gambling is licensed."
)
_CASINO_HREF = "/casino/"

_BIG_WIN_THRESHOLDS = {
    "coins": float(os.environ.get("CASINO_BIG_WIN_THRESHOLD_COINS", "1000")),
    "mn2": float(os.environ.get("CASINO_BIG_WIN_THRESHOLD_MN2", "10")),
    "usd": float(os.environ.get("CASINO_BIG_WIN_THRESHOLD_USD", "50")),
}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _blocked_countries() -> set:
    raw = os.environ.get("CASINO_DISCORD_BLOCKED_COUNTRIES", "US")
    return {c.strip().upper() for c in raw.split(",") if c.strip()}


def _prefs_path(user_id: str) -> str:
    safe = hashlib.sha256(user_id.encode()).hexdigest()[:16]
    return os.path.join(_PREFS_DIR, f"{safe}.json")


def get_preferences(user_id: str) -> Dict[str, Any]:
    path = _prefs_path(user_id)
    if not os.path.isfile(path):
        return {
            "user_id": user_id,
            "share_wins": False,
            "country_code": None,
            "updated_at": None,
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"user_id": user_id, "share_wins": False}
    except Exception:
        return {"user_id": user_id, "share_wins": False}


def set_preferences(
    user_id: str,
    *,
    share_wins: Optional[bool] = None,
    country_code: Optional[str] = None,
) -> Dict[str, Any]:
    os.makedirs(_PREFS_DIR, exist_ok=True)
    prefs = get_preferences(user_id)
    if share_wins is not None:
        prefs["share_wins"] = bool(share_wins)
    if country_code is not None:
        prefs["country_code"] = (country_code or "").strip().upper() or None
    prefs["user_id"] = user_id
    prefs["updated_at"] = _iso()
    with _LOCK:
        with open(_prefs_path(user_id), "w", encoding="utf-8") as f:
            json.dump(prefs, f, indent=2)
    return {"success": True, "preferences": prefs}


def anonymize_user(user_id: str) -> str:
    digest = hashlib.sha256(user_id.encode()).hexdigest()[:4]
    return f"Player#{digest}"


def geo_allows_discord(user_id: str) -> bool:
    blocked = _blocked_countries()
    if not blocked:
        return True
    prefs = get_preferences(user_id)
    cc = (prefs.get("country_code") or "").upper()
    if cc and cc in blocked:
        return False
    try:
        from backend.services.browser_profile_tracker import get_browser_profile
        profile = get_browser_profile(user_id) or {}
        cc2 = (profile.get("country") or "")[:2].upper()
        if cc2 and cc2 in blocked:
            return False
    except Exception:
        pass
    return True


def may_share_win(user_id: str) -> bool:
    prefs = get_preferences(user_id)
    return bool(prefs.get("share_wins")) and geo_allows_discord(user_id)


def _emit(event_type: str, *, user_id: Optional[str], payload: Dict[str, Any]) -> None:
    try:
        from backend.services.activity_events_service import emit
        emit(event_type, channel="casino", user_id=user_id, payload=payload)
    except Exception:
        pass


def _publish_news(
    *,
    item_id: str,
    title: str,
    summary: str,
    featured: bool = False,
) -> None:
    try:
        from backend.services.platform_news_publish import publish
        publish(
            item_id=item_id,
            title=title,
            summary=summary,
            channel="casino",
            href=_CASINO_HREF,
            featured=featured,
        )
    except Exception:
        pass


def _format_amount(amount: float, currency: str) -> str:
    if currency == "mn2":
        return f"{amount:.4f} MN2"
    if currency == "usd":
        return f"${amount:.2f}"
    return f"{int(amount)} coins"


def on_jackpot_win(
    *,
    user_id: str,
    currency: str,
    amount: float,
    reason: str,
    bet_id: Optional[str] = None,
) -> None:
    label = _format_amount(amount, currency)
    item_id = f"casino-jackpot-{currency}-{bet_id or _iso()}"
    _publish_news(
        item_id=item_id,
        title=f"Jackpot hit — {label} awarded",
        summary=(
            f"A progressive {currency.upper()} jackpot just dropped ({reason}). "
            f"Next pool is re-seeded — spin at the casino. {_RG_FOOTER}"
        ),
        featured=True,
    )
    _emit(
        "casino_jackpot_win",
        user_id=user_id,
        payload={
            "currency": currency,
            "amount": amount,
            "reason": reason,
            "bet_id": bet_id,
            "share_ok": may_share_win(user_id),
            "anonymized": anonymize_user(user_id),
        },
    )


def on_big_win(
    *,
    user_id: str,
    game: str,
    currency: str,
    net: float,
    payout: float,
    bet_id: str,
) -> None:
    if net < _BIG_WIN_THRESHOLDS.get(currency, float("inf")):
        return
    _emit(
        "casino_big_win",
        user_id=user_id,
        payload={
            "game": game,
            "currency": currency,
            "net": net,
            "payout": payout,
            "bet_id": bet_id,
            "share_ok": may_share_win(user_id),
            "anonymized": anonymize_user(user_id),
        },
    )


def on_tournament_end(
    *,
    tournament_id: str,
    title: str,
    currency: str,
    pool: float,
    winner_count: int,
) -> None:
    pool_label = _format_amount(pool, currency)
    _publish_news(
        item_id=f"casino-tournament-{tournament_id}",
        title=f"Tournament finished — {title}",
        summary=(
            f"Prizes from a {pool_label} pool were awarded to top {winner_count} players. "
            f"Join the next tournament at the casino. {_RG_FOOTER}"
        ),
        featured=False,
    )
    _emit(
        "casino_tournament_end",
        user_id=None,
        payload={
            "tournament_id": tournament_id,
            "title": title,
            "currency": currency,
            "pool": pool,
            "winner_count": winner_count,
        },
    )


def on_tournament_prize(
    *,
    user_id: str,
    tournament_id: str,
    rank: int,
    prize: float,
    currency: str,
) -> None:
    if prize <= 0:
        return
    _emit(
        "casino_tournament_prize",
        user_id=user_id,
        payload={
            "tournament_id": tournament_id,
            "rank": rank,
            "prize": prize,
            "currency": currency,
            "share_ok": may_share_win(user_id),
            "anonymized": anonymize_user(user_id),
        },
    )


def publish_rg_reminder() -> Dict[str, Any]:
    item_id = f"casino-rg-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    summary = (
        "Set daily deposit and loss limits before you play. "
        "Take breaks, never chase losses, and use self-exclusion if needed."
    )
    _publish_news(
        item_id=item_id,
        title="Responsible gambling reminder",
        summary=summary,
        featured=False,
    )
    _emit("casino_rg_reminder", user_id=None, payload={"summary": summary})
    return {"success": True, "item_id": item_id}


def publish_mn2_rail_promo(title: str, summary: str) -> Dict[str, Any]:
    item_id = f"casino-mn2-promo-{secrets.token_hex(4)}"
    _publish_news(item_id=item_id, title=title, summary=summary, featured=True)
    _emit("casino_mn2_promo", user_id=None, payload={"title": title, "summary": summary})
    return {"success": True, "item_id": item_id}


def _load_promos() -> Dict[str, Any]:
    if not os.path.isfile(_PROMOS_PATH):
        return {"codes": []}
    try:
        with open(_PROMOS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"codes": []}
    except Exception:
        return {"codes": []}


def _save_promos(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_PROMOS_PATH), exist_ok=True)
    with _LOCK:
        tmp = _PROMOS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, _PROMOS_PATH)


def create_discord_promo(
    *,
    reward_coins: int = 50,
    max_redemptions: int = 100,
    ttl_hours: int = 48,
) -> Dict[str, Any]:
    """M8 #52 — Discord-exclusive promo code."""
    code = "DC-" + secrets.token_hex(3).upper()
    expires = datetime.now(timezone.utc).timestamp() + ttl_hours * 3600
    row = {
        "code": code,
        "channel": "discord",
        "reward_coins": int(reward_coins),
        "max_redemptions": int(max_redemptions),
        "redeemed_by": [],
        "expires_at": datetime.fromtimestamp(expires, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "created_at": _iso(),
    }
    data = _load_promos()
    codes = data.get("codes") if isinstance(data.get("codes"), list) else []
    codes.append(row)
    data["codes"] = codes[-200:]
    _save_promos(data)
    _emit("casino_discord_promo_created", user_id=None, payload={"code": code, "reward_coins": reward_coins})
    return {"success": True, "promo": row}


def redeem_discord_promo(user_id: str, code: str) -> Dict[str, Any]:
    code = (code or "").strip().upper()
    if not code:
        return {"success": False, "error": "code required"}
    data = _load_promos()
    codes = data.get("codes") if isinstance(data.get("codes"), list) else []
    target = None
    for row in codes:
        if (row.get("code") or "").upper() == code:
            target = row
            break
    if not target:
        return {"success": False, "error": "invalid_code"}
    try:
        exp = datetime.fromisoformat((target.get("expires_at") or "").replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > exp:
            return {"success": False, "error": "expired"}
    except Exception:
        pass
    redeemed = target.get("redeemed_by") if isinstance(target.get("redeemed_by"), list) else []
    if user_id in redeemed:
        return {"success": False, "error": "already_redeemed"}
    if len(redeemed) >= int(target.get("max_redemptions") or 0):
        return {"success": False, "error": "exhausted"}
    reward = int(target.get("reward_coins") or 0)
    try:
        from backend.services import casino_service
        casino_service._apply_balance_delta(
            user_id, float(reward), "coins", "discord_promo",
            {"phase": "promo", "code": code},
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    redeemed.append(user_id)
    target["redeemed_by"] = redeemed
    _save_promos(data)
    _emit(
        "casino_discord_promo_redeemed",
        user_id=user_id,
        payload={"code": code, "reward_coins": reward},
    )
    return {"success": True, "reward_coins": reward, "code": code}


def check_vip_discord_eligibility(user_id: str) -> Dict[str, Any]:
    """M8 #51 — linked Discord + minimum MN2 balance."""
    min_mn2 = float(os.environ.get("CASINO_DISCORD_VIP_MIN_MN2", "100"))
    discord_id = None
    ident_dir = os.path.join(_BASE, "logs", "user_identifiers")
    if os.path.isdir(ident_dir):
        for name in os.listdir(ident_dir):
            if not name.startswith("discord_") or not name.endswith(".json"):
                continue
            try:
                with open(os.path.join(ident_dir, name), "r", encoding="utf-8") as f:
                    row = json.load(f)
                if row.get("user_id") == user_id:
                    discord_id = row.get("discord_id") or name.replace("discord_", "").replace(".json", "")
                    break
            except Exception:
                continue
    mn2_balance = 0.0
    try:
        from backend.services import casino_service
        bal = casino_service.get_balance(user_id)
        mn2_balance = float(bal.get("mn2_balance") or bal.get("balances", {}).get("mn2") or 0)
    except Exception:
        pass
    eligible = bool(discord_id) and mn2_balance >= min_mn2 and geo_allows_discord(user_id)
    return {
        "success": True,
        "eligible": eligible,
        "discord_linked": bool(discord_id),
        "mn2_balance": mn2_balance,
        "min_mn2": min_mn2,
        "role": "casino_vip" if eligible else None,
    }


def rg_footer() -> str:
    return _RG_FOOTER
