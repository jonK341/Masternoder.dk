"""
Wallet v2 summary facade — fast overview without deposit RPC.
Delegates to existing MN2 wallet, ledger, chainz, and shop inventory services.
"""
import json
import os
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
    """Lightweight network KPIs from cached chainz overview — best-effort, never raises."""
    out: Dict[str, Any] = {
        "block_height": None,
        "connections": None,
        "mempool_tx": None,
        "mempool_bytes": None,
        "mn2_usd_price": None,
        "pool_apr_percent": None,
        "masternode_count": None,
        "sync_ok": None,
    }
    try:
        from backend.services import mn2_chainz
        overview = mn2_chainz.network_overview() or {}
        out["block_height"] = overview.get("block_height")
        out["connections"] = overview.get("connections")
        out["mempool_tx"] = overview.get("mempool_tx")
        out["mempool_bytes"] = overview.get("mempool_bytes")
        out["mn2_usd_price"] = overview.get("mn2_usd_price")
        out["masternode_count"] = overview.get("masternode_count")
        daemon = overview.get("daemon") if isinstance(overview.get("daemon"), dict) else {}
        if daemon.get("reachable") is not None:
            out["sync_ok"] = bool(daemon.get("reachable"))
    except Exception:
        pass
    try:
        from backend.services import mn2_staking_service as staking
        out["pool_apr_percent"] = staking.dynamic_apr()
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
