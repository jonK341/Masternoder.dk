"""
MN2 services catalog — single registry for wallet, staking, masternode hosting, on-ramp,
P2P, trader market, explorer, and ops components.

GET /api/mn2/services returns this catalog with live status probes (best-effort, cached).
"""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional

_LOCK = threading.Lock()
_CACHE: Dict[str, Any] = {}
_CACHE_TTL = 30


def _cached(key: str, ttl: int, builder: Callable[[], Any]) -> Any:
    now = time.time()
    with _LOCK:
        ent = _CACHE.get(key)
        if ent and (now - ent.get("ts", 0)) < ttl:
            return ent.get("value")
    value = builder()
    with _LOCK:
        _CACHE[key] = {"value": value, "ts": now}
    return value


def _status_rank(status: str) -> int:
    order = {"healthy": 0, "active": 0, "enabled": 0, "warn": 1, "degraded": 2, "inactive": 2, "disabled": 3, "unknown": 4}
    return order.get(str(status or "").lower(), 4)


def _summarize(services: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for s in services:
        st = str(s.get("status") or "unknown").lower()
        counts[st] = counts.get(st, 0) + 1
    overall = "healthy"
    for st in ("degraded", "warn", "inactive", "disabled"):
        if counts.get(st):
            overall = st if _status_rank(st) > _status_rank(overall) else overall
    return {
        "total": len(services),
        "healthy": counts.get("healthy", 0) + counts.get("active", 0) + counts.get("enabled", 0),
        "warn": counts.get("warn", 0),
        "degraded": counts.get("degraded", 0),
        "disabled": counts.get("disabled", 0),
        "overall": overall,
    }


def _probe_wallet() -> Dict[str, Any]:
    try:
        from backend.services.mn2_rpc_client import health_check
        h = health_check()
        st = h.get("status") or "unknown"
        return {"status": "healthy" if st == "healthy" else st, "block_height": h.get("block_height")}
    except Exception as exc:
        return {"status": "degraded", "error": str(exc)}


def _probe_staking() -> Dict[str, Any]:
    try:
        from backend.services.mn2_staking_service import get_config
        cfg = get_config()
        if not cfg.get("enabled"):
            return {"status": "disabled", "enabled": False}
        from backend.services.mn2_rpc_client import staking_health
        sh = staking_health() or {}
        active = sh.get("staking_active") is True or sh.get("status") == "active"
        return {
            "status": "active" if active else "inactive",
            "enabled": True,
            "mnsync": sh.get("mnsync"),
            "pool_apr": None,
        }
    except Exception as exc:
        return {"status": "unknown", "error": str(exc)}


def _probe_onramp() -> Dict[str, Any]:
    try:
        from backend.services import mn2_onramp_service as onramp
        cfg = onramp.get_config()
        return {"status": "enabled" if cfg.get("enabled") else "disabled", "model": cfg.get("model")}
    except Exception as exc:
        return {"status": "unknown", "error": str(exc)}


def _probe_p2p() -> Dict[str, Any]:
    try:
        from backend.services import mn2_p2p_service as p2p
        cfg = p2p.get_config()
        return {"status": "enabled" if cfg.get("enabled") else "disabled"}
    except Exception as exc:
        return {"status": "unknown", "error": str(exc)}


def _probe_trader_market() -> Dict[str, Any]:
    try:
        from backend.services.mn2_staking_service import get_config
        cfg = get_config()
        ta = cfg.get("trader_agents") if isinstance(cfg.get("trader_agents"), dict) else {}
        market = ta.get("market") if isinstance(ta.get("market"), dict) else {}
        on = bool(ta.get("enabled")) and bool(market.get("enabled", True))
        return {"status": "enabled" if on else "disabled"}
    except Exception as exc:
        return {"status": "unknown", "error": str(exc)}


def _probe_explorer() -> Dict[str, Any]:
    try:
        from backend.services.mn2_explorer_urls import explorer_base_url, explorer_kind
        base = explorer_base_url()
        kind = explorer_kind()
        return {
            "status": "healthy" if base else "warn",
            "explorer_base_url": base,
            "explorer_kind": kind,
        }
    except Exception as exc:
        return {"status": "unknown", "error": str(exc)}


def _probe_deposit_scanner() -> Dict[str, Any]:
    import os
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log = os.path.join(base, "logs", "mn2_deposit_scanner.jsonl")
    if not os.path.isfile(log):
        return {"status": "unknown", "detail": "no scan log yet"}
    try:
        with open(log, "r", encoding="utf-8") as f:
            lines = [ln.strip() for ln in f.readlines() if ln.strip()]
        if not lines:
            return {"status": "unknown"}
        import json
        last = json.loads(lines[-1])
        return {"status": "healthy", "last_run": last.get("end") or last.get("ts")}
    except Exception as exc:
        return {"status": "unknown", "error": str(exc)}


def _probe_masternode_hosting() -> Dict[str, Any]:
    try:
        from backend.services import mn2_masternode_service as mn
        return mn.probe_health()
    except Exception as exc:
        return {"status": "unknown", "error": str(exc)}


def _probe_proof_of_reserves() -> Dict[str, Any]:
    try:
        from backend.services.mn2_proof_of_reserves_service import proof_of_reserves
        snap = proof_of_reserves()
        ratio = snap.get("coverage_ratio") if isinstance(snap, dict) else None
        if ratio is None:
            return {"status": "unknown"}
        ok = float(ratio) >= 1.0
        return {"status": "healthy" if ok else "warn", "coverage_ratio": ratio}
    except Exception as exc:
        return {"status": "unknown", "error": str(exc)}


# Static catalog — status filled by probes at runtime.
_SERVICE_DEFS: List[Dict[str, Any]] = [
    {
        "id": "wallet_downloads",
        "name": "Desktop Wallets",
        "category": "core",
        "description": "Official MN2 daemon and Qt wallet downloads with checksums.",
        "api": ["/api/mn2/releases"],
        "page_url": "/wallets",
        "probe": lambda: {"status": "healthy"},
    },
    {
        "id": "wallet",
        "name": "MN2 Wallet",
        "category": "core",
        "description": "Custodial in-app MN2 balance, deposits, withdrawals, ledger.",
        "api": ["/api/mn2/balance", "/api/mn2/deposit-address", "/api/mn2/transactions", "/api/mn2/wallet-hub", "/api/mn2/recent-transactions"],
        "page_url": "/profile#mn2-wallet",
        "probe": _probe_wallet,
    },
    {
        "id": "staking",
        "name": "Staking Pool",
        "category": "earn",
        "description": "Custodial PoS pool — daemon mints; users stake in-app with browser rig weighting.",
        "api": ["/api/mn2/staking/status", "/api/mn2/staking/monitor"],
        "page_url": "/explorer?tab=staking",
        "probe": _probe_staking,
    },
    {
        "id": "masternode_hosting",
        "name": "Masternode Hosting",
        "category": "earn",
        "description": "Platform-hosted MN2 masternodes on shared infrastructure (10k MN2 collateral each).",
        "api": ["/api/mn2/masternode/service", "/api/mn2/masternodes"],
        "page_url": "/explorer?tab=masternodes",
        "probe": _probe_masternode_hosting,
    },
    {
        "id": "onramp",
        "name": "PayPal On-Ramp",
        "category": "fiat",
        "description": "USD → MN2 via PayPal with hold/clearance windows.",
        "api": ["/api/mn2/onramp/config", "/api/mn2/onramp/quote"],
        "page_url": "/profile#mn2-wallet",
        "probe": _probe_onramp,
    },
    {
        "id": "p2p",
        "name": "P2P Marketplace",
        "category": "fiat",
        "description": "Escrow MN2 listings with PayPal settlement.",
        "api": ["/api/mn2/p2p/config"],
        "page_url": "/explorer?tab=market",
        "probe": _probe_p2p,
    },
    {
        "id": "trader_market",
        "name": "Agent Trader Market",
        "category": "earn",
        "description": "Internal MN2 order book driven by agent traders.",
        "api": ["/api/market/ticker", "/api/market/trades"],
        "page_url": "/explorer?tab=market",
        "probe": _probe_trader_market,
    },
    {
        "id": "explorer",
        "name": "Network Explorer",
        "category": "data",
        "description": "Live stats, blocks, masternodes; links to self-hosted eiquidus + Chainz.",
        "api": ["/api/mn2/network-overview", "/api/mn2/recent-blocks", "/api/mn2/network-dashboard"],
        "page_url": "/explorer",
        "probe": _probe_explorer,
    },
    {
        "id": "deposit_scanner",
        "name": "Deposit Scanner",
        "category": "ops",
        "description": "Cron-driven on-chain deposit detection → user credits.",
        "api": ["/api/mn2/health"],
        "page_url": None,
        "probe": _probe_deposit_scanner,
    },
    {
        "id": "proof_of_reserves",
        "name": "Proof of Reserves",
        "category": "trust",
        "description": "Custodial assets vs user liabilities coverage report.",
        "api": ["/api/mn2/staking/proof-of-reserves"],
        "page_url": "/explorer?tab=reserves",
        "probe": _probe_proof_of_reserves,
    },
]


def get_services_catalog(use_cache: bool = True) -> Dict[str, Any]:
    """Full MN2 services registry with live status."""

    def build() -> Dict[str, Any]:
        services: List[Dict[str, Any]] = []
        for defn in _SERVICE_DEFS:
            probe_fn = defn.get("probe")
            probe: Dict[str, Any] = {}
            if callable(probe_fn):
                try:
                    probe = probe_fn() or {}
                except Exception as exc:
                    probe = {"status": "unknown", "error": str(exc)}
            services.append({
                "id": defn["id"],
                "name": defn["name"],
                "category": defn.get("category"),
                "description": defn.get("description"),
                "api": defn.get("api"),
                "page_url": defn.get("page_url"),
                "status": probe.get("status") or "unknown",
                "probe": probe,
            })
        summary = _summarize(services)
        return {"success": True, "summary": summary, "services": services}

    if use_cache:
        return _cached("catalog", _CACHE_TTL, build)
    return build()


def get_service_by_id(service_id: str) -> Optional[Dict[str, Any]]:
    cat = get_services_catalog(use_cache=True)
    for s in cat.get("services") or []:
        if s.get("id") == service_id:
            return s
    return None
