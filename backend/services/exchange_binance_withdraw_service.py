"""Signed Binance capital withdraw API (USDT → external address).

Paper by default. Live requires ``EXCHANGE_PAYOUT_BINANCE_LIVE=1`` and
``EXCHANGE_ARBITRAGE_LIVE=1`` plus vault/env API credentials with withdraw scope.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

_log = logging.getLogger(__name__)

_BINANCE_API_BASE = "https://api.binance.com"
_BINANCE_KEY = "binance_api_key"
_BINANCE_SECRET = "binance_api_secret"

_NETWORK_MAP = {
    "TRC20": "TRX",
    "ERC20": "ETH",
    "BEP20": "BSC",
    "TRX": "TRX",
    "ETH": "ETH",
    "BSC": "BSC",
}

_DEFAULT_TRC20_FEE_USDT = 1.5


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def mask_address(addr: str) -> str:
    addr = (addr or "").strip()
    if not addr:
        return ""
    if len(addr) <= 8:
        return "****"
    return f"{addr[:4]}...{addr[-4:]}"


def binance_network_code(network: str) -> str:
    raw = (network or "TRC20").strip().upper()
    return _NETWORK_MAP.get(raw, raw)


def binance_credentials() -> Dict[str, Optional[str]]:
    from backend.services import exchange_secrets_vault_service as vault

    key = vault.get_secret(_BINANCE_KEY) or (os.environ.get("BINANCE_API_KEY") or "").strip() or None
    secret = vault.get_secret(_BINANCE_SECRET) or (os.environ.get("BINANCE_API_SECRET") or "").strip() or None
    return {"api_key": key, "api_secret": secret}


def binance_withdraw_live_enabled() -> bool:
    if os.environ.get("EXCHANGE_PAYOUT_BINANCE_LIVE", "").strip() not in ("1", "true", "yes"):
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


def _sign_binance(params: Dict[str, Any], secret: str) -> str:
    query = urllib.parse.urlencode(params)
    return hmac.new(secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()


def _http_request(method: str, url: str, *, headers: Optional[Dict[str, str]] = None,
                  data: Optional[str] = None, timeout: float = 12.0) -> Dict[str, Any]:
    try:
        import requests
    except Exception:
        return {"success": False, "error": "requests_unavailable"}
    try:
        resp = requests.request(method.upper(), url, headers=headers or {}, data=data, timeout=timeout)
        body: Any
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:500]
        return {
            "success": 200 <= resp.status_code < 300,
            "status_code": resp.status_code,
            "body": body,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _sanitize_log_body(body: Any) -> Any:
    if isinstance(body, dict):
        return {k: v for k, v in body.items() if "secret" not in str(k).lower()}
    if isinstance(body, str):
        return body[:500]
    return body


def _parse_binance_error(res: Dict[str, Any]) -> Tuple[Optional[Any], Optional[str]]:
    body = res.get("body")
    if isinstance(body, dict):
        return body.get("code"), body.get("msg") or body.get("message")
    if isinstance(body, str) and body.strip():
        return None, body.strip()[:500]
    if res.get("error"):
        return None, str(res.get("error"))
    return None, None


def _attach_binance_error(res: Dict[str, Any], *, path: str = "") -> Dict[str, Any]:
    if res.get("success"):
        return res
    code, msg = _parse_binance_error(res)
    http_status = res.get("status_code")
    res["binance_code"] = code
    res["binance_msg"] = msg
    res["http_status"] = http_status
    if not res.get("error"):
        res["error"] = "binance_api_error"
    _log.warning(
        "Binance API error path=%s http_status=%s code=%s msg=%s body=%s",
        path,
        http_status,
        code,
        msg,
        _sanitize_log_body(res.get("body")),
    )
    return res


def _signed_sapi_request(method: str, path: str, params: Optional[Dict[str, Any]] = None,
                         *, dry_run: Optional[bool] = None,
                         skip_live_gate: bool = False) -> Dict[str, Any]:
    params = dict(params or {})
    creds = binance_credentials()
    has_creds = bool(creds.get("api_key") and creds.get("api_secret"))
    live_required = not skip_live_gate and not binance_withdraw_live_enabled()
    use_paper = dry_run if dry_run is not None else (live_required or not has_creds)

    if use_paper:
        return {
            "success": True,
            "mode": "paper",
            "simulated": True,
            "path": path,
            "params": {k: v for k, v in params.items() if k not in ("signature",)},
            "withdraw_id": f"paper-binance-{int(time.time())}",
            "executed_at": _iso(),
        }

    if not skip_live_gate and not binance_withdraw_live_enabled():
        return {"success": False, "error": "live_gated",
                "hint": "Set EXCHANGE_PAYOUT_BINANCE_LIVE=1 and EXCHANGE_ARBITRAGE_LIVE=1"}
    if not has_creds:
        return {"success": False, "error": "missing_credentials",
                "hint": "Store binance_api_key/secret in vault or set BINANCE_API_KEY/SECRET"}

    api_key = creds["api_key"] or ""
    api_secret = creds["api_secret"] or ""
    params.setdefault("timestamp", int(time.time() * 1000))
    params["signature"] = _sign_binance(params, api_secret)
    query = urllib.parse.urlencode(params)
    url = f"{_BINANCE_API_BASE}{path}?{query}"
    headers = {"X-MBX-APIKEY": api_key}
    res = _http_request(method.upper(), url, headers=headers)
    res.setdefault("mode", "live")
    return _attach_binance_error(res, path=path)


def get_capital_config(*, dry_run: Optional[bool] = None,
                       skip_live_gate: bool = False) -> Dict[str, Any]:
    """GET /sapi/v1/capital/config/getall — coin/network withdraw permissions."""
    return _signed_sapi_request(
        "GET", "/sapi/v1/capital/config/getall", {}, dry_run=dry_run, skip_live_gate=skip_live_gate,
    )


def get_spot_usdt_free(*, dry_run: Optional[bool] = None,
                       skip_live_gate: bool = True) -> Dict[str, Any]:
    """GET /api/v3/account — USDT free balance on Binance spot."""
    res = _signed_sapi_request(
        "GET", "/api/v3/account", {}, dry_run=dry_run, skip_live_gate=skip_live_gate,
    )
    if res.get("simulated"):
        res["free"] = 0.0
        return res
    if not res.get("success"):
        return res
    body = res.get("body")
    free = 0.0
    if isinstance(body, dict):
        for bal in body.get("balances") or []:
            if str(bal.get("asset") or "").upper() == "USDT":
                try:
                    free = float(bal.get("free") or 0)
                except (TypeError, ValueError):
                    free = 0.0
                break
    res["free"] = round(free, 8)
    return res


def get_withdraw_address_list(coin: str = "USDT", *, dry_run: Optional[bool] = None,
                              skip_live_gate: bool = True) -> Dict[str, Any]:
    """GET /sapi/v1/capital/withdraw/address/list — whitelisted withdraw addresses."""
    res = _signed_sapi_request(
        "GET",
        "/sapi/v1/capital/withdraw/address/list",
        {"coin": str(coin or "USDT").upper()},
        dry_run=dry_run,
        skip_live_gate=skip_live_gate,
    )
    if res.get("simulated"):
        res["addresses"] = []
        return res
    if not res.get("success"):
        return res
    body = res.get("body")
    rows: List[Dict[str, Any]] = []
    if isinstance(body, list):
        rows = [r for r in body if isinstance(r, dict)]
    res["addresses"] = rows
    return res


def _network_withdraw_fee(network_code: str, capital_config: Optional[Dict[str, Any]] = None) -> float:
    net = binance_network_code(network_code)
    cfg = capital_config
    if cfg is None:
        cfg = get_capital_config(skip_live_gate=True)
    if cfg.get("simulated") or not cfg.get("success"):
        return _DEFAULT_TRC20_FEE_USDT if net == "TRX" else 0.0
    body = cfg.get("body")
    if not isinstance(body, list):
        return _DEFAULT_TRC20_FEE_USDT if net == "TRX" else 0.0
    for coin_row in body:
        if str(coin_row.get("coin") or "").upper() != "USDT":
            continue
        for net_row in coin_row.get("networkList") or []:
            if str(net_row.get("network") or "").upper() != net:
                continue
            try:
                return max(0.0, float(net_row.get("withdrawFee") or 0))
            except (TypeError, ValueError):
                pass
    return _DEFAULT_TRC20_FEE_USDT if net == "TRX" else 0.0


def _address_whitelisted(address: str, network_code: str, rows: List[Dict[str, Any]]) -> bool:
    addr = (address or "").strip()
    net = binance_network_code(network_code)
    if not addr:
        return False
    for row in rows:
        row_addr = str(row.get("address") or "").strip()
        row_net = str(row.get("network") or row.get("coin") or "").upper()
        if row_addr == addr and row_net == net:
            return True
    return False


def preflight_withdraw_usdt(amount: float, address: str, network: str, *,
                            dry_run: Optional[bool] = None,
                            skip_live_gate: bool = True,
                            sales_pool_usdt: Optional[float] = None) -> Dict[str, Any]:
    """Validate Binance spot balance + whitelist before a live USDT withdraw."""
    addr = (address or "").strip()
    net = binance_network_code(network)
    amt = round(max(0.0, float(amount or 0)), 8)
    blockers: List[Dict[str, Any]] = []

    creds = binance_credentials()
    if not (creds.get("api_key") and creds.get("api_secret")):
        return {
            "ready": False,
            "blockers": [{
                "code": "missing_credentials",
                "message": "Store Binance API key/secret in vault or set BINANCE_API_KEY/SECRET.",
            }],
            "amount_usdt": amt,
            "network": net,
            "address_masked": mask_address(addr),
        }

    capital = get_capital_config(dry_run=dry_run, skip_live_gate=skip_live_gate)
    fee = round(_network_withdraw_fee(net, capital), 8)
    required = round(amt + fee, 8)

    spot = get_spot_usdt_free(dry_run=dry_run, skip_live_gate=skip_live_gate)
    spot_free = float(spot.get("free") or 0) if spot.get("success") or spot.get("simulated") else 0.0
    if spot.get("simulated"):
        spot_free = 0.0

    if not spot.get("success") and not spot.get("simulated"):
        blockers.append({
            "code": "spot_balance_unavailable",
            "message": spot.get("binance_msg") or spot.get("error") or "Could not read Binance spot balance.",
            "binance_code": spot.get("binance_code"),
            "http_status": spot.get("http_status"),
        })
    elif spot_free < required:
        msg = (
            f"Binance spot USDT free ({spot_free}) is below required {required} "
            f"(amount {amt} + network fee ~{fee}). Deposit USDT to your Binance spot wallet."
        )
        if sales_pool_usdt is not None and float(sales_pool_usdt) >= amt:
            msg += (
                f" Sales pool ledger holds {round(float(sales_pool_usdt), 8)} USDT internally — "
                "that balance is not on Binance until you deposit real USDT to the API account."
            )
        blockers.append({
            "code": "insufficient_spot_balance",
            "message": msg,
            "spot_usdt_free": spot_free,
            "required_usdt": required,
            "network_fee_usdt": fee,
            "sales_pool_usdt": sales_pool_usdt,
        })

    wl = get_withdraw_address_list("USDT", dry_run=dry_run, skip_live_gate=skip_live_gate)
    wl_rows = wl.get("addresses") or []
    if not wl.get("success") and not wl.get("simulated"):
        blockers.append({
            "code": "whitelist_unavailable",
            "message": wl.get("binance_msg") or wl.get("error") or "Could not read Binance withdraw whitelist.",
            "binance_code": wl.get("binance_code"),
            "http_status": wl.get("http_status"),
        })
    elif not wl.get("simulated") and not _address_whitelisted(addr, net, wl_rows):
        blockers.append({
            "code": "address_not_whitelisted",
            "message": (
                f"Whitelist address {mask_address(addr)} on {net} network "
                f"(TRC20 maps to TRX) in Binance Security → Withdrawal Address Management."
            ),
            "address_masked": mask_address(addr),
            "network": net,
            "whitelisted_count": len(wl_rows),
        })

    return {
        "ready": len(blockers) == 0,
        "blockers": blockers,
        "amount_usdt": amt,
        "network": net,
        "address_masked": mask_address(addr),
        "spot_usdt_free": spot_free,
        "network_fee_usdt": fee,
        "required_spot_usdt": required,
        "sales_pool_usdt": sales_pool_usdt,
    }


def withdraw_usdt(amount: float, address: str, network: str, *,
                  dry_run: Optional[bool] = None,
                  withdraw_order_id: Optional[str] = None) -> Dict[str, Any]:
    """POST /sapi/v1/capital/withdraw/apply for USDT."""
    addr = (address or "").strip()
    if not addr:
        return {"success": False, "error": "missing_address"}
    amt = round(max(0.0, float(amount or 0)), 8)
    if amt <= 0:
        return {"success": False, "error": "invalid_amount"}

    net = binance_network_code(network)
    params: Dict[str, Any] = {
        "coin": "USDT",
        "network": net,
        "address": addr,
        "amount": amt,
    }
    if withdraw_order_id:
        params["withdrawOrderId"] = withdraw_order_id

    res = _signed_sapi_request("POST", "/sapi/v1/capital/withdraw/apply", params, dry_run=dry_run)
    if res.get("simulated"):
        res.setdefault("amount", amt)
        res.setdefault("network", net)
        res.setdefault("address_masked", mask_address(addr))
        return res

    body = res.get("body")
    if res.get("success") and isinstance(body, dict):
        res["withdraw_id"] = body.get("id")
    else:
        res.setdefault("error", "binance_withdraw_failed")
    res.setdefault("amount", amt)
    res.setdefault("network", net)
    res.setdefault("address_masked", mask_address(addr))
    return res
