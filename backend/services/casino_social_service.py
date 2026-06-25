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


def on_tournament_start(
    *,
    tournament_id: str,
    title: str,
    currency: str,
    pool: float,
    end_at: str,
) -> None:
    pool_label = _format_amount(pool, currency)
    _publish_news(
        item_id=f"casino-tournament-start-{tournament_id}",
        title=f"Tournament live — {title}",
        summary=(
            f"A new {pool_label} prize pool tournament is open. "
            f"Join before it ends and climb the leaderboard. {_RG_FOOTER}"
        ),
        featured=False,
    )
    _emit(
        "casino_tournament_start",
        user_id=None,
        payload={
            "tournament_id": tournament_id,
            "title": title,
            "currency": currency,
            "pool": pool,
            "end_at": end_at,
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


def _base_url() -> str:
    return (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")


def _load_casino_config() -> Dict[str, Any]:
    path = os.path.join(_BASE, "data", "casino_config.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_mobile_config() -> Dict[str, Any]:
    """TWA / Capacitor / App Store metadata for casino mobile shell."""
    cfg = _load_casino_config()
    mobile = cfg.get("mobile") if isinstance(cfg.get("mobile"), dict) else {}
    base = _base_url()
    start_path = mobile.get("start_url") or "/casino/?app=casino-capacitor&tab=lobby"
    ios_start = mobile.get("ios_start_url") or "/casino/?app=casino-capacitor&tab=lobby"
    return {
        "success": True,
        "app_version": mobile.get("app_version") or "1.0.0",
        "package_id": mobile.get("package_id") or "dk.masternoder.casino",
        "bundle_id": mobile.get("bundle_id") or "dk.masternoder.casino",
        "play_store_url": mobile.get("play_store_url") or (
            "https://play.google.com/store/apps/details?id=dk.masternoder.casino"
        ),
        "app_store_url": mobile.get("app_store_url") or (
            "https://apps.apple.com/app/id0000000000"
        ),
        "manifest_url": f"{base}/casino/manifest.webmanifest",
        "assetlinks_url": f"{base}/.well-known/assetlinks.json",
        "aasa_url": f"{base}/.well-known/apple-app-site-association",
        "start_url": f"{base}{start_path}" if start_path.startswith("/") else start_path,
        "ios_start_url": f"{base}{ios_start}" if ios_start.startswith("/") else ios_start,
        "deep_link_base": mobile.get("deep_link_base") or f"{base}/casino/",
        "deep_link_params": {
            "game": "Opens game tab (e.g. crash, plinko, slot_classic)",
            "tab": "Main tab (home, social, lobby, walk, leaderboard, activity)",
            "app": "Shell chrome: casino-twa (Play TWA), casino-capacitor, casino-pwa",
        },
        "url_scheme": mobile.get("url_scheme") or "masternoder",
        "custom_scheme_examples": [
            "masternoder://casino?game=crash",
            "masternoder://casino?tab=social",
        ],
        "universal_link_paths": mobile.get("universal_link_paths") or ["/casino", "/casino/*"],
        "theme_color": mobile.get("theme_color") or "#1A1035",
        "background_color": mobile.get("background_color") or "#0A0E14",
        "display": "standalone",
        "orientation": mobile.get("orientation") or "portrait-primary",
        "twa_app_param": "casino-twa",
        "capacitor_app_param": "casino-capacitor",
        "pwa_app_param": "casino-pwa",
        "install_prompt_enabled": bool(mobile.get("install_prompt_enabled", True)),
        "feature_flags": {
            "haptics": bool(mobile.get("haptics", True)),
            "bottom_nav_shell": bool(mobile.get("bottom_nav_shell", True)),
            "universal_links": bool(mobile.get("universal_links", True)),
        },
    }


def get_social_links() -> Dict[str, Any]:
    """Official social URLs and share networks for the casino Social tab."""
    cfg = _load_casino_config()
    links = cfg.get("social_links") if isinstance(cfg.get("social_links"), list) else []
    discord_cfg = cfg.get("discord_integration") if isinstance(cfg.get("discord_integration"), dict) else {}
    facebook_cfg = cfg.get("facebook") if isinstance(cfg.get("facebook"), dict) else {}
    social_cfg = cfg.get("social") if isinstance(cfg.get("social"), dict) else {}
    networks: List[Dict[str, Any]] = []
    sn_path = os.path.join(_BASE, "data", "social_networks.json")
    if os.path.isfile(sn_path):
        try:
            with open(sn_path, "r", encoding="utf-8") as f:
                sn = json.load(f)
            if isinstance(sn.get("networks"), list):
                networks = sn["networks"]
        except Exception:
            pass
    base = social_cfg.get("share_base_url") or _base_url()
    mobile = get_mobile_config()
    return {
        "success": True,
        "follow_links": links,
        "share_networks": networks,
        "share_base_url": base,
        "default_share_text": social_cfg.get("default_share_text") or (
            "Play at MasterNoder Casino — crash, slots, plinko, and more."
        ),
        "discord": {
            "invite_url": discord_cfg.get("invite_url") or "https://discord.gg/masternoder",
            "activity_invite_url": discord_cfg.get("activity_invite_url") or discord_cfg.get("invite_url"),
            "earn_coins_join": int(discord_cfg.get("earn_coins_join") or 0),
            "discord_play_path": discord_cfg.get("discord_play_path") or "/discord-play/",
            "webhook_env": discord_cfg.get("webhook_env") or "DISCORD_CHANNEL_ID_CASINO",
            "enabled": bool(discord_cfg.get("enabled", True)),
        },
        "facebook": {
            "page_url": facebook_cfg.get("page_url") or "https://facebook.com/MasterNoder",
            "og_title": facebook_cfg.get("og_title") or "MasterNoder Casino",
            "og_description": facebook_cfg.get("og_description") or (
                "Social casino lounge — virtual coins, big wins, and tournaments."
            ),
            "og_image": facebook_cfg.get("og_image") or "/static/img/casino/og-share.svg",
            "pixel_id_env": facebook_cfg.get("pixel_id_env") or "META_PIXEL_ID",
        },
        "mobile": {
            "play_store_url": mobile.get("play_store_url"),
            "package_id": mobile.get("package_id"),
        },
    }


def build_big_win_share(
    user_id: str,
    *,
    game: Optional[str] = None,
    net: Optional[float] = None,
    currency: Optional[str] = None,
    multiplier: Optional[float] = None,
    bet_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Share card payload for Facebook, X, Discord, and in-app copy."""
    cfg = _load_casino_config()
    facebook_cfg = cfg.get("facebook") if isinstance(cfg.get("facebook"), dict) else {}
    base = _base_url()
    handle = anonymize_user(user_id) if user_id else "Player"
    game_label = (game or "casino").replace("_", " ").replace("-", " ")
    cur = (currency or "coins").lower()
    win_net = float(net or 0)
    mult = float(multiplier or 0) if multiplier is not None else None
    image_path = facebook_cfg.get("og_image") or "/static/img/casino/og-share.svg"
    image_url = image_path if image_path.startswith("http") else f"{base}{image_path}"
    title = f"{handle} won on {game_label}!"
    if win_net > 0:
        desc = f"Big win: {_format_amount(win_net, cur)} on {game_label}"
        if mult and mult >= 1:
            desc += f" ({mult:.1f}×)"
    else:
        desc = f"Playing {game_label} at MasterNoder Casino"
    params = {"share": "big-win", "game": game or "casino"}
    if win_net > 0:
        params["net"] = str(int(win_net) if cur == "coins" else win_net)
        params["currency"] = cur
    if mult and mult >= 1:
        params["mult"] = f"{mult:.2f}"
    if bet_id:
        params["bet"] = bet_id
    from urllib.parse import urlencode
    share_url = f"{base}/casino/?{urlencode(params)}"
    text = f"{desc} — MasterNoder Casino"
    from urllib.parse import quote
    q_url = quote(share_url, safe="")
    q_text = quote(text, safe="")
    return {
        "success": True,
        "card": {
            "handle": handle,
            "game": game or "casino",
            "net": win_net,
            "currency": cur,
            "multiplier": mult,
            "title": title,
            "description": desc,
            "image_url": image_url,
            "share_url": share_url,
        },
        "share_urls": {
            "facebook": f"https://www.facebook.com/sharer/sharer.php?u={q_url}",
            "twitter": f"https://twitter.com/intent/tweet?text={q_text}&url={q_url}",
            "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={q_url}",
            "telegram": f"https://t.me/share/url?url={q_url}&text={q_text}",
        },
        "rg_footer": _RG_FOOTER,
    }


def discord_integration_config() -> Dict[str, Any]:
    cfg = _load_casino_config()
    return cfg.get("discord_integration") if isinstance(cfg.get("discord_integration"), dict) else {}
