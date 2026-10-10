"""
System A+ control boards — API integrations, crypto rewards, and cross-program links.
"""
from __future__ import annotations

from typing import Any, Dict, List


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def get_api_integration_board() -> Dict[str, Any]:
    from backend.services.generator_api_crypto_service import list_external_integrations

    integrations = list_external_integrations()
    live = sum(1 for i in integrations if (i.get("status") or "") == "live")
    return {
        "success": True,
        "board": "api_integrations",
        "integrations": integrations,
        "summary": {
            "total": len(integrations),
            "live": live,
            "beta": sum(1 for i in integrations if i.get("status") == "beta"),
            "planned": sum(1 for i in integrations if i.get("status") == "planned"),
        },
        "external_links": [
            {"label": "API monitor", "href": "/api/", "reward_note": "Ops probe dashboard"},
            {"label": "Generator API tiers", "href": "/api/generator/api/tiers", "reward_note": "Metered white-label"},
            {"label": "Shop payment health", "href": "/api/shop/payment-health", "reward_note": "MN2 + PayPal rails"},
            {"label": "Mobile IAP catalog", "href": "/api/mobile/iap/catalog", "reward_note": "Google Play stub"},
        ],
    }


def get_crypto_rewards_board() -> Dict[str, Any]:
    from backend.services.generator_api_crypto_service import get_crypto_rewards_info

    rewards = get_crypto_rewards_info()
    auction_fee = _safe(
        lambda: __import__(
            "backend.services.tier_b_monetization_service",
            fromlist=["get_auction_fee_info"],
        ).get_auction_fee_info(),
        {},
    )
    return {
        "success": True,
        "board": "crypto_rewards",
        "generator_api": rewards,
        "auction_house": auction_fee,
        "rails": ["paypal", "mn2", "credits", "mn2_onchain", "mobile_iap", "invoice"],
    }


def get_a_plus_board() -> Dict[str, Any]:
    from backend.services.point_system_control_board import get_board_status

    core = get_board_status()
    api_board = get_api_integration_board()
    crypto_board = get_crypto_rewards_board()
    monitor_dims = get_monitor_dimensions_snapshot()
    boards: List[Dict[str, Any]] = [
        {"id": "core_systems", "title": "Core systems", "data": core},
        {"id": "api_integrations", "title": "API integrations", "data": api_board},
        {"id": "crypto_rewards", "title": "Crypto rewards", "data": crypto_board},
        {"id": "api_monitor", "title": "API monitor (6D)", "data": monitor_dims},
    ]
    healthy = bool(core.get("healthy")) and float(monitor_dims.get("availability_pct") or 0) >= 50
    return {
        "success": True,
        "version": "A+",
        "healthy": healthy,
        "boards": boards,
        "board_count": len(boards),
    }


def get_monitor_dimensions_snapshot() -> Dict[str, Any]:
    """Lightweight 6-dimension snapshot for control board (no full probe)."""
    endpoints = [
        "/api/health",
        "/api/mn2/balance",
        "/api/shop/payment-health",
        "/api/generator/api/tiers",
        "/api/shop/auction/listings",
        "/api/mobile/iap/catalog",
    ]
    return {
        "success": True,
        "dimensions": [
            "latency",
            "availability",
            "error_rate",
            "throughput",
            "auth_health",
            "crypto_rails",
        ],
        "dimension_count": 6,
        "probe_endpoints": endpoints,
        "availability_pct": None,
        "note": "Full 6D probe runs at GET /api/monitor/status?dimensions=1",
    }
