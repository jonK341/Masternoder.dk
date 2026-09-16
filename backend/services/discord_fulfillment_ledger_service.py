"""Discord community fulfillment ledger — order list for MN2 Discord members."""
from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_IDENT_DIR = os.path.join(_BASE, "logs", "user_identifiers")
_LEDGER_FILE = "discord_fulfillment_ledger.json"
_ORDER_LIST_FILE = "discord_order_list.json"
_CONFIG_FILE = "discord_fulfillment_config.json"
_MN2_CHANNEL_CONFIG = os.path.join(_BASE, "data", "discord_mn2_channel.json")
_PAYMENT_LEDGER = os.path.join(_BASE, "logs", "monetization", "payment_ledger.jsonl")
_DISCORD_CLICKS = os.path.join(_BASE, "logs", "discord_clicks.jsonl")
_DISCORD_PROMOS = os.path.join(_BASE, "data", "discord_promo_codes.json")
_ONRAMP_ORDERS = os.path.join(_BASE, "data", "mn2_onramp_orders.json")
_MN2_LEDGER = os.path.join(_BASE, "data", "mn2_ledger.json")
_INTENT_REGISTRY = os.path.join(_BASE, "data", "discord_mn2_purchase_intent.json")

_SOURCE_LOCAL = "local_linked"
_SOURCE_API = "discord_api"
_SOURCE_BUYER = "purchase_intent"
# Legacy source buckets map to granular population source ids in community_ledger_population.


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _data_dir() -> str:
    return os.path.join(_BASE, "data")


def _config_path() -> str:
    return os.path.join(_data_dir(), _CONFIG_FILE)


def _ledger_path() -> str:
    return os.path.join(_data_dir(), _LEDGER_FILE)


def _order_list_path() -> str:
    return os.path.join(_data_dir(), _ORDER_LIST_FILE)


def load_config() -> Dict[str, Any]:
    path = _config_path()
    defaults: Dict[str, Any] = {
        "mn2_channel_id": None,
        "buyer_signal_weights": {
            "payment_ledger": 30,
            "discord_promo_redeem": 25,
            "mn2_onramp_quote": 35,
            "mn2_onramp_funded": 45,
            "discord_click": 15,
            "coin_pack_purchase": 20,
            "casino_discord_play": 10,
            "wallet_intent_register": 40,
        },
        "buyer_signal_threshold": 20,
        "default_coin_pack_sku": "mn2-pack-s",
        "default_onramp_nudge_url": "/exchange?tab=onramp",
        "discord_promo_codes": ["DISCORD-STARTER", "HOSTMN5", "MARKET-BONUS"],
        "payment_item_id_hints": ["mn2", "coin", "pack", "onramp", "paypal"],
        "priority_weights": {
            "local_linked": 10,
            "discord_api": 5,
            "purchase_intent": 15,
            "linked_and_buyer": 25,
        },
    }
    if not os.path.isfile(path):
        return defaults
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            merged = {**defaults, **data}
            merged["buyer_signal_weights"] = {**defaults["buyer_signal_weights"], **(data.get("buyer_signal_weights") or {})}
            merged["priority_weights"] = {**defaults["priority_weights"], **(data.get("priority_weights") or {})}
            return merged
    except Exception:
        pass
    return defaults


def _bot_token() -> str:
    return (os.environ.get("DISCORD_BOT_TOKEN") or "").strip()


def _guild_id() -> str:
    return (os.environ.get("DISCORD_GUILD_ID") or "").strip()


def _mn2_channel_id() -> Optional[str]:
    cfg = load_config()
    cid = str(cfg.get("mn2_channel_id") or "").strip()
    if cid.isdigit():
        return cid
    env_id = (os.environ.get("DISCORD_MN2_CHANNEL_ID") or "").strip()
    if env_id.isdigit():
        return env_id
    if os.path.isfile(_MN2_CHANNEL_CONFIG):
        try:
            with open(_MN2_CHANNEL_CONFIG, "r", encoding="utf-8") as f:
                ch = json.load(f)
            cid = str((ch or {}).get("channel_id") or "").strip()
            if cid.isdigit():
                return cid
        except Exception:
            pass
    return None


def _read_jsonl(path: str, limit: int = 5000) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    if isinstance(row, dict):
                        rows.append(row)
                except Exception:
                    continue
                if len(rows) >= limit:
                    break
    except Exception:
        pass
    return rows


def _discord_api_get(path: str, params: Optional[Dict[str, str]] = None) -> Tuple[Optional[Any], Optional[str]]:
    token = _bot_token()
    if not token:
        return None, "bot_token_missing"
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params)
    url = f"https://discord.com/api/v10{path}{query}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bot {token}",
            "User-Agent": "MasternoderBot/1.0 (+[REDACTED])",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else None, None
    except urllib.error.HTTPError as exc:
        err_body = ""
        try:
            err_body = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        return None, f"HTTP {exc.code}: {err_body or exc.reason}"
    except Exception as exc:
        return None, str(exc)


def _resolve_discord_id(user_id: Optional[str]) -> Optional[str]:
    uid = (user_id or "").strip()
    if not uid:
        return None
    try:
        from backend.services.discord_link_service import get_discord_id_for_user

        return get_discord_id_for_user(uid)
    except Exception:
        return None


def _resolve_user_id(discord_id: Optional[str]) -> Optional[str]:
    did = (discord_id or "").strip()
    if not did:
        return None
    try:
        from backend.services.discord_link_service import get_user_id_for_discord

        return get_user_id_for_discord(did)
    except Exception:
        return None


def scan_local_linked_users() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not os.path.isdir(_IDENT_DIR):
        return rows
    for name in sorted(os.listdir(_IDENT_DIR)):
        if not name.startswith("discord_") or not name.endswith(".json"):
            continue
        path = os.path.join(_IDENT_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not data.get("linked"):
                continue
            discord_id = str(data.get("discord_id") or name.replace("discord_", "").replace(".json", "")).strip()
            if not discord_id:
                continue
            rows.append(
                {
                    "discord_id": discord_id,
                    "user_id": (data.get("user_id") or "").strip() or None,
                    "discord_username": data.get("discord_username") or data.get("username"),
                    "source": _SOURCE_LOCAL,
                    "buyer_signals": [],
                    "buyer_score": 0.0,
                }
            )
        except Exception:
            continue
    return rows


def fetch_discord_guild_members(limit: int = 1000) -> Dict[str, Any]:
    """Fetch guild members via Discord API (requires bot token + guild id)."""
    guild = _guild_id()
    token = _bot_token()
    if not token or not guild:
        return {"success": False, "members": [], "error": "bot_or_guild_not_configured", "api_used": False}

    members: List[Dict[str, Any]] = []
    after: Optional[str] = None
    pages = 0
    err: Optional[str] = None
    while pages < 10 and len(members) < limit:
        params: Dict[str, str] = {"limit": "1000"}
        if after:
            params["after"] = after
        data, api_err = _discord_api_get(f"/guilds/{guild}/members", params)
        if api_err:
            err = api_err
            break
        if not isinstance(data, list) or not data:
            break
        for m in data:
            user = m.get("user") if isinstance(m, dict) else {}
            if not isinstance(user, dict):
                continue
            uid = str(user.get("id") or "").strip()
            if not uid:
                continue
            members.append(
                {
                    "discord_id": uid,
                    "discord_username": user.get("global_name") or user.get("username"),
                    "user_id": None,
                    "source": _SOURCE_API,
                    "buyer_signals": [],
                    "buyer_score": 0.0,
                }
            )
        after = members[-1]["discord_id"] if members else None
        pages += 1
        if len(data) < 1000:
            break

    return {
        "success": not err,
        "members": members[:limit],
        "error": err,
        "api_used": True,
        "pages": pages,
    }


def fetch_discord_channel_authors(limit: int = 200) -> Dict[str, Any]:
    """Fetch recent message authors from the MN2 Discord channel."""
    channel_id = _mn2_channel_id()
    token = _bot_token()
    if not token or not channel_id:
        return {
            "success": False,
            "members": [],
            "error": "mn2_channel_or_bot_not_configured",
            "api_used": False,
        }

    data, api_err = _discord_api_get(f"/channels/{channel_id}/messages", {"limit": "100"})
    if api_err:
        return {"success": False, "members": [], "error": api_err, "api_used": True}

    seen: Set[str] = set()
    members: List[Dict[str, Any]] = []
    for msg in data if isinstance(data, list) else []:
        author = msg.get("author") if isinstance(msg, dict) else {}
        if not isinstance(author, dict) or author.get("bot"):
            continue
        uid = str(author.get("id") or "").strip()
        if not uid or uid in seen:
            continue
        seen.add(uid)
        members.append(
            {
                "discord_id": uid,
                "discord_username": author.get("global_name") or author.get("username"),
                "user_id": None,
                "source": _SOURCE_API,
                "buyer_signals": [],
                "buyer_score": 0.0,
            }
        )
        if len(members) >= limit:
            break

    return {"success": True, "members": members, "error": None, "api_used": True, "channel_id": channel_id}


def _buyer_signal_weight(cfg: Dict[str, Any], signal: str) -> float:
    weights = cfg.get("buyer_signal_weights") or {}
    try:
        return float(weights.get(signal) or 0)
    except (TypeError, ValueError):
        return 0.0


def _item_matches_mn2_coin(item_id: str, item_name: str, hints: List[str]) -> bool:
    blob = f"{item_id} {item_name}".lower()
    return any(h in blob for h in hints)


def _load_intent_registry() -> Dict[str, Any]:
    if not os.path.isfile(_INTENT_REGISTRY):
        return {"version": 1, "entries": []}
    try:
        with open(_INTENT_REGISTRY, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("entries", [])
            return data
    except Exception:
        pass
    return {"version": 1, "entries": []}


def _save_intent_registry(doc: Dict[str, Any]) -> None:
    os.makedirs(_data_dir(), exist_ok=True)
    doc["updated_at"] = _iso()
    path = _INTENT_REGISTRY
    tmp = path + ".tmp"
    with _LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        os.replace(tmp, path)


def register_mn2_purchase_intent(
    *,
    user_id: Optional[str] = None,
    discord_id: Optional[str] = None,
    channel: str = "wallet",
    pack_id: Optional[str] = None,
    amount_usd: Optional[float] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Record explicit MN2 buy intent (wallet CTA, Discord bot, ops import)."""
    uid = (user_id or "").strip() or None
    did = (discord_id or "").strip() or None
    if not did and uid:
        did = _resolve_discord_id(uid)
    if not did and not uid:
        return {"success": False, "error": "user_id or discord_id required"}

    entry = {
        "user_id": uid,
        "discord_id": did,
        "channel": (channel or "wallet").strip()[:64],
        "pack_id": (pack_id or "").strip()[:64] or None,
        "amount_usd": float(amount_usd) if amount_usd is not None else None,
        "note": (note or "").strip()[:256] or None,
        "registered_at": _iso(),
    }
    doc = _load_intent_registry()
    entries = doc.get("entries") or []
    dedupe = f"{did or ''}:{uid or ''}:{entry['channel']}:{entry.get('pack_id') or ''}"
    for prev in entries:
        if prev.get("_dedupe") == dedupe:
            prev.update(entry)
            prev["updated_at"] = _iso()
            _save_intent_registry(doc)
            return {"success": True, "updated": True, "discord_id": did, "user_id": uid, "entry": prev}
    entry["_dedupe"] = dedupe
    entries.append(entry)
    doc["entries"] = entries[-5000:]
    _save_intent_registry(doc)
    return {"success": True, "registered": True, "discord_id": did, "user_id": uid, "entry": entry}


def scan_purchase_intent_buyers() -> List[Dict[str, Any]]:
    """
    Source C — users with MN2/coin purchase intent signals, resolved to discord_id when possible.
    """
    cfg = load_config()
    hints = [str(h).lower() for h in (cfg.get("payment_item_id_hints") or [])]
    promo_codes = {str(c).upper() for c in (cfg.get("discord_promo_codes") or [])}
    by_discord: Dict[str, Dict[str, Any]] = {}

    def _bump(discord_id: str, user_id: Optional[str], signal: str, username: Optional[str] = None) -> None:
        did = (discord_id or "").strip()
        if not did:
            return
        w = _buyer_signal_weight(cfg, signal)
        if did not in by_discord:
            by_discord[did] = {
                "discord_id": did,
                "user_id": user_id,
                "discord_username": username,
                "source": _SOURCE_BUYER,
                "buyer_signals": [],
                "buyer_score": 0.0,
            }
        row = by_discord[did]
        if user_id and not row.get("user_id"):
            row["user_id"] = user_id
        if username and not row.get("discord_username"):
            row["discord_username"] = username
        if signal not in row["buyer_signals"]:
            row["buyer_signals"].append(signal)
        row["buyer_score"] = float(row.get("buyer_score") or 0) + w

    # Explicit wallet / Discord bot intent registry
    for entry in _load_intent_registry().get("entries") or []:
        uid = (entry.get("user_id") or "").strip() or None
        did = str(entry.get("discord_id") or "").strip() or None
        if not did and uid:
            did = _resolve_discord_id(uid)
        if not did:
            continue
        _bump(did, uid, "wallet_intent_register")

    # PayPal / monetization payment ledger
    for entry in _read_jsonl(_PAYMENT_LEDGER):
        user_id = (entry.get("user_id") or "").strip() or None
        extra = entry.get("extra") if isinstance(entry.get("extra"), dict) else {}
        discord_id = str(extra.get("discord_id") or entry.get("discord_id") or "").strip() or None
        if not discord_id and user_id:
            discord_id = _resolve_discord_id(user_id)
        if not discord_id:
            continue
        item_id = str(entry.get("item_id") or "")
        item_name = str(entry.get("item_name") or "")
        if _item_matches_mn2_coin(item_id, item_name, hints):
            sig = "coin_pack_purchase" if "coin" in item_id.lower() or "coin" in item_name.lower() else "payment_ledger"
            _bump(discord_id, user_id, sig)

    # Discord promo redemptions (DISCORD-STARTER, etc.)
    if os.path.isfile(_DISCORD_PROMOS):
        try:
            with open(_DISCORD_PROMOS, "r", encoding="utf-8") as f:
                promo_doc = json.load(f)
            for promo in promo_doc.get("codes") or []:
                if not isinstance(promo, dict):
                    continue
                code = str(promo.get("code") or "").upper()
                if promo_codes and code not in promo_codes:
                    continue
                for uid in promo.get("redeemed_by") or []:
                    if not isinstance(uid, str):
                        continue
                    did = _resolve_discord_id(uid)
                    if did:
                        _bump(did, uid, "discord_promo_redeem")
        except Exception:
            pass

    # MN2 on-ramp orders (quoted / funded = buy intent)
    if os.path.isfile(_ONRAMP_ORDERS):
        try:
            with open(_ONRAMP_ORDERS, "r", encoding="utf-8") as f:
                orders = json.load(f)
            for order in (orders.values() if isinstance(orders, dict) else []):
                if not isinstance(order, dict):
                    continue
                uid = (order.get("user_id") or "").strip() or None
                if not uid:
                    continue
                did = _resolve_discord_id(uid)
                if not did:
                    continue
                status = (order.get("status") or "").strip()
                if status in ("held", "cleared"):
                    _bump(did, uid, "mn2_onramp_funded")
                elif status in ("quoted", "pending_payment"):
                    _bump(did, uid, "mn2_onramp_quote")
        except Exception:
            pass

    # Exchange PayPal MN2 pack orders (pending + captured)
    paypal_mn2_orders = os.path.join(_BASE, "data", "crypto_exchange", "paypal_mn2_orders.json")
    if os.path.isfile(paypal_mn2_orders):
        try:
            with open(paypal_mn2_orders, "r", encoding="utf-8") as f:
                orders_doc = json.load(f)
            for bucket in ("pending", "captured"):
                for order in (orders_doc.get(bucket) or {}).values():
                    if not isinstance(order, dict):
                        continue
                    uid = (order.get("user_id") or "").strip() or None
                    if not uid:
                        continue
                    did = _resolve_discord_id(uid)
                    if not did:
                        continue
                    sig = "mn2_onramp_funded" if bucket == "captured" else "mn2_onramp_quote"
                    _bump(did, uid, sig)
        except Exception:
            pass

    # MN2 ledger on-ramp purchases for linked users
    if os.path.isfile(_MN2_LEDGER):
        try:
            with open(_MN2_LEDGER, "r", encoding="utf-8") as f:
                ledger = json.load(f)
            entries = ledger.get("entries") if isinstance(ledger, dict) else ledger
            for entry in entries or []:
                if not isinstance(entry, dict):
                    continue
                if entry.get("type") not in ("onramp_purchase", "shop_payment", "deposit"):
                    continue
                uid = (entry.get("user_id") or "").strip() or None
                if not uid:
                    continue
                meta = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
                if entry.get("type") == "onramp_purchase":
                    did = _resolve_discord_id(uid)
                    if did:
                        _bump(did, uid, "mn2_onramp_funded")
                elif entry.get("type") == "shop_payment":
                    iid = str(meta.get("item_id") or "")
                    if _item_matches_mn2_coin(iid, "", hints):
                        did = _resolve_discord_id(uid)
                        if did:
                            _bump(did, uid, "coin_pack_purchase")
        except Exception:
            pass

    # Discord click / referral trail (casino discord-play, affiliate links)
    for click in _read_jsonl(_DISCORD_CLICKS):
        user_id = (click.get("user_id") or "").strip() or None
        link_id = str(click.get("link_id") or "")
        meta = click.get("meta") if isinstance(click.get("meta"), dict) else {}
        if not user_id:
            continue
        did = _resolve_discord_id(user_id)
        if not did:
            continue
        if "discord" in link_id.lower() or meta.get("source") in ("affiliate_rotator", "promo_rotator"):
            sig = "casino_discord_play" if "casino" in link_id.lower() or "play" in link_id.lower() else "discord_click"
            _bump(did, user_id, sig)

    threshold = float(cfg.get("buyer_signal_threshold") or 0)
    return [row for row in by_discord.values() if float(row.get("buyer_score") or 0) >= threshold]


def _canonical_source(sources: Set[str]) -> str:
    if not sources:
        return "unknown"
    ordered_legacy = [_SOURCE_LOCAL, _SOURCE_API, _SOURCE_BUYER]
    legacy_present = [s for s in ordered_legacy if s in sources]
    granular = sorted(s for s in sources if s not in ordered_legacy)
    if granular:
        if len(granular) == 1 and not legacy_present:
            return granular[0]
        parts = legacy_present + granular
        if len(parts) == 1:
            return parts[0]
        if len(legacy_present) >= 3:
            return "all"
        return "+".join(parts[:4]) + ("+more" if len(parts) > 4 else "")
    if len(legacy_present) == 0:
        return "unknown"
    if len(legacy_present) == 1:
        return legacy_present[0]
    if len(legacy_present) >= 3:
        return "all"
    return "+".join(legacy_present)


def _source_weight(source_id: str, cfg: Dict[str, Any]) -> int:
    pw = cfg.get("priority_weights") or {}
    if source_id in pw:
        return int(pw.get(source_id) or 0)
    legacy_map = {
        "local_linked": "local_linked",
        "discord_api_guild": "discord_api",
        "discord_api_channel": "discord_api",
        "discord_api": "discord_api",
        "purchase_intent": "purchase_intent",
    }
    legacy_key = legacy_map.get(source_id)
    if legacy_key:
        return int(pw.get(legacy_key) or 0)
    try:
        from backend.services.community_ledger_population import load_population_catalog

        for entry in load_population_catalog().get("sources") or []:
            if entry.get("id") == source_id:
                return int(entry.get("weight") or 0)
    except Exception:
        pass
    return 0


def _priority_score(sources: Set[str], buyer_score: float, linked: bool, cfg: Dict[str, Any]) -> int:
    score = int(buyer_score)
    for sid in sources:
        score += _source_weight(sid, cfg)
    if linked and (_SOURCE_BUYER in sources or "purchase_intent" in sources):
        score += int((cfg.get("priority_weights") or {}).get("linked_and_buyer") or 0)
    return score


def _row_identity_keys(row: Dict[str, Any]) -> List[str]:
    keys: List[str] = []
    did = str(row.get("discord_id") or "").strip()
    yid = str(row.get("youtube_id") or "").strip()
    fid = str(row.get("facebook_id") or "").strip()
    uid = str(row.get("user_id") or "").strip()
    if did:
        keys.append(f"discord:{did}")
    if yid:
        keys.append(f"youtube:{yid}")
    if fid:
        keys.append(f"facebook:{fid}")
    if uid:
        keys.append(f"user:{uid}")
    return keys


def _new_merge_key(row: Dict[str, Any]) -> str:
    keys = _row_identity_keys(row)
    if keys:
        return keys[0]
    name = str(row.get("display_name") or row.get("discord_username") or "anon")
    return f"anon:{row.get('source_id', 'unknown')}:{name}"


def _merge_seed(merged: Dict[str, Dict[str, Any]], index: Dict[str, str], row: Dict[str, Any], source_key: str) -> None:
    """Merge a population row by discord/youtube/facebook/user id."""
    identity = _row_identity_keys(row)
    if not identity:
        identity = [_new_merge_key(row)]

    merge_key: Optional[str] = None
    for ik in identity:
        if ik in index:
            merge_key = index[ik]
            break
    if merge_key is None:
        merge_key = identity[0]
        merged[merge_key] = {
            "discord_id": row.get("discord_id"),
            "youtube_id": row.get("youtube_id"),
            "facebook_id": row.get("facebook_id"),
            "user_id": row.get("user_id"),
            "discord_username": row.get("discord_username") or row.get("display_name"),
            "display_name": row.get("display_name") or row.get("discord_username"),
            "sources": {source_key},
            "buyer_signals": list(row.get("buyer_signals") or []),
            "buyer_score": float(row.get("buyer_score") or 0),
        }
    else:
        existing = merged[merge_key]
        existing["sources"].add(source_key)
        for field in ("discord_id", "youtube_id", "facebook_id", "user_id"):
            if row.get(field) and not existing.get(field):
                existing[field] = row[field]
        if row.get("discord_username") and not existing.get("discord_username"):
            existing["discord_username"] = row["discord_username"]
        if row.get("display_name") and not existing.get("display_name"):
            existing["display_name"] = row["display_name"]
        for sig in row.get("buyer_signals") or []:
            if sig not in existing["buyer_signals"]:
                existing["buyer_signals"].append(sig)
        existing["buyer_score"] = max(float(existing.get("buyer_score") or 0), float(row.get("buyer_score") or 0))

    for ik in _row_identity_keys(merged[merge_key]):
        index[ik] = merge_key


def _mn2_balance_for_user(user_id: Optional[str]) -> float:
    if not user_id:
        return 0.0
    try:
        from backend.services.unified_points_database import unified_points_db

        pts = unified_points_db.get_all_points(user_id) or {}
        return float((pts.get("points") or {}).get("mn2_balance") or 0)
    except Exception:
        return 0.0


def _discord_username_for_user(user_id: str) -> Optional[str]:
    try:
        from backend.services.wallet_v2_service import _discord_profile_from_user

        profile = _discord_profile_from_user(user_id) or {}
        return profile.get("username")
    except Exception:
        return None


def _line_template(
    line_id: str,
    status: str = "pending",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    labels = {
        "account_link": "Account link verified",
        "role_sync": "Linked role metadata sync",
        "casino_vip_role": "Casino VIP role",
        "hosting_vip_role": "Hosting VIP role",
        "mn2_credit": "MN2 community credit",
        "trophy_grant": "Community trophy grant",
        "coin_pack_offer": "MN2 coin pack offer",
        "mn2_onramp_nudge": "MN2 on-ramp nudge",
        "paypal_mn2_bundle": "PayPal MN2 bundle offer",
    }
    row: Dict[str, Any] = {
        "id": line_id,
        "label": labels.get(line_id, line_id),
        "status": status,
        "fulfilled_at": _iso() if status == "fulfilled" else None,
    }
    if metadata:
        row["metadata"] = metadata
    return row


def _compute_order_lines(
    discord_id: str,
    user_id: Optional[str],
    mn2_balance: float,
    existing_lines: Optional[List[Dict[str, Any]]] = None,
    *,
    buyer_signals: Optional[List[str]] = None,
    buyer_score: float = 0.0,
    cfg: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    cfg = cfg or load_config()
    existing = {ln.get("id"): ln for ln in (existing_lines or []) if isinstance(ln, dict) and ln.get("id")}
    lines: List[Dict[str, Any]] = []
    signals = set(buyer_signals or [])

    linked = bool(user_id)
    min_vip = float(os.environ.get("CASINO_DISCORD_VIP_MIN_MN2", "100"))
    casino_vip = linked and mn2_balance >= min_vip
    hosting_vip = False
    if linked:
        try:
            from backend.services.discord_hosting_vip_service import check_hosting_vip_eligibility

            hosting_vip = bool((check_hosting_vip_eligibility(user_id) or {}).get("eligible"))
        except Exception:
            pass

    has_buyer_signal = bool(signals) and float(buyer_score or 0) >= float(cfg.get("buyer_signal_threshold") or 0)

    specs: List[Tuple[str, str]] = [
        ("account_link", "fulfilled" if linked else "pending"),
        ("role_sync", "fulfilled" if linked else "pending"),
        ("casino_vip_role", "fulfilled" if casino_vip else ("pending" if linked else "skipped")),
        ("hosting_vip_role", "fulfilled" if hosting_vip else ("pending" if linked else "skipped")),
        ("mn2_credit", "pending" if has_buyer_signal or linked else "skipped"),
        ("trophy_grant", "pending"),
    ]

    if has_buyer_signal:
        specs.extend([
            ("coin_pack_offer", "pending"),
            ("mn2_onramp_nudge", "pending" if "mn2_onramp_funded" not in signals else "skipped"),
            ("paypal_mn2_bundle", "pending" if any(s in signals for s in ("payment_ledger", "coin_pack_purchase")) else "skipped"),
        ])

    for line_id, default_status in specs:
        prev = existing.get(line_id) or {}
        if prev.get("status") == "fulfilled":
            lines.append(prev)
            continue
        status = default_status
        if status == "skipped":
            lines.append(_line_template(line_id, status="skipped"))
            continue
        meta: Dict[str, Any] = {}
        if line_id == "mn2_credit":
            meta["default_amount_mn2"] = float(os.environ.get("DISCORD_FULFILLMENT_MN2_CREDIT", "0") or 0)
            if has_buyer_signal:
                meta["buyer_signals"] = list(signals)
        if line_id == "trophy_grant":
            meta["trophy_sku"] = os.environ.get("DISCORD_FULFILLMENT_TROPHY_SKU", "discord-community")
        if line_id == "coin_pack_offer":
            meta["coin_pack_sku"] = cfg.get("default_coin_pack_sku") or "mn2-pack-s"
            meta["buyer_signals"] = list(signals)
        if line_id == "mn2_onramp_nudge":
            meta["onramp_url"] = cfg.get("default_onramp_nudge_url") or "/exchange?tab=onramp"
        if line_id == "paypal_mn2_bundle":
            meta["bundle_hint"] = "paypal_mn2"
        lines.append(_line_template(line_id, status=status, metadata=meta or None))

    return lines


def _aggregate_status(lines: List[Dict[str, Any]]) -> str:
    actionable = [ln for ln in lines if ln.get("status") not in ("skipped", "fulfilled")]
    if not actionable:
        fulfilled = [ln for ln in lines if ln.get("status") == "fulfilled"]
        return "fulfilled" if fulfilled else "pending"
    if all(ln.get("status") == "fulfilled" for ln in lines if ln.get("status") != "skipped"):
        return "fulfilled"
    if any(ln.get("status") == "fulfilled" for ln in lines):
        return "partial"
    return "pending"


def _load_ledger_doc() -> Dict[str, Any]:
    path = _ledger_path()
    with _LOCK:
        if not os.path.isfile(path):
            return {"version": 2, "updated_at": None, "rows": [], "meta": {}}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data.setdefault("rows", [])
                data.setdefault("meta", {})
                return data
        except Exception:
            pass
    return {"version": 2, "updated_at": None, "rows": [], "meta": {}}


def _save_ledger_doc(doc: Dict[str, Any]) -> None:
    os.makedirs(_data_dir(), exist_ok=True)
    doc["updated_at"] = _iso()
    path = _ledger_path()
    tmp = path + ".tmp"
    with _LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        os.replace(tmp, path)


def _save_order_list_export(doc: Dict[str, Any], rows: List[Dict[str, Any]]) -> None:
    meta = doc.get("meta") or {}
    export = {
        "generated_at": _iso(),
        "total": len(rows),
        "pending": sum(1 for r in rows if r.get("fulfillment_status") == "pending"),
        "partial": sum(1 for r in rows if r.get("fulfillment_status") == "partial"),
        "fulfilled": sum(1 for r in rows if r.get("fulfillment_status") == "fulfilled"),
        "sources": meta.get("sources", {}),
        "population_source_count": meta.get("population_source_count", 0),
        "overlaps": meta.get("overlaps", {}),
        "buyer_signal_count": meta.get("buyer_signal_count", 0),
        "discord_api_used": bool(meta.get("discord_api_used")),
        "orders": rows,
    }
    path = _order_list_path()
    tmp = path + ".tmp"
    with _LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(export, f, indent=2)
        os.replace(tmp, path)


def build_order_list(
    *,
    use_local: bool = True,
    use_discord_api: bool = True,
    use_buyer_signals: bool = True,
    use_all_sources: bool = True,
) -> Dict[str, Any]:
    """Aggregate community users from up to 25 population sources into fulfillment ledger."""
    cfg = load_config()
    existing_doc = _load_ledger_doc()
    existing_by_id: Dict[str, Dict[str, Any]] = {}
    for r in existing_doc.get("rows") or []:
        if not isinstance(r, dict):
            continue
        lid = str(r.get("ledger_row_id") or r.get("discord_id") or "").strip()
        if lid:
            existing_by_id[lid] = r
        did = str(r.get("discord_id") or "").strip()
        if did:
            existing_by_id[f"discord:{did}"] = r

    merged: Dict[str, Dict[str, Any]] = {}
    index: Dict[str, str] = {}
    source_counts: Dict[str, int] = {}
    overlap_counts: Dict[str, int] = {
        "local_and_api": 0,
        "local_and_buyer": 0,
        "api_and_buyer": 0,
        "all_three": 0,
    }
    api_used = False
    api_notes: List[str] = []

    if use_all_sources:
        try:
            from backend.services.community_ledger_population import scan_all_enabled_sources

            scan_result = scan_all_enabled_sources(use_discord_api=use_discord_api)
            api_used = bool(scan_result.get("api_used"))
            api_notes.extend(scan_result.get("api_notes") or [])
            source_counts.update(scan_result.get("source_counts") or {})
            for row in scan_result.get("rows") or []:
                sid = str(row.get("source_id") or "unknown")
                if sid == "local_linked" and not use_local:
                    continue
                if sid == "purchase_intent" and not use_buyer_signals:
                    continue
                _merge_seed(merged, index, row, sid)
        except Exception as exc:
            api_notes.append(f"population_scan: {exc}")
    else:
        if use_local:
            for row in scan_local_linked_users():
                _merge_seed(merged, index, row, _SOURCE_LOCAL)
        if use_discord_api and _bot_token():
            guild_result = fetch_discord_guild_members()
            if guild_result.get("api_used"):
                api_used = True
            if guild_result.get("error"):
                api_notes.append(f"guild_members: {guild_result['error']}")
            for row in guild_result.get("members") or []:
                _merge_seed(merged, index, row, "discord_api_guild")
            channel_result = fetch_discord_channel_authors()
            if channel_result.get("api_used"):
                api_used = True
            if channel_result.get("error"):
                api_notes.append(f"channel_authors: {channel_result['error']}")
            for row in channel_result.get("members") or []:
                _merge_seed(merged, index, row, "discord_api_channel")
        if use_buyer_signals:
            for row in scan_purchase_intent_buyers():
                _merge_seed(merged, index, row, _SOURCE_BUYER)

    for _mk, seed in merged.items():
        srcs: Set[str] = set(seed.get("sources") or [])
        has_api = bool(srcs & {"discord_api", "discord_api_guild", "discord_api_channel"})
        has_local = _SOURCE_LOCAL in srcs or "local_linked" in srcs
        has_buyer = _SOURCE_BUYER in srcs or "purchase_intent" in srcs
        if has_local and has_api:
            overlap_counts["local_and_api"] += 1
        if has_local and has_buyer:
            overlap_counts["local_and_buyer"] += 1
        if has_api and has_buyer:
            overlap_counts["api_and_buyer"] += 1
        if has_local and has_api and has_buyer:
            overlap_counts["all_three"] += 1

    if not source_counts:
        source_counts = {_SOURCE_LOCAL: 0, _SOURCE_API: 0, _SOURCE_BUYER: 0}
        for seed in merged.values():
            for s in seed.get("sources") or set():
                source_counts[s] = source_counts.get(s, 0) + 1

    rows_out: List[Dict[str, Any]] = []
    for merge_key, seed in merged.items():
        discord_id = seed.get("discord_id")
        user_id = seed.get("user_id")
        if discord_id and not user_id:
            user_id = _resolve_user_id(str(discord_id))
        if user_id and not discord_id:
            discord_id = _resolve_discord_id(user_id)
        mn2_balance = _mn2_balance_for_user(user_id)
        username = seed.get("discord_username") or seed.get("display_name")
        if not username and user_id:
            username = _discord_username_for_user(user_id)

        sources_set: Set[str] = set(seed.get("sources") or [])
        buyer_signals = list(seed.get("buyer_signals") or [])
        buyer_score = float(seed.get("buyer_score") or 0)
        linked = bool(user_id)
        priority = _priority_score(sources_set, buyer_score, linked, cfg)

        prev_key = merge_key
        if discord_id and f"discord:{discord_id}" in existing_by_id:
            prev_key = f"discord:{discord_id}"
        prev = existing_by_id.get(prev_key) or existing_by_id.get(merge_key) or {}
        lines = _compute_order_lines(
            str(discord_id or merge_key),
            user_id,
            mn2_balance,
            existing_lines=prev.get("order_lines"),
            buyer_signals=buyer_signals,
            buyer_score=buyer_score,
            cfg=cfg,
        )
        row = {
            "ledger_row_id": prev.get("ledger_row_id") or merge_key,
            "discord_id": discord_id,
            "youtube_id": seed.get("youtube_id"),
            "facebook_id": seed.get("facebook_id"),
            "discord_username": username,
            "display_name": seed.get("display_name") or username,
            "user_id": user_id,
            "mn2_balance": mn2_balance,
            "source": _canonical_source(sources_set),
            "sources": sorted(sources_set),
            "source_count": len(sources_set),
            "buyer_signal": bool(buyer_signals) and buyer_score >= float(cfg.get("buyer_signal_threshold") or 0),
            "buyer_signals": buyer_signals,
            "buyer_score": buyer_score,
            "priority_score": priority,
            "fulfillment_status": _aggregate_status(lines),
            "order_lines": lines,
            "mn2_coin_offer_status": _mn2_coin_offer_status(lines),
            "created_at": prev.get("created_at") or _iso(),
            "updated_at": _iso(),
        }
        rows_out.append(row)

    rows_out.sort(
        key=lambda r: (
            -int(r.get("priority_score") or 0),
            -float(r.get("buyer_score") or 0),
            -int(r.get("source_count") or 0),
            r.get("created_at") or "",
        )
    )
    for rank, row in enumerate(rows_out, start=1):
        row["ledger_rank"] = rank

    doc = {
        "version": 3,
        "updated_at": _iso(),
        "rows": rows_out,
        "meta": {
            "sources": source_counts,
            "population_source_count": len(source_counts),
            "overlaps": overlap_counts,
            "buyer_signal_count": sum(1 for r in rows_out if r.get("buyer_signal")),
            "discord_api_used": api_used,
            "discord_api_notes": api_notes,
            "bot_configured": bool(_bot_token()),
            "guild_configured": bool(_guild_id()),
            "mn2_channel_configured": bool(_mn2_channel_id()),
            "sources_enabled": {
                "local": use_local,
                "discord_api": use_discord_api,
                "buyer_signals": use_buyer_signals,
                "all_population_sources": use_all_sources,
            },
        },
    }
    _save_ledger_doc(doc)
    _save_order_list_export(doc, rows_out)

    return {
        "success": True,
        "total": len(rows_out),
        "pending": sum(1 for r in rows_out if r.get("fulfillment_status") == "pending"),
        "partial": sum(1 for r in rows_out if r.get("fulfillment_status") == "partial"),
        "fulfilled": sum(1 for r in rows_out if r.get("fulfillment_status") == "fulfilled"),
        "discord_api_used": api_used,
        "sources": source_counts,
        "overlaps": overlap_counts,
        "buyer_signal_count": doc["meta"]["buyer_signal_count"],
        "api_notes": api_notes,
        "ledger_path": _LEDGER_FILE,
        "order_list_path": _ORDER_LIST_FILE,
    }


def _mn2_coin_offer_status(lines: List[Dict[str, Any]]) -> str:
    offer_ids = ("coin_pack_offer", "mn2_onramp_nudge", "paypal_mn2_bundle", "mn2_credit")
    relevant = [ln for ln in lines if ln.get("id") in offer_ids and ln.get("status") != "skipped"]
    if not relevant:
        return "none"
    if all(ln.get("status") == "fulfilled" for ln in relevant):
        return "fulfilled"
    if any(ln.get("status") == "fulfilled" for ln in relevant):
        return "partial"
    return "pending"


def get_order_list() -> Dict[str, Any]:
    doc = _load_ledger_doc()
    rows = doc.get("rows") or []
    return {
        "success": True,
        "total": len(rows),
        "pending": sum(1 for r in rows if r.get("fulfillment_status") == "pending"),
        "partial": sum(1 for r in rows if r.get("fulfillment_status") == "partial"),
        "fulfilled": sum(1 for r in rows if r.get("fulfillment_status") == "fulfilled"),
        "updated_at": doc.get("updated_at"),
        "meta": doc.get("meta") or {},
        "orders": rows,
    }


def get_row_for_discord(discord_id: str) -> Optional[Dict[str, Any]]:
    did = (discord_id or "").strip()
    if not did:
        return None
    for row in _load_ledger_doc().get("rows") or []:
        if str(row.get("discord_id")) == did:
            return row
    return None


def get_row_by_id(ledger_row_id: str) -> Optional[Dict[str, Any]]:
    lid = (ledger_row_id or "").strip()
    if not lid:
        return None
    for row in _load_ledger_doc().get("rows") or []:
        if str(row.get("ledger_row_id")) == lid or str(row.get("discord_id")) == lid:
            return row
    return None


def get_user_fulfillment_status(user_id: str) -> Dict[str, Any]:
    user_id = (user_id or "").strip()
    if not user_id or user_id in ("default_user", "guest"):
        return {"success": True, "user_id": user_id, "guest": True, "in_order_list": False}

    discord_id: Optional[str] = None
    try:
        from backend.services.discord_link_service import get_discord_id_for_user

        discord_id = get_discord_id_for_user(user_id)
    except Exception:
        pass

    if not discord_id:
        return {
            "success": True,
            "user_id": user_id,
            "linked": False,
            "in_order_list": False,
            "message": "Link Discord to appear on the community fulfillment order list.",
        }

    row = get_row_for_discord(discord_id)
    if not row:
        build_order_list(use_local=True, use_discord_api=False, use_buyer_signals=True)
        row = get_row_for_discord(discord_id)

    return {
        "success": True,
        "user_id": user_id,
        "linked": True,
        "discord_id": discord_id,
        "in_order_list": bool(row),
        "fulfillment_status": (row or {}).get("fulfillment_status"),
        "order_lines": (row or {}).get("order_lines") or [],
        "mn2_balance": (row or {}).get("mn2_balance"),
        "source": (row or {}).get("source"),
        "sources": (row or {}).get("sources") or [],
        "buyer_signal": (row or {}).get("buyer_signal"),
        "buyer_signals": (row or {}).get("buyer_signals") or [],
        "mn2_coin_offer_status": (row or {}).get("mn2_coin_offer_status"),
        "priority_score": (row or {}).get("priority_score"),
        "order_list_api": "/api/discord/fulfillment/order-list",
    }


def _apply_line_fulfillment(
    row: Dict[str, Any],
    line_items: Optional[List[str]] = None,
    *,
    operator: Optional[str] = None,
) -> Dict[str, Any]:
    cfg = load_config()
    targets = set(line_items or [ln.get("id") for ln in row.get("order_lines") or [] if ln.get("status") == "pending"])
    applied: List[str] = []
    errors: List[str] = []
    user_id = row.get("user_id")
    discord_id = row.get("discord_id")

    for ln in row.get("order_lines") or []:
        lid = ln.get("id")
        if lid not in targets or ln.get("status") in ("fulfilled", "skipped"):
            continue

        if lid == "mn2_credit":
            amount = float((ln.get("metadata") or {}).get("amount_mn2") or (ln.get("metadata") or {}).get("default_amount_mn2") or 0)
            if amount > 0 and user_id:
                try:
                    from backend.services.unified_points_database import unified_points_db

                    ref = f"discord_fulfill:{discord_id}:{lid}"
                    unified_points_db.add_points(
                        user_id,
                        "mn2_balance",
                        amount,
                        source="discord_fulfillment",
                        metadata={"discord_id": discord_id, "reference": ref, "operator": operator},
                    )
                    try:
                        from backend.services.mn2_ledger import append_entry

                        append_entry(
                            user_id,
                            "deposit",
                            amount,
                            metadata={"source": "discord_fulfillment", "discord_id": discord_id, "reference": ref},
                        )
                    except Exception:
                        pass
                except Exception as exc:
                    errors.append(f"mn2_credit: {exc}")
                    continue

        if lid == "role_sync" and user_id:
            try:
                from backend.services.discord_linked_roles_service import build_metadata_for_user

                build_metadata_for_user(user_id)
            except Exception as exc:
                errors.append(f"role_sync: {exc}")
                continue

        if lid == "hosting_vip_role" and user_id:
            try:
                from backend.services.discord_hosting_vip_service import grant_hosting_vip_role

                grant_hosting_vip_role(user_id, reason="discord_fulfillment")
            except Exception as exc:
                errors.append(f"hosting_vip_role: {exc}")
                continue

        if lid == "trophy_grant" and user_id:
            sku = (ln.get("metadata") or {}).get("trophy_sku") or "discord-community"
            try:
                from backend.routes.shop_routes import _apply_shop_item_effects, _get_shop_items

                item = next((i for i in (_get_shop_items() or []) if i.get("id") == sku), None)
                if item:
                    _apply_shop_item_effects(
                        user_id,
                        sku,
                        item,
                        1,
                        purchase_ref=f"discord_fulfill:{discord_id}",
                    )
            except Exception as exc:
                errors.append(f"trophy_grant: {exc}")
                continue

        if lid == "coin_pack_offer" and user_id:
            sku = (ln.get("metadata") or {}).get("coin_pack_sku") or cfg.get("default_coin_pack_sku") or "mn2-pack-s"
            try:
                from backend.services.shop_mn2_fulfillment_service import apply_mn2_grants_for_purchase

                apply_mn2_grants_for_purchase(
                    user_id,
                    sku,
                    None,
                    1,
                    source="discord_fulfillment_coin_pack",
                    reference=f"discord_fulfill:{discord_id}:coin_pack",
                )
            except Exception as exc:
                errors.append(f"coin_pack_offer: {exc}")
                continue

        if lid == "mn2_onramp_nudge" and user_id:
            ln.setdefault("metadata", {})["offer_sent"] = True
            ln["metadata"]["onramp_url"] = (ln.get("metadata") or {}).get("onramp_url") or cfg.get("default_onramp_nudge_url")

        if lid == "paypal_mn2_bundle" and user_id:
            micro = float(os.environ.get("DISCORD_FULFILLMENT_MN2_CREDIT", "0") or 0)
            if micro > 0:
                try:
                    from backend.services.unified_points_database import unified_points_db

                    ref = f"discord_fulfill:{discord_id}:paypal_bundle"
                    unified_points_db.add_points(
                        user_id,
                        "mn2_balance",
                        micro,
                        source="discord_fulfillment_paypal_bundle",
                        metadata={"discord_id": discord_id, "reference": ref, "operator": operator},
                    )
                except Exception as exc:
                    errors.append(f"paypal_mn2_bundle: {exc}")
                    continue
            ln.setdefault("metadata", {})["offer_sent"] = True

        ln["status"] = "fulfilled"
        ln["fulfilled_at"] = _iso()
        if operator:
            ln.setdefault("metadata", {})["operator"] = operator
        applied.append(lid)

    row["order_lines"] = _compute_order_lines(
        str(row.get("discord_id")),
        row.get("user_id"),
        float(row.get("mn2_balance") or 0),
        existing_lines=row.get("order_lines"),
        buyer_signals=row.get("buyer_signals"),
        buyer_score=float(row.get("buyer_score") or 0),
        cfg=cfg,
    )
    row["fulfillment_status"] = _aggregate_status(row["order_lines"])
    row["mn2_coin_offer_status"] = _mn2_coin_offer_status(row["order_lines"])
    row["updated_at"] = _iso()
    return {"applied": applied, "errors": errors}


def fulfill_order(
    discord_id: str,
    line_items: Optional[List[str]] = None,
    *,
    operator: Optional[str] = None,
) -> Dict[str, Any]:
    did = (discord_id or "").strip()
    if not did:
        return {"success": False, "error": "discord_id required"}

    doc = _load_ledger_doc()
    rows = doc.get("rows") or []
    target = next((r for r in rows if str(r.get("discord_id")) == did), None)
    if not target:
        build_order_list(use_local=True, use_discord_api=False, use_buyer_signals=True)
        doc = _load_ledger_doc()
        rows = doc.get("rows") or []
        target = next((r for r in rows if str(r.get("discord_id")) == did), None)
    if not target:
        return {"success": False, "error": "discord_id_not_in_order_list", "discord_id": did}

    result = _apply_line_fulfillment(target, line_items, operator=operator)
    _save_ledger_doc(doc)
    _save_order_list_export(doc, rows)

    return {
        "success": len(result["errors"]) == 0,
        "discord_id": did,
        "fulfillment_status": target.get("fulfillment_status"),
        "mn2_coin_offer_status": target.get("mn2_coin_offer_status"),
        "applied": result["applied"],
        "errors": result["errors"],
    }


def fulfill_all_pending(*, limit: int = 100, operator: Optional[str] = None) -> Dict[str, Any]:
    doc = _load_ledger_doc()
    rows = doc.get("rows") or []
    processed = 0
    fulfilled_count = 0
    errors: List[Dict[str, Any]] = []

    for row in rows:
        if row.get("fulfillment_status") not in ("pending", "partial"):
            continue
        if processed >= limit:
            break
        pending_lines = [ln.get("id") for ln in row.get("order_lines") or [] if ln.get("status") == "pending"]
        if not pending_lines:
            continue
        if not row.get("user_id"):
            errors.append({"discord_id": row.get("discord_id"), "error": "no_linked_user"})
            processed += 1
            continue
        result = _apply_line_fulfillment(row, pending_lines, operator=operator)
        if result["errors"]:
            errors.append({"discord_id": row.get("discord_id"), "errors": result["errors"]})
        else:
            fulfilled_count += 1
        processed += 1

    _save_ledger_doc(doc)
    _save_order_list_export(doc, rows)

    return {
        "success": True,
        "processed": processed,
        "fulfilled_users": fulfilled_count,
        "errors": errors,
        "remaining_pending": sum(1 for r in rows if r.get("fulfillment_status") in ("pending", "partial")),
    }
