"""Live transferable USDT/USDC markets — paper inventing disabled by default.

Customer swap balances settle against venue-backed inventory (Binance spot).
Users can withdraw USDT/USDC to an external address when payout live gates are on.
"""
from __future__ import annotations

import os
from typing import Any, Dict, FrozenSet, Optional

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_binance_withdraw_service import (
    binance_credentials,
    binance_withdraw_live_enabled,
    get_spot_asset_free,
)

_STABLES: FrozenSet[str] = frozenset({"USDT", "USDC"})

_DEFAULT_NETWORKS = {"USDT": "TRC20", "USDC": "ETH"}


def _stable_cfg() -> Dict[str, Any]:
    cfg = ex.load_config()
    row = cfg.get("stable_markets") if isinstance(cfg.get("stable_markets"), dict) else {}
    return row if isinstance(row, dict) else {}


def paper_mode_enabled() -> bool:
    """Paper inventing is OFF unless explicitly re-enabled."""
    env = (os.environ.get("EXCHANGE_STABLE_PAPER") or "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return True
    if env in ("0", "false", "no", "off"):
        return False
    live_env = (os.environ.get("EXCHANGE_STABLE_MARKETS_LIVE") or "").strip().lower()
    if live_env in ("1", "true", "yes", "on"):
        return False
    cfg = _stable_cfg()
    if "paper_mode" in cfg:
        return bool(cfg.get("paper_mode"))
    return False


def withdraw_enabled() -> bool:
    cfg = _stable_cfg()
    if cfg.get("withdraw_enabled") is False:
        return False
    return True


def default_network(asset: str) -> str:
    sym = (asset or "").strip().upper()
    cfg = _stable_cfg()
    nets = cfg.get("default_networks") if isinstance(cfg.get("default_networks"), dict) else {}
    return str(nets.get(sym) or _DEFAULT_NETWORKS.get(sym) or "TRC20").upper()


def min_withdraw(asset: str) -> float:
    sym = (asset or "").strip().upper()
    cfg = _stable_cfg()
    mins = cfg.get("min_withdraw") if isinstance(cfg.get("min_withdraw"), dict) else {}
    try:
        return max(0.0, float(mins.get(sym) or 10.0))
    except (TypeError, ValueError):
        return 10.0


def venue_credentials_ok() -> bool:
    creds = binance_credentials()
    return bool(creds.get("api_key") and creds.get("api_secret"))


def venue_free(asset: str) -> Optional[float]:
    """Binance spot free for asset, or None when unreadable."""
    sym = (asset or "").strip().upper()
    if sym not in _STABLES:
        return None
    if not venue_credentials_ok():
        return None
    try:
        res = get_spot_asset_free(sym, skip_live_gate=True)
    except Exception:
        return None
    if not res.get("success") and not res.get("simulated"):
        return None
    try:
        return round(float(res.get("free") or 0), 8)
    except (TypeError, ValueError):
        return 0.0


def venue_backed_available(ledger_amount: float, asset: str) -> float:
    """Cap ledger liquidity to real venue free when paper mode is off."""
    ledger = max(0.0, float(ledger_amount or 0))
    if paper_mode_enabled():
        return ledger
    sym = (asset or "").strip().upper()
    if sym not in _STABLES:
        return ledger
    free = venue_free(sym)
    if free is None:
        return 0.0
    return round(min(ledger, free), 8)


def sync_sales_pool_stables_from_venue(*, dry_run: bool = False) -> Dict[str, Any]:
    """Align sales-pool USDT/USDC ledger with Binance spot (real wallet inventory)."""
    if paper_mode_enabled():
        return {"success": True, "skipped": True, "reason": "paper_mode"}
    if not venue_credentials_ok():
        return {"success": False, "error": "missing_binance_credentials"}

    try:
        from backend.services.exchange_sales_pool_service import sales_pool_user_id
        pool_uid = sales_pool_user_id()
    except Exception:
        pool_uid = "exchange_sales_pool"

    synced: Dict[str, Any] = {}
    for sym in sorted(_STABLES):
        free = venue_free(sym)
        if free is None:
            synced[sym] = {"error": "venue_unreadable"}
            continue
        before = float(ex._get_balance(pool_uid, sym) or 0)
        if dry_run:
            synced[sym] = {"before": before, "venue_free": free, "would_set": free}
            continue
        delta = round(free - before, 12)
        if abs(delta) > 1e-12:
            ex._adjust_balance(pool_uid, sym, delta)
        synced[sym] = {"before": before, "venue_free": free, "after": free, "delta": delta}

    ex._audit(
        "stable_markets_pool_sync",
        user_id=pool_uid,
        synced=synced,
        paper_mode=False,
    )
    return {
        "success": True,
        "pool_user_id": pool_uid,
        "synced": synced,
        "paper_mode": False,
        "dry_run": bool(dry_run),
    }


def stable_markets_status() -> Dict[str, Any]:
    cfg = _stable_cfg()
    paper = paper_mode_enabled()
    live_withdraw = binance_withdraw_live_enabled()
    venue: Dict[str, Any] = {}
    for sym in sorted(_STABLES):
        venue[sym] = {"free": venue_free(sym)}
    return {
        "success": True,
        "paper_mode": paper,
        "transferable": (not paper) and bool(cfg.get("transferable", True)),
        "withdraw_enabled": withdraw_enabled() and (not paper),
        "withdraw_live": live_withdraw,
        "venue_credentials": venue_credentials_ok(),
        "venue_balances": venue,
        "default_networks": {
            "USDT": default_network("USDT"),
            "USDC": default_network("USDC"),
        },
        "min_withdraw": {
            "USDT": min_withdraw("USDT"),
            "USDC": min_withdraw("USDC"),
        },
        "note": (
            "Paper inventing disabled. USDT/USDC swaps settle against Binance-backed pool "
            "inventory and can be withdrawn to an external address when live payout gates are on."
            if not paper
            else "Paper mode is on (EXCHANGE_STABLE_PAPER=1). Balances are not transferable."
        ),
    }


def withdraw_user_stable(
    user_id: str,
    asset: str,
    amount: float,
    address: str,
    network: Optional[str] = None,
) -> Dict[str, Any]:
    """Send user custodial USDT/USDC via the multi-wallet withdraw rail."""
    sym = (asset or "").strip().upper()
    if sym not in _STABLES:
        return {"success": False, "error": "unsupported_asset", "supported": sorted(_STABLES)}
    from backend.services.exchange_multi_wallet_service import withdraw_user_asset
    return withdraw_user_asset(user_id, sym, amount, address, network)
