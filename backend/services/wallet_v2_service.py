"""
Wallet v2 summary facade — fast overview without deposit RPC.
Delegates to existing MN2 wallet, ledger, chainz, and shop inventory services.
"""
import json
import os
import urllib.parse
from typing import Any, Dict, List, Optional, Set

_DEFAULT_SECTIONS = ("balance", "trophy_counts", "flags", "network")


def _config_path() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "data", "mn2_config.json")


def load_wallet_config() -> Dict[str, Any]:
    path = _config_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    return loaded
        except Exception:
            pass
    return {}


def _parse_sections(raw: Optional[str]) -> Set[str]:
    if not (raw or "").strip():
        return set(_DEFAULT_SECTIONS)
    return {s.strip().lower() for s in raw.split(",") if s.strip()}


def _trophy_counts(user_id: str) -> Dict[str, int]:
    """Count shop trophy SKUs (top25-* prefix) from inventory — no RPC."""
    counts = {"total": 0, "top25_owned": 0, "shop_items": 0}
    if not (user_id or "").strip():
        return counts
    try:
        from backend.services.shop_db_service import get_inventory
        inventory = get_inventory(user_id) or []
    except Exception:
        inventory = []
    for item in inventory:
        if not isinstance(item, dict):
            continue
        item_id = (item.get("item_id") or "").strip()
        qty = int(item.get("quantity") or 0)
        if qty <= 0:
            continue
        counts["shop_items"] += qty
        if item_id.startswith("top25-"):
            counts["top25_owned"] += qty
            counts["total"] += qty
    return counts


def _network_snapshot() -> Dict[str, Any]:
    """Rich network KPIs from cached chainz overview — best-effort, never raises."""
    out: Dict[str, Any] = {
        "block_height": None,
        "connections": None,
        "mempool_tx": None,
        "mempool_bytes": None,
        "mn2_usd_price": None,
        "pool_apr_percent": None,
        "pool_total_staked": None,
        "masternode_count": None,
        "masternode_enabled": None,
        "sync_ok": None,
        "difficulty": None,
        "network_hashps": None,
        "staking_weight": None,
        "expected_stake_time_sec": None,
        "circulating_supply": None,
        "daemon_version": None,
        "daemon_subversion": None,
        "chain": None,
        "verification_progress": None,
        "headers": None,
        "median_time": None,
        "staking_health": None,
        "peer_health": None,
        "rpc_degraded": None,
        "source": {},
    }
    try:
        from backend.services import mn2_chainz
        overview = mn2_chainz.network_overview() or {}
        out["block_height"] = overview.get("block_height")
        out["connections"] = overview.get("connections")
        out["mempool_tx"] = overview.get("mempool_tx")
        out["difficulty"] = overview.get("difficulty")
        out["network_hashps"] = overview.get("network_hashps")
        out["staking_weight"] = overview.get("staking_weight")
        out["expected_stake_time_sec"] = overview.get("expected_stake_time_sec")
        out["circulating_supply"] = overview.get("circulating_supply")
        out["mn2_usd_price"] = overview.get("mn2_usd_price")
        out["masternode_count"] = overview.get("masternode_count")
        if isinstance(overview.get("source"), dict):
            out["source"] = overview.get("source")
        daemon = overview.get("daemon") if isinstance(overview.get("daemon"), dict) else {}
        out["mempool_bytes"] = daemon.get("mempool_bytes")
        out["daemon_version"] = daemon.get("version")
        out["daemon_subversion"] = daemon.get("subversion")
        out["chain"] = daemon.get("chain")
        out["verification_progress"] = daemon.get("verification_progress")
        out["headers"] = daemon.get("headers")
        out["median_time"] = daemon.get("median_time")
        if daemon.get("reachable") is not None:
            out["sync_ok"] = bool(daemon.get("reachable"))
        if overview.get("rpc_degraded"):
            out["rpc_degraded"] = True
    except Exception:
        pass
    try:
        from backend.services import mn2_staking_service as staking
        out["pool_apr_percent"] = staking.dynamic_apr()
        out["pool_total_staked"] = staking.total_staked()
    except Exception:
        pass
    try:
        from backend.services.mn2_explorer_data import masternodes
        mn = masternodes(limit=5) or {}
        out["masternode_enabled"] = mn.get("enabled")
        if out["masternode_count"] is None and mn.get("total"):
            out["masternode_count"] = mn.get("total")
    except Exception:
        pass
    try:
        from backend.services import mn2_rpc_client
        sh = mn2_rpc_client.staking_health()
        if isinstance(sh, dict):
            out["staking_health"] = sh
    except Exception:
        pass
    try:
        from backend.services.mn2_network_peers_service import peer_health_from_overview
        from backend.services import mn2_chainz
        overview = mn2_chainz.network_overview() or {}
        out["peer_health"] = peer_health_from_overview(overview)
    except Exception:
        pass
    return out


def build_summary(user_id: str, sections_raw: Optional[str] = None) -> Dict[str, Any]:
    """
    Assemble wallet v2 summary. Never calls get_or_create_deposit_address.
    """
    sections = _parse_sections(sections_raw)
    cfg = load_wallet_config()
    payload: Dict[str, Any] = {
        "success": True,
        "user_id": user_id,
        "sections": sorted(sections),
        "wallet_v2_enabled": bool(cfg.get("wallet_v2_enabled", True)),
        "wallet_fun_mode": bool(cfg.get("wallet_fun_mode", False)),
        "wallet_v2_default_tab": (cfg.get("wallet_v2_default_tab") or "overview").strip(),
    }

    if "flags" in sections:
        try:
            from backend.services.mn2_explorer_urls import explorer_base_url
            payload["explorer_base_url"] = explorer_base_url()
        except Exception:
            payload["explorer_base_url"] = (cfg.get("explorer_base_url") or "").strip() or None
        payload["coins_per_mn2"] = float(cfg.get("coins_per_mn2") or 100)
        if cfg.get("withdrawal_requires_verification"):
            try:
                from backend.services.mn2_verification import is_verified
                payload["withdrawal_verified"] = is_verified(user_id or "")
            except Exception:
                payload["withdrawal_verified"] = False

    if "balance" in sections:
        from backend.services.mn2_wallet_service import get_balance
        bal = get_balance(user_id)
        payload["mn2_balance"] = float(bal.get("mn2_balance") or 0) if bal.get("success") else 0.0
        payload["balance_ok"] = bool(bal.get("success"))
        try:
            from backend.services.mn2_hold_registry import get_holds
            holds = get_holds(user_id)
            payload["liquid_mn2"] = holds.get("liquid_mn2")
            payload["held_mn2"] = holds.get("held_mn2")
            payload["withdrawable_mn2"] = holds.get("withdrawable_mn2")
        except Exception:
            pass
        if payload.get("mn2_usd_price") is None:
            try:
                from backend.services.mn2_chainz import chainz_ticker_usd_with_updated
                ticker = chainz_ticker_usd_with_updated()
                if isinstance(ticker, dict) and ticker.get("price") is not None:
                    payload["mn2_usd_price"] = round(float(ticker["price"]), 8)
            except Exception:
                pass

    if "trophy_counts" in sections:
        payload["trophy_counts"] = _trophy_counts(user_id)

    if "network" in sections:
        payload["network"] = _network_snapshot()
        if payload.get("mn2_usd_price") is None and payload["network"].get("mn2_usd_price") is not None:
            payload["mn2_usd_price"] = payload["network"]["mn2_usd_price"]

    return payload


def _discord_invite_url() -> Optional[str]:
    try:
        import json as _json

        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data",
            "casino_config.json",
        )
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                cfg = _json.load(f)
            discord_cfg = cfg.get("discord_integration") if isinstance(cfg, dict) else {}
            if isinstance(discord_cfg, dict):
                url = (discord_cfg.get("invite_url") or "").strip()
                if url:
                    return url
    except Exception:
        pass
    return (os.environ.get("DISCORD_INVITE_URL") or "https://discord.gg/masternoder").strip() or None


def _discord_profile_from_user(user_id: str) -> Dict[str, Any]:
    """Best-effort Discord display fields from profile preferences."""
    out: Dict[str, Any] = {"username": None, "avatar_url": None}
    if not (user_id or "").strip():
        return out
    try:
        from backend.services.user_onboarding import user_onboarding

        profile = user_onboarding.get_user_profile(user_id) or {}
        prefs_raw = profile.get("preferences")
        if isinstance(prefs_raw, str):
            prefs = json.loads(prefs_raw) if prefs_raw.strip() else {}
        elif isinstance(prefs_raw, dict):
            prefs = prefs_raw
        else:
            prefs = {}
        social = prefs.get("social_auth") if isinstance(prefs.get("social_auth"), dict) else {}
        if (social.get("provider") or "").lower() == "discord":
            out["username"] = social.get("email") or profile.get("username")
            out["avatar_url"] = social.get("avatar")
        out["username"] = out["username"] or prefs.get("discord_username") or prefs.get("display_name") or profile.get("username")
        out["avatar_url"] = out["avatar_url"] or prefs.get("discord_avatar_url") or prefs.get("avatar_url") or profile.get("avatar_url")
    except Exception:
        pass
    return out


def build_discord_status(user_id: str) -> Dict[str, Any]:
    """Wallet Discord panel — wraps discord_link_service and linked-role OAuth."""
    user_id = (user_id or "").strip() or "default_user"
    guest = user_id in ("", "default_user", "guest")
    invite = _discord_invite_url()
    payload: Dict[str, Any] = {
        "success": True,
        "user_id": user_id,
        "guest": guest,
        "linked": False,
        "discord_id": None,
        "server_invite_url": invite,
        "manual_link_supported": True,
        "profile_discord_path": "/profile#discord-link-card",
        "share_supported": bool(os.environ.get("DISCORD_WEBHOOK_URL")),
        "notification_prefs": {
            "balance_alerts": False,
            "trophy_drops": False,
            "block_trophy_mint": False,
            "battle_results": False,
        },
        "notification_prefs_note": (
            "Per-user Discord DM notifications require bot DM scope — "
            "toggles are saved locally until WR-DISCORD-2 ships server prefs."
        ),
        "roles_available": [],
    }
    if guest:
        payload["message"] = "Sign in with a Profile account to link Discord."
        payload["oauth_login_configured"] = False
        return payload

    from backend.services.discord_link_service import link_status

    status = link_status(user_id) or {}
    payload.update(
        {
            "linked": bool(status.get("linked")),
            "discord_id": status.get("discord_id"),
            "mn2_balance": status.get("mn2_balance"),
            "casino_vip_eligible": status.get("casino_vip_eligible"),
            "min_mn2_for_vip": status.get("min_mn2_for_vip"),
            "hosting_customer": status.get("hosting_customer"),
            "hosting_vip_eligible": status.get("hosting_vip_eligible"),
            "hosting_vip_message": status.get("hosting_vip_message"),
        }
    )
    profile = _discord_profile_from_user(user_id)
    payload["username"] = profile.get("username")
    payload["avatar_url"] = profile.get("avatar_url")

    roles: List[str] = []
    if payload.get("linked"):
        roles.append("linked")
    if payload.get("casino_vip_eligible"):
        roles.append("casino_vip")
    if payload.get("hosting_vip_eligible"):
        roles.append("hosting_vip")
    payload["roles_available"] = roles

    try:
        from backend.services.discord_linked_roles_service import configured as linked_role_configured

        payload["linked_role_configured"] = bool(linked_role_configured())
        payload["linked_role_verification_path"] = "/api/discord/linked-role"
        if payload["linked_role_configured"]:
            payload["linked_role_connect_path"] = (
                f"/api/discord/linked-role?user_id={urllib.parse.quote(user_id)}&redirect=1"
            )
    except Exception:
        payload["linked_role_configured"] = False

    try:
        from backend.services.social_auth_service import list_providers

        providers = list_providers().get("providers") or []
        discord_provider = next((p for p in providers if p.get("id") == "discord"), None)
        if discord_provider and discord_provider.get("configured"):
            payload["oauth_login_configured"] = True
            return_url = urllib.parse.quote("/wallets?tab=settings&panel=discord")
            payload["oauth_login_start_path"] = (
                f"/api/auth/discord/start?redirect=1&return_url={return_url}"
                f"&user_id_hint={urllib.parse.quote(user_id)}"
            )
        else:
            payload["oauth_login_configured"] = False
    except Exception:
        payload["oauth_login_configured"] = False

    return payload


# Canonical site feature matrix for wallet Site Features Hub (WR-PORTAL).
_SITE_FEATURES: List[Dict[str, Any]] = [
    {"id": "portal", "name": "Command Center", "icon": "🌀", "path": "/command-center", "category": "portal", "primary": True, "description": "Battle · Trophies · Game · Quests · Podcast hub with MN2 rewards"},
    {"id": "rewards", "name": "Rewards & Points", "icon": "💎", "path": "/profile?tab=points", "category": "rewards", "primary": True, "description": "Unified points, XP, quests, achievements, and trophy score"},
    {"id": "shop", "name": "Shop", "icon": "🛒", "path": "/shop", "category": "commerce", "description": "Trophies, boosts, digital goods, PayPal on-ramp"},
    {"id": "exchange", "name": "Exchange", "icon": "💱", "path": "/exchange", "category": "commerce", "description": "25-crypto swap, limits, staking, tax records"},
    {"id": "wallets", "name": "Wallets", "icon": "💾", "path": "/wallets", "category": "wallet", "description": "MN2 deposit, withdraw, monitors, upgrades"},
    {"id": "generator", "name": "Generator", "icon": "🎬", "path": "/generator", "category": "create", "description": "AI video and content generation"},
    {"id": "game", "name": "Game", "icon": "🎮", "path": "/game", "category": "play", "description": "Hunters game mode and progression"},
    {"id": "battle", "name": "Battle", "icon": "⚔️", "path": "/battle", "category": "play", "description": "Tournaments, quick battle, fantasy arena"},
    {"id": "trophies", "name": "Trophies", "icon": "🏆", "path": "/trophies", "category": "collect", "description": "Hunter trophies and social leaderboard"},
    {"id": "quests", "name": "Quests", "icon": "📜", "path": "/quests", "category": "rewards", "description": "Quest MN2 rewards, XP, and streaks"},
    {"id": "explorer", "name": "Explorer", "icon": "🔎", "path": "/explorer", "category": "network", "description": "MN2 crypto hub: blocks, staking, reserves, market"},
    {"id": "staking-monitor", "name": "Staking Monitor", "icon": "🌱", "path": "/staking-monitor", "category": "network", "description": "Pool stats and stake health"},
    {"id": "staking-leaderboard", "name": "Staking Leaderboard", "icon": "📊", "path": "/staking-leaderboard", "category": "network", "description": "MN2 staking ranks"},
    {"id": "hosting", "name": "Masternode Hosting", "icon": "🖥️", "path": "/hosting", "category": "network", "description": "Hosted masternode status and payouts"},
    {"id": "proof-of-reserves", "name": "Proof of Reserves", "icon": "🔐", "path": "/proof-of-reserves", "category": "network", "description": "Treasury transparency"},
    {"id": "market", "name": "P2P Market", "icon": "📈", "path": "/market", "category": "commerce", "description": "Peer MN2 marketplace"},
    {"id": "casino", "name": "Casino", "icon": "🎰", "path": "/casino/", "category": "play", "description": "Casino games and VIP rewards"},
    {"id": "battlegrounds", "name": "Battlegrounds", "icon": "🗺️", "path": "/battlegrounds", "category": "play", "description": "Large-scale battle maps"},
    {"id": "starmap25", "name": "Star Map 25", "icon": "🌌", "path": "/starmap25", "category": "play", "description": "Investigation rewards and invasion events"},
    {"id": "aggregator", "name": "Aggregator", "icon": "📡", "path": "/aggregator", "category": "agents", "description": "75 AI aggregators — catalog and control panel"},
    {"id": "agents", "name": "AI Agents", "icon": "🤖", "path": "/agents", "category": "agents", "description": "Agent marketplace and wallets"},
    {"id": "agents-control", "name": "Agents Control", "icon": "🎛️", "path": "/dashboard/agents_control", "category": "agents", "description": "Agents control board"},
    {"id": "podcast", "name": "Podcast", "icon": "🎙️", "path": "/podcast", "category": "social", "description": "YouTube, Discord, GitHub — crypto rewards"},
    {"id": "social", "name": "Social", "icon": "👥", "path": "/social", "category": "social", "description": "Social hub and engagement"},
    {"id": "profile", "name": "Profile", "icon": "👤", "path": "/profile", "category": "account", "description": "Points, stats, inventory, shop wallet"},
    {"id": "compendium", "name": "Compendium", "icon": "📖", "path": "/compendium/?calm=1", "category": "library", "description": "Rulebooks V1–V16 and compendium points"},
    {"id": "lab", "name": "Lab", "icon": "🔬", "path": "/lab", "category": "create", "description": "Discussion, experiments, research log"},
    {"id": "gallery", "name": "Gallery", "icon": "🖼️", "path": "/gallery", "category": "create", "description": "Media gallery and showcases"},
    {"id": "news", "name": "News", "icon": "📰", "path": "/news", "category": "social", "description": "Site news and updates"},
    {"id": "profit", "name": "Profit Daemon", "icon": "⚡", "path": "/profit/", "category": "commerce", "description": "24/7 profit monitor and rentals"},
    {"id": "business-control", "name": "Business Control", "icon": "🏢", "path": "/business-control", "category": "admin", "description": "Owner trading bots and fleet controls"},
    {"id": "debugger", "name": "Debugger", "icon": "🔧", "path": "/debugger", "category": "tools", "description": "API routes, tests, and diagnostics"},
    {"id": "agent-support", "name": "Agent Support", "icon": "🛠️", "path": "/agent_support", "category": "tools", "description": "Tickets, AI API keys, tools"},
    {"id": "customers", "name": "Customers", "icon": "👥", "path": "/customers", "category": "admin", "description": "Customer directory"},
]


def build_site_features() -> Dict[str, Any]:
    """Site feature matrix for wallet Site Features Hub — lazy-loaded."""
    primary = [f for f in _SITE_FEATURES if f.get("primary")]
    categories = sorted({f.get("category") or "other" for f in _SITE_FEATURES})
    return {
        "success": True,
        "total": len(_SITE_FEATURES),
        "primary_ids": [f["id"] for f in primary],
        "categories": categories,
        "features": _SITE_FEATURES,
    }


def build_rewards_snapshot(user_id: str) -> Dict[str, Any]:
    """Unified points summary for wallet Rewards tab — wraps existing points DB."""
    user_id = (user_id or "").strip() or "default_user"
    guest = user_id in ("", "default_user", "guest")
    out: Dict[str, Any] = {
        "success": True,
        "user_id": user_id,
        "guest": guest,
        "profile_points_url": "/profile?tab=points",
        "quests_url": "/quests",
        "command_center_url": "/command-center",
        "points": {
            "xp_total": 0,
            "level": 1,
            "coins": 0,
            "trophy_points": 0,
            "quest_points": 0,
            "battle_points": 0,
            "mn2_balance": 0,
        },
    }
    if guest:
        out["message"] = "Sign in to track unified points and quest rewards."
        return out
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db and hasattr(unified_points_db, "get_all_points"):
            result = unified_points_db.get_all_points(user_id) or {}
            if result.get("success") and isinstance(result.get("points"), dict):
                pts = result["points"]
                for key in out["points"]:
                    if key in pts:
                        out["points"][key] = pts[key]
                out["points_full"] = pts
    except Exception as exc:
        out["points_error"] = str(exc)
    return out
