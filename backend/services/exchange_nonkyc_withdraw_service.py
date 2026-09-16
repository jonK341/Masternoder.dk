"""Signed NonKYC.io capital withdraw connector (any listed asset -> external address).

NonKYC (and its XeggeX sibling) expose ``POST /createwithdrawal`` with a body of
``{ticker, quantity, address, paymentId?}``. The withdrawal address must already be a
validated address on the NonKYC account. Signing + transport are handled by the shared
``exchange_venue_api_service.venue_api_request`` (``nonkyc_hmac`` auth).

Paper by default. Live requires ``EXCHANGE_PAYOUT_NONKYC_LIVE=1`` and
``EXCHANGE_ARBITRAGE_LIVE=1`` plus vault ``nonkyc_api_key`` / ``nonkyc_api_secret``.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_log = logging.getLogger(__name__)

_DEFAULT_VENUE = "nonkyc"


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def mask_address(addr: str) -> str:
    addr = (addr or "").strip()
    if not addr:
        return ""
    if len(addr) <= 8:
        return "****"
    return f"{addr[:4]}...{addr[-4:]}"


def nonkyc_credentials(venue: str = _DEFAULT_VENUE) -> Dict[str, Optional[str]]:
    from backend.services import exchange_venue_api_service as vapi
    return vapi.venue_credentials(venue)


def has_credentials(venue: str = _DEFAULT_VENUE) -> bool:
    from backend.services import exchange_venue_api_service as vapi
    return vapi.venue_has_credentials(venue)


def nonkyc_withdraw_live_enabled(venue: str = _DEFAULT_VENUE) -> bool:
    """Live withdraw gate: env flag + arb live gate + payout spork ok."""
    flag = f"EXCHANGE_PAYOUT_{venue.upper()}_LIVE"
    if os.environ.get(flag, "").strip() not in ("1", "true", "yes"):
        return False
    try:
        from backend.services.exchange_arbitrage_service import live_enabled
        if not live_enabled():
            return False
    except Exception:
        return False
    try:
        from backend.services import mn2_spork_service as spork
        ok, _reason = spork.payout_live_spork_ok()
        if not ok:
            return False
    except Exception:
        pass
    return True


def get_spot_asset_free(asset: str, venue: str = _DEFAULT_VENUE, *,
                        dry_run: Optional[bool] = None) -> Dict[str, Any]:
    """Free spot balance for one asset on the venue (paper -> 0.0)."""
    from backend.services import exchange_venue_api_service as vapi
    sym = str(asset or "").upper()
    if not has_credentials(venue):
        return {"success": True, "simulated": True, "mode": "paper", "free": 0.0, "asset": sym}
    balances = vapi.parse_spot_balances(venue, dry_run=dry_run)
    return {"success": True, "mode": "live", "free": round(float(balances.get(sym) or 0), 8), "asset": sym}


def preflight_withdraw_asset(coin: str, amount: float, address: str, *,
                             venue: str = _DEFAULT_VENUE,
                             sales_pool_amount: Optional[float] = None,
                             dry_run: Optional[bool] = None) -> Dict[str, Any]:
    """Validate venue credentials + spot balance before a live NonKYC withdraw."""
    coin_u = str(coin or "").upper()
    addr = (address or "").strip()
    amt = round(max(0.0, float(amount or 0)), 8)
    blockers = []

    if not has_credentials(venue):
        blockers.append({
            "code": "missing_credentials",
            "message": f"Store {venue}_api_key / {venue}_api_secret in the vault.",
        })
        return {"ready": False, "coin": coin_u, "venue": venue, "blockers": blockers,
                "amount": amt, "address_masked": mask_address(addr)}

    if not addr:
        blockers.append({"code": "missing_address", "message": "No withdraw address configured."})

    spot = get_spot_asset_free(coin_u, venue, dry_run=dry_run)
    spot_free = float(spot.get("free") or 0) if not spot.get("simulated") else 0.0
    if spot_free < amt:
        msg = (
            f"{venue} spot {coin_u} free ({spot_free}) is below {amt}. "
            f"Deposit {coin_u} to your {venue} account before withdraw."
        )
        if sales_pool_amount is not None and float(sales_pool_amount) >= amt:
            msg += (
                f" Sales pool ledger holds {round(float(sales_pool_amount), 8)} {coin_u} internally — "
                f"that is not on {venue} until real coins are deposited."
            )
        blockers.append({
            "code": "insufficient_spot_balance",
            "message": msg,
            "spot_free": spot_free,
            "required": amt,
            "sales_pool_amount": sales_pool_amount,
        })

    return {
        "ready": len(blockers) == 0,
        "coin": coin_u,
        "venue": venue,
        "blockers": blockers,
        "amount": amt,
        "address_masked": mask_address(addr),
        "spot_free": spot_free,
        "sales_pool_amount": sales_pool_amount,
    }


def withdraw_asset(coin: str, amount: float, address: str, *,
                   venue: str = _DEFAULT_VENUE,
                   ticker: Optional[str] = None,
                   payment_id: Optional[str] = None,
                   dry_run: Optional[bool] = None) -> Dict[str, Any]:
    """POST /createwithdrawal on NonKYC/XeggeX for any listed asset."""
    from backend.services import exchange_venue_api_service as vapi

    coin_u = str(coin or "").upper()
    if not coin_u:
        return {"success": False, "error": "missing_coin"}
    addr = (address or "").strip()
    if not addr:
        return {"success": False, "error": "missing_address"}
    amt = round(max(0.0, float(amount or 0)), 8)
    if amt <= 0:
        return {"success": False, "error": "invalid_amount"}

    # Paper unless the venue live gate is on (independent of the shared arb gate).
    use_paper = dry_run if dry_run is not None else (not nonkyc_withdraw_live_enabled(venue))
    if not use_paper and not has_credentials(venue):
        return {"success": False, "error": "missing_credentials",
                "hint": f"Store {venue}_api_key / {venue}_api_secret in the vault"}

    params: Dict[str, Any] = {
        "ticker": str(ticker or coin_u),
        "quantity": str(amt),
        "address": addr,
    }
    if payment_id:
        params["paymentId"] = str(payment_id)

    res = vapi.venue_api_request(venue, "withdraw", params, dry_run=use_paper)
    if res.get("simulated"):
        return {
            "success": True,
            "mode": "paper",
            "simulated": True,
            "venue": venue,
            "coin": coin_u,
            "amount": amt,
            "address_masked": mask_address(addr),
            "withdraw_id": f"paper-{venue}-{int(time.time())}",
            "executed_at": _iso(),
        }

    body = res.get("body")
    out: Dict[str, Any] = {
        "success": bool(res.get("success")),
        "mode": "live",
        "venue": venue,
        "coin": coin_u,
        "amount": amt,
        "address_masked": mask_address(addr),
    }
    if isinstance(body, dict):
        out["withdraw_id"] = body.get("id") or body.get("_id") or body.get("withdrawalId")
    if not out["success"]:
        out["error"] = vapi.extract_order_error(res) or "nonkyc_withdraw_failed"
        out["http_status"] = res.get("status_code")
        _log.warning("NonKYC withdraw failed venue=%s coin=%s status=%s err=%s",
                     venue, coin_u, res.get("status_code"), out.get("error"))
    return out
