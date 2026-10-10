"""
Discord Controller — app manifest, slash commands, play-to-earn for linked users.

Gate S: rewards always credited on-site (coins/MN2); Discord is the control surface only.
"""
from __future__ import annotations

import json
import os
import secrets
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MANIFEST_PATH = os.path.join(_BASE, "data", "discord_app_manifest.json")
_CONFIG_PATH = os.path.join(_BASE, "data", "discord_controller_config.json")
_STATE_DIR = os.path.join(_BASE, "logs", "discord_controller")
_USERS_PATH = os.path.join(_STATE_DIR, "users.json")
_CODES_PATH = os.path.join(_STATE_DIR, "link_codes.json")
_BASE_URL = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> str:
    return _utcnow().strftime("%Y-%m-%d")


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


def _user_id_for_discord(discord_id: str) -> Optional[str]:
    did = (discord_id or "").strip()
    if not did:
        return None
    ident_dir = os.path.join(_BASE, "logs", "user_identifiers")
    path = os.path.join(ident_dir, f"discord_{did}.json")
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                row = json.load(f)
            if row.get("linked"):
                return row.get("user_id")
        except Exception:
            pass
    return None


def _discord_row(discord_id: str) -> Dict[str, Any]:
    did = (discord_id or "").strip()
    data = _load_json(_USERS_PATH)
    users = data.setdefault("users", {})
    row = users.setdefault(did, {})
    row.setdefault("discord_id", did)
    row.setdefault("lifetime_coins", 0)
    row.setdefault("lifetime_mn2", 0.0)
    row.setdefault("today_coins", 0)
    row.setdefault("today_date", _today())
    row.setdefault("daily_claimed_at", None)
    if row.get("today_date") != _today():
        row["today_date"] = _today()
        row["today_coins"] = 0
    _save_json(_USERS_PATH, data)
    return row


def get_app_manifest() -> Dict[str, Any]:
    manifest = _load_json(_MANIFEST_PATH)
    activities = manifest.get("activities") or []
    out_acts = []
    for act in activities:
        if not isinstance(act, dict):
            continue
        url = act.get("url") or "/"
        full = url if str(url).startswith("http") else f"{_BASE_URL}{url if url.startswith('/') else '/' + url}"
        out_acts.append({**act, "full_url": full})
    return {
        "success": True,
        "version": manifest.get("version"),
        "application_id": os.environ.get("DISCORD_APPLICATION_ID") or None,
        "activities": out_acts,
        "commands": _config().get("slash_commands") or [],
        "compliance": _config().get("compliance_note"),
    }


def create_link_code(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    code = secrets.token_hex(3).upper()
    data = _load_json(_CODES_PATH)
    codes = data.get("codes") if isinstance(data.get("codes"), dict) else {}
    codes[code] = {
        "user_id": uid,
        "created_at": _utcnow().isoformat(),
        "expires_at": (_utcnow().timestamp() + 900),
    }
    data["codes"] = codes
    _save_json(_CODES_PATH, data)
    return {
        "success": True,
        "code": code,
        "expires_in_sec": 900,
        "discord_command": f"/link {code}",
    }


def complete_link_with_code(discord_id: str, code: str) -> Dict[str, Any]:
    did = (discord_id or "").strip()
    code = (code or "").strip().upper()
    if not did or not code:
        return {"success": False, "error": "discord_id and code required"}
    data = _load_json(_CODES_PATH)
    codes = data.get("codes") if isinstance(data.get("codes"), dict) else {}
    row = codes.get(code)
    if not row:
        return {"success": False, "error": "invalid_code"}
    if _utcnow().timestamp() > float(row.get("expires_at") or 0):
        return {"success": False, "error": "expired_code"}
    uid = row.get("user_id")
    from backend.services.discord_link_service import link_user

    out = link_user(uid, did)
    if out.get("success"):
        del codes[code]
        data["codes"] = codes
        _save_json(_CODES_PATH, data)
        row = _discord_row(did)
        row["user_id"] = uid
        welcome = grant_discord_new_user_reward(uid, did)
        if welcome:
            out["welcome_reward"] = welcome
    return out


def grant_discord_new_user_reward(user_id: str, discord_id: str) -> Dict[str, Any]:
    """One-time MN2/coins for first Discord casino link (Gate S — site wallet only)."""
    uid = (user_id or "").strip()
    did = (discord_id or "").strip()
    if not uid or not did:
        return {"success": False, "error": "user_id and discord_id required"}
    earn = _earn_cfg()
    mn2 = float(earn.get("new_user_mn2") or 0)
    coins = int(earn.get("new_user_coins") or 0)
    if mn2 <= 0 and coins <= 0:
        return {"success": False, "skipped": "disabled"}

    row = _discord_row(did)
    if row.get("welcome_reward_granted_at"):
        return {
            "success": True,
            "already_claimed": True,
            "granted_mn2": 0.0,
            "granted_coins": 0,
        }

    granted_mn2 = 0.0
    granted_coins = 0

    if mn2 > 0:
        try:
            from backend.services.game_mn2_rewards import credit_mn2

            cr = credit_mn2(
                uid,
                mn2,
                source="discord_new_user_reward",
                reference=f"discord_welcome_{did}",
                metadata={"discord_id": did, "reward_type": "discord_casino_new_user"},
            )
            if not cr.get("success"):
                return {"success": False, "error": cr.get("error", "mn2_credit_failed")}
            if not cr.get("duplicate"):
                granted_mn2 = mn2
                row["lifetime_mn2"] = float(row.get("lifetime_mn2") or 0) + mn2
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    if coins > 0:
        g = _grant_earn(uid, did, coins, 0.0, source="discord_new_user_reward")
        granted_coins = int(g.get("granted_coins") or 0)

    row["welcome_reward_granted_at"] = _utcnow().isoformat()
    data = _load_json(_USERS_PATH)
    data.setdefault("users", {})[did] = row
    _save_json(_USERS_PATH, data)

    try:
        from backend.services.casino_social_hub_service import push_casino_activity

        push_casino_activity(
            uid,
            "discord_welcome_reward",
            f"Discord welcome bonus +{granted_mn2} MN2",
            {"discord_id": did, "granted_coins": granted_coins},
        )
    except Exception:
        pass

    return {
        "success": True,
        "first_time": True,
        "granted_mn2": granted_mn2,
        "granted_coins": granted_coins,
    }


def get_controller_status(*, user_id: Optional[str] = None, discord_id: Optional[str] = None) -> Dict[str, Any]:
    uid = (user_id or "").strip() or None
    did = (discord_id or "").strip() or None
    if uid and not did:
        try:
            from backend.services.discord_link_service import get_discord_id_for_user

            did = get_discord_id_for_user(uid)
        except Exception:
            pass
    if did and not uid:
        uid = _user_id_for_discord(did)
    linked = bool(uid and did)
    row = _discord_row(did) if did else {}
    hosting = {"hosting_customer": False}
    casino_level = 1
    if uid:
        try:
            from backend.services.discord_link_service import link_status

            st = link_status(uid)
            hosting = {
                "hosting_customer": st.get("hosting_customer"),
                "hosting_vip_eligible": st.get("hosting_vip_eligible"),
            }
        except Exception:
            pass
        try:
            from backend.services.casino_progression_service import get_user_progression

            casino_level = int((get_user_progression(uid) or {}).get("level") or 1)
        except Exception:
            pass
    earn = _earn_cfg()
    from backend.services.discord_setup_service import validate_env_config

    env_check = validate_env_config()
    return {
        "success": True,
        "linked": linked,
        "user_id": uid,
        "discord_id": did,
        "casino_level": casino_level,
        "hosting": hosting,
        "earn": {
            "lifetime_coins": int(row.get("lifetime_coins") or 0),
            "lifetime_mn2": float(row.get("lifetime_mn2") or 0),
            "today_coins": int(row.get("today_coins") or 0),
            "daily_cap": int(earn.get("daily_play_cap_coins") or 250),
            "daily_claimed_today": row.get("daily_claimed_at") == _today(),
            "daily_claim_coins": int(earn.get("daily_claim_coins") or 35),
            "new_user_mn2": float(earn.get("new_user_mn2") or 0),
            "welcome_reward_claimed": bool(row.get("welcome_reward_granted_at")),
        },
        "manifest_href": "/api/discord/app/manifest",
        "bot_token_configured": bool((os.environ.get("DISCORD_BOT_TOKEN") or "").strip()),
        "public_key_configured": bool((os.environ.get("DISCORD_PUBLIC_KEY") or "").strip()),
        "application_id_configured": bool(
            (os.environ.get("DISCORD_APPLICATION_ID") or os.environ.get("DISCORD_CLIENT_ID") or "").strip()
        ),
        "interactions_url": f"{_BASE_URL}/api/discord/interactions",
        "env": env_check,
    }


def _grant_earn(user_id: str, discord_id: str, coins: int, mn2: float, *, source: str) -> Dict[str, Any]:
    if coins <= 0 and mn2 <= 0:
        return {"granted_coins": 0, "granted_mn2": 0.0}
    try:
        from backend.services.unified_points_database import unified_points_db

        if coins > 0:
            unified_points_db.add_points(user_id, "coins", float(coins), source=source, metadata={"discord_id": discord_id})
        if mn2 > 0:
            unified_points_db.add_points(user_id, "mn2_balance", mn2, source=source, metadata={"discord_id": discord_id})
    except Exception:
        return {"granted_coins": 0, "granted_mn2": 0.0}
    row = _discord_row(discord_id)
    row["lifetime_coins"] = int(row.get("lifetime_coins") or 0) + coins
    row["lifetime_mn2"] = float(row.get("lifetime_mn2") or 0) + mn2
    row["today_coins"] = int(row.get("today_coins") or 0) + coins
    data = _load_json(_USERS_PATH)
    data.setdefault("users", {})[discord_id] = row
    _save_json(_USERS_PATH, data)
    return {"granted_coins": coins, "granted_mn2": mn2}


def record_casino_play_earn(
    user_id: str,
    *,
    game: str,
    outcome: str,
    net: float,
    currency: str = "coins",
) -> Dict[str, Any]:
    """Credit linked Discord users for on-site casino play (Gate S — site wallet only)."""
    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return {"success": False, "skipped": "anonymous"}
    try:
        from backend.services.discord_link_service import get_discord_id_for_user

        did = get_discord_id_for_user(uid)
    except Exception:
        did = None
    if not did:
        return {"success": False, "skipped": "not_linked"}
    earn = _earn_cfg()
    if earn.get("requires_link") and not did:
        return {"success": False, "skipped": "requires_link"}
    row = _discord_row(did)
    cap = int(earn.get("daily_play_cap_coins") or 250)
    if int(row.get("today_coins") or 0) >= cap:
        return {"success": True, "capped": True}
    coins = 0
    mn2 = 0.0
    if currency == "coins":
        coins += int(earn.get("coins_per_bet") or 2)
        if outcome in ("win", "jackpot", "payout") and net > 0:
            coins += int(earn.get("coins_per_win") or 8)
        if net >= float(earn.get("big_win_net_threshold_coins") or 100):
            mn2 = float(earn.get("mn2_per_big_win") or 0.001)
    remaining = max(0, cap - int(row.get("today_coins") or 0))
    coins = min(coins, remaining)
    granted = _grant_earn(uid, did, coins, mn2, source="discord_casino_play")
    try:
        from backend.services.casino_social_hub_service import push_casino_activity

        push_casino_activity(
            uid,
            "casino_discord_earn",
            f"Discord play-earn +{granted.get('granted_coins', 0)} coins",
            {"discord_id": did, "game": game},
        )
    except Exception:
        pass
    return {"success": True, "discord_id": did, **granted}


def claim_discord_daily(*, user_id: Optional[str] = None, discord_id: Optional[str] = None) -> Dict[str, Any]:
    st = get_controller_status(user_id=user_id, discord_id=discord_id)
    if not st.get("linked"):
        return {"success": False, "error": "link_required"}
    did = st.get("discord_id")
    uid = st.get("user_id")
    row = _discord_row(did)
    if row.get("daily_claimed_at") == _today():
        return {"success": False, "error": "already_claimed_today"}
    earn = _earn_cfg()
    coins = int(earn.get("daily_claim_coins") or 35)
    mn2 = float(earn.get("daily_claim_mn2") or 0.005)
    granted = _grant_earn(uid, did, coins, mn2, source="discord_daily_claim")
    row["daily_claimed_at"] = _today()
    data = _load_json(_USERS_PATH)
    data.setdefault("users", {})[did] = row
    _save_json(_USERS_PATH, data)
    return {"success": True, **granted}


def handle_slash_command(command: str, discord_id: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return Discord interaction-style payload { type, data: { content } }."""
    cmd = (command or "").strip().lower().lstrip("/")
    did = (discord_id or "").strip()
    opts = options or {}
    manifest = get_app_manifest()

    def reply(text: str, *, embed_title: Optional[str] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"type": 4, "data": {"content": text[:2000]}}
        if embed_title:
            payload["data"]["embeds"] = [{"title": embed_title, "description": text[:4096]}]
        return payload

    if cmd == "link":
        code = (opts.get("code") or "").strip().upper()
        if not code:
            return reply("Usage: `/link YOUR_CODE` — get a code from Casino → Discord tab or Profile.")
        out = complete_link_with_code(did, code)
        if out.get("success"):
            welcome = out.get("welcome_reward") or {}
            if welcome.get("first_time") and float(welcome.get("granted_mn2") or 0) > 0:
                return reply(
                    f"✅ Linked to site account **{out.get('user_id')}**.\n"
                    f"🎁 **Welcome bonus: +{welcome.get('granted_mn2')} MN2** credited to your casino wallet!\n"
                    f"Play at {_BASE_URL}/casino/ or `/playnow` to earn more."
                )
            if welcome.get("already_claimed"):
                return reply(f"✅ Linked to site account **{out.get('user_id')}**. Welcome bonus was already claimed for this Discord.")
            return reply(f"✅ Linked to site account **{out.get('user_id')}**. Play casino on-site to earn Discord rewards!")
        return reply(f"❌ Link failed: {out.get('error', 'unknown')}")

    if cmd == "earn":
        st = get_controller_status(discord_id=did)
        if not st.get("linked"):
            return reply("Link first: open masternoder.dk/casino → **Discord** tab → copy code → `/link CODE`")
        e = st.get("earn") or {}
        if not e.get("daily_claimed_today"):
            claim = claim_discord_daily(discord_id=did)
            if claim.get("success"):
                return reply(
                    f"🎁 Daily claimed: **+{claim.get('granted_coins', 0)} coins**"
                    f" + **{claim.get('granted_mn2', 0)} MN2**\n"
                    f"Lifetime Discord earn: {e.get('lifetime_coins', 0)} coins · "
                    f"Today from play: {e.get('today_coins', 0)}/{e.get('daily_cap', 250)}"
                )
        return reply(
            f"💰 Discord play-earn\n"
            f"Lifetime: **{e.get('lifetime_coins', 0)}** coins · **{e.get('lifetime_mn2', 0)}** MN2\n"
            f"Today from casino play: **{e.get('today_coins', 0)}/{e.get('daily_cap', 250)}**\n"
            f"Daily already claimed — play at {_BASE_URL}/casino/ for more."
        )

    if cmd == "casino":
        st = get_controller_status(discord_id=did)
        lvl = st.get("casino_level", 1)
        link = f"{_BASE_URL}/casino/?tab=lobby"
        msg = f"🎰 **Casino** — Level **{lvl}**\nPlay: {link}\n"
        if st.get("linked"):
            e = st.get("earn") or {}
            msg += f"Discord earn today: {e.get('today_coins', 0)}/{e.get('daily_cap', 250)} coins"
        else:
            msg += "Link account to earn coins while playing (`/link CODE`)."
        return reply(msg, embed_title="MasterNoder Casino")

    if cmd == "hosting":
        st = get_controller_status(discord_id=did)
        h = st.get("hosting") or {}
        msg = f"🖥️ **Masternode Hosting**\n{_BASE_URL}/hosting/\n"
        if h.get("hosting_customer"):
            msg += "✅ You have active hosting — VIP Discord role eligible when linked."
        else:
            msg += "Browse slots from **$4.99** — coins, PayPal, or MN2 checkout."
        return reply(msg, embed_title="MN2 Hosting")

    if cmd == "shop":
        return reply(f"🛒 **Game Shop**\n{_BASE_URL}/shop/\nPromos: DISCORD-STARTER · HOSTMN5 · GENERATE10")

    if cmd == "quests":
        return reply(f"📜 **Daily Quests**\n{_BASE_URL}/quests/\nComplete on-site — rewards never via Discord custody.")

    if cmd == "play":
        lines = [f"**{a.get('icon', '•')} {a.get('name')}** — {_BASE_URL}{a.get('url', '/')}" for a in (manifest.get("activities") or [])[:8]]
        return reply("🕹️ **MasterNoder activities**\n" + "\n".join(lines))

    if cmd == "playnow":
        st = get_controller_status(discord_id=did)
        if not st.get("linked"):
            return reply(f"Link first, then play: {_BASE_URL}/discord-play/\n`/link CODE`")
        try:
            from backend.services.discord_play_site_service import create_play_session
            sess = create_play_session(st["user_id"], discord_id=did, venue=opts.get("venue") or "uber", currency=opts.get("currency") or "usd")
            return reply(f"🎮 **Discord Play Site**\n{sess.get('play_url')}\nExpires in 1h · USD/MN2 preferred · MN2 network bonuses active.")
        except Exception as exc:
            return reply(f"Could not open play session: {exc}")

    if cmd == "uber":
        try:
            from backend.services.casino_uber_games_service import get_uber_catalog
            cat = get_uber_catalog()
            games = cat.get("games") or []
            lines = [f"• **{g.get('title')}** ({g.get('engine')}) — USD/MN2" for g in games[:5]]
            return reply("💎 **Uber Games** (real currency preferred)\n" + "\n".join(lines) + f"\n\nPlay: `/playnow` or {_BASE_URL}/discord-play/?venue=uber")
        except Exception:
            return reply(f"Uber lounge: {_BASE_URL}/discord-play/?venue=uber")

    if cmd == "ai":
        st = get_controller_status(discord_id=did)
        if not st.get("linked"):
            return reply("Link account to meet AI hosts Nova–Iris on the casino floor.")
        try:
            from backend.services.casino_ai_entertainment_service import list_hosts
            hosts = (list_hosts(st["user_id"]).get("hosts") or [])[:5]
            lines = [f"• **{h.get('name')}** — {h.get('persona')}" for h in hosts]
            return reply("🤖 **AI Casino Hosts**\n" + "\n".join(lines) + f"\nTip on-site · {_BASE_URL}/casino/?tab=agents")
        except Exception:
            return reply(f"AI hosts: {_BASE_URL}/casino/")

    if cmd == "network":
        st = get_controller_status(discord_id=did)
        if not st.get("linked"):
            return reply("Link to track MN2 network bonuses from real-currency wins.")
        try:
            from backend.services.casino_network_rewards_service import get_network_status
            ns = get_network_status(st["user_id"])
            return reply(
                f"⛓️ **MN2 Network bonuses**\n"
                f"Today: **{ns.get('bonus_mn2_today', 0)}** / {ns.get('daily_cap_mn2', 0.5)} MN2\n"
                f"Lifetime: **{ns.get('lifetime_bonus_mn2', 0)}** MN2\n"
                f"Deposit: `{ns.get('deposit_address') or 'link wallet on profile'}`"
            )
        except Exception:
            return reply("Network rewards: play uber games with USD/MN2 on discord-play site.")

    if cmd == "vip":
        return reply(f"👑 **Discord VIP pass** — 500 coins · 7 days · 2× play-earn\nBuy in casino shop or {_BASE_URL}/shop/")

    if cmd == "tip":
        return reply("💸 Tip AI hosts with coins on the casino floor (Nova–Iris). Revenue supports live entertainment.")

    if cmd == "deposit":
        return reply(
            f"💳 **Deposits**\n"
            f"• PayPal USD: {_BASE_URL}/casino/\n"
            f"• MN2 wallet buy-in: {_BASE_URL}/casino/\n"
            f"• On-chain MN2: Profile → wallet deposit\n"
            f"First match promo on discord-play site."
        )

    if cmd == "balance":
        st = get_controller_status(discord_id=did)
        if not st.get("linked"):
            return reply("Not linked — `/link CODE` from casino Discord tab.")
        try:
            from backend.services import casino_service
            bal = casino_service.get_balance(st["user_id"])
            return reply(
                f"💰 **Balances**\n"
                f"Coins: **{bal.get('coins', 0)}**\n"
                f"MN2: **{bal.get('mn2_balance', bal.get('balances', {}).get('mn2', 0))}**\n"
                f"USD: **{bal.get('fiat_balance', 0)}**"
            )
        except Exception:
            return reply(f"View balances: {_BASE_URL}/profile/")

    if cmd == "mn2":
        try:
            from backend.services.discord_mn2_channel_service import format_slash_mn2_reply

            return reply(format_slash_mn2_reply(discord_id=did), embed_title="MN2 Hub")
        except Exception as exc:
            return reply(f"MN2 hub: {_BASE_URL}/explorer/\nStaking: {_BASE_URL}/staking-monitor/\n({exc})")

    if cmd == "bundle":
        return reply(f"🎁 **Entertainment bundle** $9.99 — AI pack + 500 coins + uber day pass\n{_BASE_URL}/shop/")

    return reply(f"Unknown command `/{cmd}`. Try: `/play` `/playnow` `/mn2` `/uber` `/casino` `/earn` `/deposit` `/balance`")


def parse_discord_interaction(body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Map Discord APPLICATION_COMMAND interaction to slash handler."""
    if int(body.get("type") or 0) != 2:
        return None
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    name = (data.get("name") or "").strip()
    member = body.get("member") if isinstance(body.get("member"), dict) else {}
    user = body.get("user") if isinstance(body.get("user"), dict) else member.get("user") or {}
    discord_id = str(user.get("id") or "")
    options = {}
    for opt in data.get("options") or []:
        if isinstance(opt, dict) and opt.get("name"):
            options[opt["name"]] = opt.get("value")
    return handle_slash_command(name, discord_id, options)
