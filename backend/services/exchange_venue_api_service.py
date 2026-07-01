"""Signed private REST clients for major crypto exchange venues.

Public market data lives in ``external_exchange_connector_service``; this module handles
account reads and market-order placement when live gates pass. Paper mode (default) returns
deterministic simulated responses so the AI trading loop can exercise the full API surface
without moving real funds.

Live gate: ``EXCHANGE_ARBITRAGE_LIVE=1`` + per-venue ``{venue_id}_api_key`` / ``_api_secret``
(and ``_api_passphrase`` for OKX/KuCoin) in the encrypted vault.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.services import crypto_exchange_service as ex
from backend.services import external_exchange_connector_service as conn
from backend.services.exchange_http_util import force_ipv4_outbound_if_configured

_API_CFG_PATH = ex._BASE + "/data/exchange_venue_api_config.json"


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_api_config() -> Dict[str, Any]:
    cfg = ex._read_json(_API_CFG_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def live_allowed() -> bool:
    from backend.services.exchange_arbitrage_service import live_enabled
    return live_enabled()


def _venue_api_cfg(venue_id: str) -> Optional[Dict[str, Any]]:
    return (load_api_config().get("venues") or {}).get(venue_id)


def _secret_names(venue_id: str) -> Tuple[str, str, str]:
    cfg = load_api_config()
    key_pat = str(cfg.get("secret_key_pattern") or "{venue_id}_api_key")
    sec_pat = str(cfg.get("secret_secret_pattern") or "{venue_id}_api_secret")
    pass_pat = str(cfg.get("secret_passphrase_pattern") or "{venue_id}_api_passphrase")
    return (
        key_pat.format(venue_id=venue_id),
        sec_pat.format(venue_id=venue_id),
        pass_pat.format(venue_id=venue_id),
    )


def venue_has_credentials(venue_id: str) -> bool:
    from backend.services import exchange_secrets_vault_service as vault
    key_name, sec_name, _ = _secret_names(venue_id)
    return bool(vault.get_secret(key_name) and vault.get_secret(sec_name))


def venue_credentials(venue_id: str) -> Dict[str, Optional[str]]:
    from backend.services import exchange_secrets_vault_service as vault
    key_name, sec_name, pass_name = _secret_names(venue_id)
    return {
        "api_key": vault.get_secret(key_name),
        "api_secret": vault.get_secret(sec_name),
        "passphrase": vault.get_secret(pass_name),
    }


def _http_request(method: str, url: str, *, headers: Optional[Dict[str, str]] = None,
                  data: Optional[str] = None, timeout: float = 8.0) -> Dict[str, Any]:
    try:
        import requests
    except Exception:
        return {"success": False, "error": "requests_unavailable"}
    force_ipv4_outbound_if_configured()
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


def _sign_binance(params: Dict[str, Any], secret: str) -> str:
    query = urllib.parse.urlencode(params)
    return hmac.new(secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()


def _sign_okx(timestamp: str, method: str, path: str, body: str, secret: str) -> str:
    msg = f"{timestamp}{method.upper()}{path}{body}"
    return hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest().hex()


def _sign_bybit(timestamp: str, api_key: str, recv_window: str, payload: str, secret: str) -> str:
    msg = f"{timestamp}{api_key}{recv_window}{payload}"
    return hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()


def _sign_nonkyc(api_key: str, request_url: str, body: str, nonce: str, secret: str) -> str:
    payload = f"{api_key}{request_url}{body}{nonce}"
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _sign_kraken(path: str, postdata: str, secret: str) -> str:
    import base64
    sha = hashlib.sha256(postdata.encode("utf-8")).digest()
    mac = hmac.new(base64.b64decode(secret), path.encode("utf-8") + sha, hashlib.sha512)
    return base64.b64encode(mac.digest()).decode("utf-8")


def _simulate_response(venue_id: str, endpoint_key: str, params: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "success": True,
        "mode": "paper",
        "simulated": True,
        "venue_id": venue_id,
        "endpoint": endpoint_key,
        "params": params,
        "order_id": f"paper-{venue_id}-{int(time.time())}",
        "executed_at": _iso(),
    }


def venue_api_request(
    venue_id: str,
    endpoint_key: str,
    params: Optional[Dict[str, Any]] = None,
    *,
    dry_run: Optional[bool] = None,
) -> Dict[str, Any]:
    """Signed private API call for a venue endpoint (account, order_market, …)."""
    params = dict(params or {})
    vcfg = _venue_api_cfg(venue_id)
    if not vcfg:
        return {"success": False, "error": "unknown_venue", "venue_id": venue_id}

    endpoint = (vcfg.get("endpoints") or {}).get(endpoint_key)
    if not endpoint:
        return {"success": False, "error": "unknown_endpoint", "endpoint": endpoint_key}

    creds = venue_credentials(venue_id)
    has_creds = bool(creds.get("api_key") and creds.get("api_secret"))
    use_paper = dry_run if dry_run is not None else (not live_allowed() or not has_creds)

    if use_paper or not vcfg.get("live_supported", True):
        return _simulate_response(venue_id, endpoint_key, params)

    if not live_allowed():
        return {"success": False, "error": "live_gated", "hint": "Set EXCHANGE_ARBITRAGE_LIVE=1"}

    auth = str(vcfg.get("auth") or "")
    api_base = str(vcfg.get("api_base") or "").rstrip("/")
    method = str(endpoint.get("method") or "GET").upper()
    path = str(endpoint.get("path") or "")

    api_key = creds["api_key"] or ""
    api_secret = creds["api_secret"] or ""
    passphrase = creds.get("passphrase") or ""

    timeout = float((conn.load_connectors_config().get("request_timeout_sec") or 8))

    if auth == "binance_hmac":
        from backend.services.exchange_binance_time_service import binance_timestamp_ms, recv_window_ms
        params.setdefault("timestamp", binance_timestamp_ms())
        params.setdefault("recvWindow", recv_window_ms())
        params["signature"] = _sign_binance(params, api_secret)
        query = urllib.parse.urlencode(params)
        url = f"{api_base}{path}?{query}"
        headers = {"X-MBX-APIKEY": api_key}
        if method == "POST":
            return _http_request("POST", url, headers=headers, timeout=timeout)
        return _http_request("GET", url, headers=headers, timeout=timeout)

    if auth == "okx_hmac":
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        body = json.dumps(params) if method != "GET" else ""
        sign_path = path + ("?" + urllib.parse.urlencode(params) if method == "GET" and params else "")
        sig = _sign_okx(ts, method, sign_path, body, api_secret)
        headers = {
            "OK-ACCESS-KEY": api_key,
            "OK-ACCESS-SIGN": sig,
            "OK-ACCESS-TIMESTAMP": ts,
            "OK-ACCESS-PASSPHRASE": passphrase,
            "Content-Type": "application/json",
        }
        url = f"{api_base}{sign_path}" if method == "GET" else f"{api_base}{path}"
        return _http_request(method, url, headers=headers, data=body or None, timeout=timeout)

    if auth == "bybit_hmac":
        ts = str(int(time.time() * 1000))
        recv = "5000"
        body = json.dumps(params)
        sig = _sign_bybit(ts, api_key, recv, body, api_secret)
        headers = {
            "X-BAPI-API-KEY": api_key,
            "X-BAPI-SIGN": sig,
            "X-BAPI-TIMESTAMP": ts,
            "X-BAPI-RECV-WINDOW": recv,
            "Content-Type": "application/json",
        }
        return _http_request(method, f"{api_base}{path}", headers=headers, data=body, timeout=timeout)

    if auth == "nonkyc_hmac":
        nonce = str(int(time.time() * 1000))
        if method == "GET":
            query = ("?" + urllib.parse.urlencode(params)) if params else ""
            path_with_query = path + query
            full_url = f"{api_base}{path_with_query}"
            sig = _sign_nonkyc(api_key, full_url, "", nonce, api_secret)
            headers = {
                "X-API-KEY": api_key,
                "X-API-NONCE": nonce,
                "X-API-SIGN": sig,
                "Content-Type": "application/json",
            }
            return _http_request("GET", full_url, headers=headers, timeout=timeout)
        body = json.dumps(params, separators=(",", ":"))
        full_url = f"{api_base}{path}"
        sig = _sign_nonkyc(api_key, full_url, body, nonce, api_secret)
        headers = {
            "X-API-KEY": api_key,
            "X-API-NONCE": nonce,
            "X-API-SIGN": sig,
            "Content-Type": "application/json",
        }
        return _http_request("POST", full_url, headers=headers, data=body, timeout=timeout)

    if auth == "kraken_hmac":
        nonce = str(int(time.time() * 1000))
        postdata = urllib.parse.urlencode({**params, "nonce": nonce})
        sig_path = path
        signature = _sign_kraken(sig_path, postdata, api_secret)
        headers = {"API-Key": api_key, "API-Sign": signature}
        return _http_request("POST", f"{api_base}{path}", headers=headers, data=postdata, timeout=timeout)

    if auth == "kucoin_hmac":
        ts = str(int(time.time() * 1000))
        body = json.dumps(params)
        str_to_sign = ts + method + path + body
        sig = base64_encode(hmac.new(api_secret.encode(), str_to_sign.encode(), hashlib.sha256).digest())
        passphrase_sig = base64_encode(
            hmac.new(api_secret.encode(), passphrase.encode(), hashlib.sha256).digest()
        ) if passphrase else ""
        headers = {
            "KC-API-KEY": api_key,
            "KC-API-SIGN": sig,
            "KC-API-TIMESTAMP": ts,
            "KC-API-PASSPHRASE": passphrase_sig or passphrase,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json",
        }
        return _http_request(method, f"{api_base}{path}", headers=headers, data=body, timeout=timeout)

    return {"success": False, "error": "auth_stub", "auth": auth, "venue_id": venue_id}


def base64_encode(raw: bytes) -> str:
    import base64
    return base64.b64encode(raw).decode("utf-8")


def place_market_order(
    venue_id: str,
    symbol: str,
    side: str,
    quantity: float,
    *,
    dry_run: Optional[bool] = None,
) -> Dict[str, Any]:
    """Place a spot market order on a venue (paper-simulated unless live + credentialed)."""
    vmap = conn._venue_map()
    venue = vmap.get(venue_id) or {}
    pair = conn.build_pair(venue, symbol.upper())
    side_u = str(side or "buy").upper()
    qty = round(max(0.0, float(quantity or 0)), 8)
    if qty <= 0:
        return {"success": False, "error": "invalid_quantity"}

    params: Dict[str, Any]
    if venue_id == "binance":
        params = {"symbol": pair, "side": side_u, "type": "MARKET", "quantity": qty}
    elif venue_id == "okx":
        params = {"instId": pair, "tdMode": "cash", "side": side_u.lower(), "ordType": "market",
                  "sz": str(qty), "tgtCcy": "base_ccy"}
    elif venue_id == "bybit":
        params = {"category": "spot", "symbol": pair, "side": side_u.capitalize(), "orderType": "Market",
                  "qty": str(qty)}
    elif venue_id == "nonkyc":
        params = {
            "symbol": pair,
            "side": side_u.lower(),
            "type": "market",
            "quantity": str(qty),
            "strictValidate": False,
        }
    elif venue_id == "xeggex":
        params = {
            "symbol": pair,
            "side": side_u.lower(),
            "type": "market",
            "quantity": str(qty),
            "price": "0",
            "strictValidate": False,
        }
    elif venue_id == "kraken":
        params = {"pair": pair, "type": side_u.lower(), "ordertype": "market", "volume": str(qty)}
    elif venue_id == "kucoin":
        params = {"clientOid": f"mn2-{int(time.time())}", "side": side_u.lower(), "symbol": pair,
                  "type": "market", "size": str(qty)}
    else:
        params = {"symbol": pair, "side": side_u, "quantity": qty, "type": "market"}

    res = venue_api_request(venue_id, "order_market", params, dry_run=dry_run)
    res.setdefault("symbol", symbol.upper())
    res.setdefault("side", side_u.lower())
    res.setdefault("quantity", qty)
    res.setdefault("pair", pair)
    return res


def get_account_balance(venue_id: str, asset: str = "", *, dry_run: Optional[bool] = None) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    if venue_id == "bybit":
        params = {"accountType": "UNIFIED"}
    elif venue_id == "okx" and asset:
        params = {"ccy": asset.upper()}
    res = venue_api_request(venue_id, "account", params, dry_run=dry_run)
    res.setdefault("venue_id", venue_id)
    return res


def venue_quote_asset(venue_id: str) -> str:
    return conn.venue_quote(venue_id)


def parse_spot_balances(venue_id: str, *, dry_run: Optional[bool] = None) -> Dict[str, float]:
    """Return asset -> free spot balance for a credentialed venue."""
    if not venue_has_credentials(venue_id):
        return {}
    res = get_account_balance(venue_id, dry_run=dry_run)
    if not res.get("success"):
        return {}
    body = res.get("body")
    out: Dict[str, float] = {}
    if venue_id == "binance" and isinstance(body, dict):
        for row in body.get("balances") or []:
            if not isinstance(row, dict):
                continue
            sym = str(row.get("asset") or "").upper()
            try:
                free = float(row.get("free") or 0)
            except (TypeError, ValueError):
                free = 0.0
            if sym and free > 0:
                out[sym] = free
        return out
    items: List[Any] = []
    if isinstance(body, list):
        items = body
    elif isinstance(body, dict):
        for key in ("balances", "data", "result", "assets"):
            if isinstance(body.get(key), list):
                items = body[key]
                break
    for row in items:
        if not isinstance(row, dict):
            continue
        sym = str(row.get("symbol") or row.get("asset") or row.get("currency") or "").upper()
        try:
            free = float(row.get("available") or row.get("free") or row.get("balance") or 0)
        except (TypeError, ValueError):
            free = 0.0
        if sym and free > 0:
            out[sym] = free
    return out


def can_fund_arb_leg(
    venue_id: str,
    symbol: str,
    side: str,
    *,
    qty: float,
    notional_usd: float,
    buffer_pct: float = 0.03,
) -> Dict[str, Any]:
    """Check live spot balance for one arb leg (buy needs quote, sell needs base coin)."""
    if venue_id == "internal":
        return {"ok": True, "venue_id": venue_id, "side": side}
    side_l = str(side or "").lower()
    bals = parse_spot_balances(venue_id, dry_run=False)
    if side_l == "buy":
        quote = venue_quote_asset(venue_id)
        need = round(float(notional_usd) * (1.0 + buffer_pct), 4)
        free = float(bals.get(quote) or 0)
        return {
            "ok": free >= need,
            "venue_id": venue_id,
            "side": "buy",
            "asset": quote,
            "free": round(free, 8),
            "need": need,
        }
    sym = str(symbol or "").upper()
    need = round(float(qty), 8)
    free = float(bals.get(sym) or 0)
    return {
        "ok": free >= need * (1.0 - buffer_pct),
        "venue_id": venue_id,
        "side": "sell",
        "asset": sym,
        "free": round(free, 8),
        "need": need,
    }


def max_funded_notional_usd(
    symbol: str,
    buy_venue: str,
    sell_venue: str,
    buy_ask: float,
    *,
    configured_usd: float,
    buffer_pct: float = 0.03,
) -> float:
    """Max USD notional both arb legs can fund at ``buy_ask`` (live spot balances)."""
    if buy_ask <= 0 or configured_usd <= 0:
        return 0.0
    if buy_venue == "internal" and sell_venue == "internal":
        return configured_usd
    buy_cap = configured_usd
    if buy_venue != "internal":
        quote = venue_quote_asset(buy_venue)
        free_quote = float(parse_spot_balances(buy_venue, dry_run=False).get(quote) or 0)
        buy_cap = free_quote / (1.0 + buffer_pct)
    sell_cap = configured_usd
    if sell_venue != "internal":
        sym = str(symbol or "").upper()
        free_coin = float(parse_spot_balances(sell_venue, dry_run=False).get(sym) or 0)
        sell_cap = free_coin * buy_ask * (1.0 - buffer_pct)
    return max(0.0, min(float(configured_usd), buy_cap, sell_cap))


def opportunity_funded(opp: Dict[str, Any], *, buffer_pct: float = 0.03) -> Dict[str, Any]:
    """True when both external legs have enough spot inventory for a live arb."""
    symbol = str(opp.get("symbol") or "").upper()
    notional = float(opp.get("notional_usd") or 0)
    buy_price = float(opp.get("buy_ask") or 0)
    qty = round(notional / buy_price, 8) if buy_price > 0 else 0.0
    buy_v = str(opp.get("buy_venue") or "")
    sell_v = str(opp.get("sell_venue") or "")
    buy_chk = can_fund_arb_leg(buy_v, symbol, "buy", qty=qty, notional_usd=notional, buffer_pct=buffer_pct)
    sell_chk = can_fund_arb_leg(sell_v, symbol, "sell", qty=qty, notional_usd=notional, buffer_pct=buffer_pct)
    ok = bool(buy_chk.get("ok")) and bool(sell_chk.get("ok"))
    return {"ok": ok, "qty": qty, "buy": buy_chk, "sell": sell_chk}


def probe_all_venues() -> Dict[str, Any]:
    """Ping public tickers + private account endpoints (paper if no keys) across all venues."""
    cfg = conn.load_connectors_config()
    api_cfg = load_api_config()
    venue_ids = [v["id"] for v in (cfg.get("venues") or []) if isinstance(v, dict) and v.get("id")]
    rows: List[Dict[str, Any]] = []
    for vid in venue_ids:
        pub = conn.fetch_ticker(vid, "BTC", timeout=4.0)
        vapi = (api_cfg.get("venues") or {}).get(vid) or {}
        priv = get_account_balance(vid, dry_run=not (live_allowed() and venue_has_credentials(vid)))
        rows.append({
            "venue_id": vid,
            "public_ticker_ok": pub is not None,
            "live_supported": bool(vapi.get("live_supported", False)),
            "credentials_configured": venue_has_credentials(vid),
            "private_mode": priv.get("mode") or ("live" if priv.get("success") else "error"),
            "private_ok": bool(priv.get("success")),
        })
    return {
        "success": True,
        "probed_at": _iso(),
        "live_allowed": live_allowed(),
        "venue_count": len(rows),
        "public_ok_count": sum(1 for r in rows if r["public_ticker_ok"]),
        "credentials_count": sum(1 for r in rows if r["credentials_configured"]),
        "venues": rows,
    }


def onboard_venue_credentials(
    venue_id: str,
    *,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    passphrase: Optional[str] = None,
) -> Dict[str, Any]:
    """Store per-venue API credentials in the encrypted vault (admin onboarding)."""
    from backend.services import exchange_secrets_vault_service as vault

    vid = str(venue_id or "").strip().lower()
    if not vid:
        return {"success": False, "error": "missing_venue_id"}
    vcfg = _venue_api_cfg(vid)
    if not vcfg:
        return {"success": False, "error": "unknown_venue", "venue_id": vid}
    key_name, sec_name, pass_name = _secret_names(vid)
    results: Dict[str, Any] = {}
    if api_key is not None and str(api_key).strip():
        results["api_key"] = vault.set_secret(key_name, str(api_key).strip())
    if api_secret is not None and str(api_secret).strip():
        results["api_secret"] = vault.set_secret(sec_name, str(api_secret).strip())
    if passphrase is not None and str(passphrase).strip():
        results["passphrase"] = vault.set_secret(pass_name, str(passphrase).strip())
    if not results:
        return {"success": False, "error": "no_credentials_provided", "venue_id": vid}
    failed = [k for k, v in results.items() if not v.get("success")]
    probe = probe_all_venues()
    row = next((r for r in (probe.get("venues") or []) if r.get("venue_id") == vid), {})
    return {
        "success": not failed,
        "venue_id": vid,
        "stored": list(results.keys()),
        "failed": failed,
        "credentials_configured": bool(row.get("credentials_configured")),
        "private_ok": bool(row.get("private_ok")),
    }


def list_venue_capabilities() -> Dict[str, Any]:
    api_cfg = load_api_config()
    venues = []
    for vid, v in (api_cfg.get("venues") or {}).items():
        if not isinstance(v, dict):
            continue
        venues.append({
            "venue_id": vid,
            "live_supported": bool(v.get("live_supported")),
            "auth": v.get("auth"),
            "endpoints": list((v.get("endpoints") or {}).keys()),
            "credentials_configured": venue_has_credentials(vid),
        })
    return {"success": True, "live_allowed": live_allowed(), "venues": venues}
