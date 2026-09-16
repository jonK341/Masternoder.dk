"""
Wallet v2 integration hub — single BFF payload linking exchange, encoder, shop, news,
podcast, network chat, and camgirls with snapshot counts.
"""
import json
import os
from typing import Any, Dict

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _count_json_list(path: str, key: str) -> int:
    if not os.path.isfile(path):
        return 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data.get(key) if isinstance(data, dict) else []
        return len(items) if isinstance(items, list) else 0
    except Exception:
        return 0


def _encoder_job_count(user_id: str) -> int:
    try:
        from backend.services.generator_db_service import list_jobs
        jobs = list_jobs(user_id=user_id, limit=200)
        if jobs is not None:
            return len(jobs)
    except Exception:
        pass
    try:
        from backend.services.generator_db_service import get_job_statistics
        stats = get_job_statistics(user_id=user_id, days=30)
        if stats:
            return int(stats.get("total_jobs") or 0)
    except Exception:
        pass
    return 0


def build_integration_hub(user_id: str) -> Dict[str, Any]:
    user_id = (user_id or "").strip() or "default_user"

    exchange_assets = 0
    exchange_mn2 = None
    try:
        from backend.services.crypto_exchange_service import get_wallet
        wallet = get_wallet(user_id) or {}
        assets = wallet.get("assets") if isinstance(wallet.get("assets"), dict) else {}
        exchange_assets = len([k for k, v in assets.items() if float(v or 0) > 0])
        exchange_mn2 = assets.get("MN2")
    except Exception:
        pass

    shop_trophy_count = 0
    try:
        from backend.services.wallet_v2_service import _trophy_counts
        counts = _trophy_counts(user_id)
        shop_trophy_count = int(counts.get("shop_items") or counts.get("total") or 0)
    except Exception:
        shop_trophy_count = _count_json_list(os.path.join(_BASE, "data", "shop_catalog.json"), "items")

    news_count = _count_json_list(os.path.join(_BASE, "data", "platform_news.json"), "items")
    podcast_episodes = _count_json_list(os.path.join(_BASE, "data", "podcast_episodes.json"), "episodes")
    podcast_channels = _count_json_list(os.path.join(_BASE, "data", "podcast_channels.json"), "channels")

    chat_online = 0
    chat_messages = 0
    try:
        from backend.services.network_chat_service import get_status as chat_status
        cs = chat_status(user_id, limit=1)
        chat_online = int(cs.get("online_count") or 0)
        chat_messages = int(cs.get("message_count") or 0)
    except Exception:
        pass

    camgirls_total = 0
    camgirls_online = 0
    camgirls_upgrades = 0
    camgirls_ai_features = 0
    try:
        from backend.services.camgirls_wallet_service import list_performers, load_upgrades_catalog
        from backend.services.camgirls_ai_features_service import load_catalog
        perf = list_performers()
        camgirls_total = int(perf.get("total") or 0)
        camgirls_online = int(perf.get("online_count") or 0)
        camgirls_upgrades = int((load_upgrades_catalog().get("total") or 0))
        camgirls_ai_features = int((load_catalog().get("total") or 0))
    except Exception:
        pass

    encoder_jobs = _encoder_job_count(user_id)

    return {
        "success": True,
        "user_id": user_id,
        "units": {
            "WR-INT-EXCH": {
                "id": "exchange",
                "label": "Exchange",
                "path": "/exchange",
                "api": "/api/exchange/wallet",
                "wallet_tab": "exchange",
                "asset_count": exchange_assets,
                "mn2_balance": exchange_mn2,
            },
            "WR-INT-ENC": {
                "id": "encoder",
                "label": "Encoder",
                "path": "/generator",
                "api": "/api/generator/history",
                "wallet_tab": "encoder",
                "recent_jobs_count": encoder_jobs,
            },
            "WR-INT-SHOP": {
                "id": "shop",
                "label": "Shop",
                "path": "/shop?tab=trophies",
                "api": "/api/shop/catalog",
                "wallet_tab": "shop",
                "trophy_skus": shop_trophy_count,
            },
            "WR-INT-NEWS": {
                "id": "news",
                "label": "News",
                "path": "/news",
                "api": "/api/news/platform",
                "wallet_tab": "news",
                "item_count": news_count,
            },
            "WR-INT-POD": {
                "id": "podcast",
                "label": "Podcast",
                "path": "/podcast",
                "api": "/api/podcast/episodes",
                "wallet_tab": "podcast",
                "episode_count": podcast_episodes,
                "channel_count": podcast_channels,
            },
            "WR-INT-CHAT": {
                "id": "network-chat",
                "label": "Network Chat",
                "path": "/wallets?tab=network-chat",
                "api": "/api/wallet/v2/network-chat/status",
                "wallet_tab": "network-chat",
                "online_count": chat_online,
                "message_count": chat_messages,
            },
            "WR-INT-CAM": {
                "id": "camgirls",
                "label": "Camgirls",
                "path": "/camgirls",
                "api": "/api/wallet/v2/camgirls/catalog",
                "wallet_tab": "camgirls",
                "performer_count": camgirls_total,
                "online_count": camgirls_online,
            },
            "WR-INT-CAM-UPG": {
                "id": "camgirls-upgrades",
                "label": "Camgirl Upgrades",
                "path": "/wallets?tab=camgirls&panel=upgrades",
                "api": "/api/wallet/v2/camgirls/upgrades",
                "wallet_tab": "camgirls",
                "upgrade_count": camgirls_upgrades,
            },
            "WR-CAM-AI-100": {
                "id": "camgirls-ai-features",
                "label": "Camgirl AI Features",
                "path": "/wallets?tab=camgirls&panel=ai-features",
                "api": "/api/wallet/v2/camgirls/ai-features",
                "wallet_tab": "camgirls",
                "feature_count": camgirls_ai_features,
            },
        },
        "tab_groups": {
            "core": ["overview", "portal", "send", "receive", "activity", "settings"],
            "earn": ["rewards", "earn", "casino", "upgrades"],
            "media": ["encoder", "news", "podcast"],
            "social": ["network-chat", "exchange", "shop"],
            "camgirls": ["camgirls"],
        },
    }
