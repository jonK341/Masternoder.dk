"""Operator exchange registry for The Profit Daemon Jon.

One JSON file (`data/exchanges_registry.json`) drives which venues are enabled,
which join the ladder, and how public tickers are parsed. Adding a venue is a
JSON write (reuse an existing ``parser`` id) plus optional private API block.
"""
from __future__ import annotations

import json
import os
import socket
import time
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from backend.services import crypto_exchange_service as ex

_REGISTRY_PATH = os.path.join(ex._BASE, "data", "exchanges_registry.json")
_CONNECTORS_PATH = os.path.join(ex._BASE, "data", "exchange_connectors_config.json")
_VENUE_API_PATH = os.path.join(ex._BASE, "data", "exchange_venue_api_config.json")

_KNOWN_PARSERS = frozenset({
    "binance", "coinbase", "kraken", "nonkyc", "kucoin", "okx", "bybit", "bitfinex",
    "gateio", "bitstamp", "cryptocom", "mexc", "bitget", "htx", "gemini", "bingx",
    "poloniex", "bitmart", "coinex", "lbank", "whitebit", "upbit", "xt", "bitunix",
    "phemex", "tapbit", "xeggex",
})

_KNOWN_AUTH = frozenset({
    "binance_hmac", "okx_hmac", "bybit_hmac", "nonkyc_hmac", "xeggex_hmac",
    "kucoin_hmac", "kraken_hmac", "coinbase_jwt_stub", "bitfinex_hmac_stub",
    "gateio_hmac_stub", "bitstamp_hmac_stub", "cryptocom_hmac_stub",
})


def _read(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return default


def _write(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def registry_path() -> str:
    return _REGISTRY_PATH


def load_registry() -> Dict[str, Any]:
    raw = _read(_REGISTRY_PATH, {})
    if not isinstance(raw, dict) or not isinstance(raw.get("exchanges"), list):
        return {"version": 1, "exchanges": [], "recommended_services": [], "control": {}}
    return raw


def save_registry(reg: Dict[str, Any]) -> None:
    _write(_REGISTRY_PATH, reg)


def list_exchanges(*, enabled_only: bool = False) -> List[Dict[str, Any]]:
    rows = []
    for row in load_registry().get("exchanges") or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        if enabled_only and not row.get("enabled", True):
            continue
        rows.append(dict(row))
    return rows


def get_exchange(venue_id: str) -> Optional[Dict[str, Any]]:
    vid = str(venue_id or "").lower().strip()
    for row in list_exchanges():
        if str(row.get("id") or "").lower() == vid:
            return row
    return None


def ladder_venues() -> Tuple[str, ...]:
    """Venues that participate in the resting ladder maker."""
    out = [
        str(r["id"]).lower()
        for r in list_exchanges()
        if r.get("ladder") and r.get("enabled", True)
    ]
    return tuple(out) or ("nonkyc", "binance")


def ladder_quotes() -> Dict[str, str]:
    quotes = {
        str(r["id"]).lower(): str(r.get("quote") or "USDT").upper()
        for r in list_exchanges()
        if r.get("ladder")
    }
    if "nonkyc" not in quotes:
        quotes["nonkyc"] = "USDT"
    if "binance" not in quotes:
        quotes["binance"] = "USDC"
    return quotes


def cross_trade_venues() -> List[str]:
    """Enabled venues suitable for cross-trade / arb scanning."""
    out: List[str] = []
    for row in list_exchanges(enabled_only=True):
        vid = str(row.get("id") or "").lower()
        if not vid or vid == "internal":
            continue
        # Prefer live-capable or ladder venues; still include public-enabled ones for scan.
        out.append(vid)
    return out or ["binance", "nonkyc", "xeggex"]


def primary_maker_venue() -> Dict[str, str]:
    """Default resting-maker venue (prefer non-Binance ladder venue)."""
    rows = list_exchanges(enabled_only=True)
    for row in rows:
        if row.get("ladder") and str(row.get("id") or "").lower() != "binance":
            return {
                "id": str(row["id"]).lower(),
                "quote": str(row.get("quote") or "USDT").upper(),
            }
    for row in rows:
        if row.get("live_trading") and str(row.get("id") or "").lower() != "binance":
            return {
                "id": str(row["id"]).lower(),
                "quote": str(row.get("quote") or "USDT").upper(),
            }
    return {"id": "nonkyc", "quote": "USDT"}


def hydrate_live_secrets_from_vault() -> Dict[str, Any]:
    """Copy vault secrets into process env for every registered exchange."""
    from backend.services.exchange_secrets_vault_service import get_secret

    loaded: List[str] = []
    for row in list_exchanges():
        creds = row.get("credentials_env") or {}
        for key in ("api_key", "api_secret", "api_passphrase"):
            name = str(creds.get(key) or "").strip()
            if not name or os.environ.get(name):
                continue
            got = get_secret(name)
            if got:
                os.environ[name] = str(got)
                loaded.append(name)
    return {"success": True, "loaded": loaded}


def known_parsers() -> List[str]:
    return sorted(_KNOWN_PARSERS)


def known_auth_modes() -> List[str]:
    return sorted(_KNOWN_AUTH)


def set_exchange_enabled(venue_id: str, enabled: bool) -> Dict[str, Any]:
    vid = str(venue_id or "").lower().strip()
    reg = load_registry()
    found = False
    for row in reg.get("exchanges") or []:
        if str(row.get("id") or "").lower() == vid:
            row["enabled"] = bool(enabled)
            found = True
            break
    if not found:
        return {"success": False, "error": "unknown_exchange", "id": vid}
    save_registry(reg)
    _sync_connectors_enabled(vid, bool(enabled))
    return {"success": True, "id": vid, "enabled": bool(enabled)}


def set_ladder_participation(venue_id: str, ladder: bool) -> Dict[str, Any]:
    vid = str(venue_id or "").lower().strip()
    reg = load_registry()
    found = False
    for row in reg.get("exchanges") or []:
        if str(row.get("id") or "").lower() == vid:
            row["ladder"] = bool(ladder)
            found = True
            break
    if not found:
        return {"success": False, "error": "unknown_exchange", "id": vid}
    save_registry(reg)
    return {"success": True, "id": vid, "ladder": bool(ladder)}


def add_exchange(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Add or update an exchange in the registry + public connectors config.

    Required: id, ticker_url, pair_template, quote.
    ``parser`` must be an existing parser id (defaults to id when known).
    Optional private trading: auth + api_base (+ live_trading).
    """
    vid = str(spec.get("id") or "").lower().strip()
    if not vid or not vid.replace("_", "").isalnum():
        return {"success": False, "error": "invalid_id"}
    parser = str(spec.get("parser") or (vid if vid in _KNOWN_PARSERS else "")).lower().strip()
    if parser not in _KNOWN_PARSERS:
        return {
            "success": False,
            "error": "unknown_parser",
            "hint": "Reuse a known parser id (e.g. binance, okx, nonkyc).",
            "known_parsers": known_parsers(),
        }
    ticker_url = str(spec.get("ticker_url") or "").strip()
    pair_template = str(spec.get("pair_template") or "{base}{quote}").strip()
    quote = str(spec.get("quote") or "USDT").upper().strip()
    if not ticker_url or "{pair}" not in ticker_url:
        return {"success": False, "error": "ticker_url_must_include_{pair}"}
    name = str(spec.get("name") or vid).strip()
    fee = float(spec.get("fee_taker_bps") or 20.0)
    enabled = bool(spec.get("enabled", True))
    ladder = bool(spec.get("ladder", False))
    auth = str(spec.get("auth") or "").strip() or None
    api_base = str(spec.get("api_base") or "").strip() or None
    live_trading = bool(spec.get("live_trading", False))
    if auth and auth not in _KNOWN_AUTH:
        return {"success": False, "error": "unknown_auth", "known_auth": known_auth_modes()}

    row = {
        "id": vid,
        "name": name,
        "enabled": enabled,
        "quote": quote,
        "fee_taker_bps": fee,
        "ticker_url": ticker_url,
        "pair_template": pair_template,
        "parser": parser,
        "ladder": ladder,
        "live_trading": live_trading and bool(auth and api_base),
        "auth": auth,
        "api_base": api_base,
        "credentials_env": {
            "api_key": f"{vid.upper()}_API_KEY",
            "api_secret": f"{vid.upper()}_API_SECRET",
        },
        "withdrawal_note": str(spec.get("withdrawal_note") or ""),
    }
    if spec.get("lowercase_pair"):
        row["lowercase_pair"] = True

    reg = load_registry()
    exchanges = list(reg.get("exchanges") or [])
    exchanges = [e for e in exchanges if str(e.get("id") or "").lower() != vid]
    exchanges.append(row)
    exchanges.sort(key=lambda e: str(e.get("id") or ""))
    reg["exchanges"] = exchanges
    save_registry(reg)

    _upsert_connector(row)
    if auth and api_base:
        _upsert_venue_api(row)

    return {"success": True, "exchange": row}


def _sync_connectors_enabled(venue_id: str, enabled: bool) -> None:
    cfg = _read(_CONNECTORS_PATH, {})
    if not isinstance(cfg, dict):
        return
    for venue in cfg.get("venues") or []:
        if isinstance(venue, dict) and str(venue.get("id") or "").lower() == venue_id:
            venue["enabled"] = enabled
    _write(_CONNECTORS_PATH, cfg)


def _upsert_connector(row: Dict[str, Any]) -> None:
    cfg = _read(_CONNECTORS_PATH, {})
    if not isinstance(cfg, dict):
        cfg = {"venues": []}
    venues = [v for v in (cfg.get("venues") or []) if isinstance(v, dict)]
    venues = [v for v in venues if str(v.get("id") or "").lower() != row["id"]]
    entry = {
        "id": row["id"],
        "name": row["name"],
        "enabled": row["enabled"],
        "fee_taker_bps": row.get("fee_taker_bps") or 20,
        "quote": row["quote"],
        "ticker_url": row["ticker_url"],
        "pair_template": row["pair_template"],
        "parser": row.get("parser") or row["id"],
        "withdrawal_note": row.get("withdrawal_note") or "",
    }
    if row.get("lowercase_pair"):
        entry["lowercase_pair"] = True
    venues.append(entry)
    cfg["venues"] = venues
    _write(_CONNECTORS_PATH, cfg)


def _upsert_venue_api(row: Dict[str, Any]) -> None:
    cfg = _read(_VENUE_API_PATH, {})
    if not isinstance(cfg, dict):
        cfg = {"venues": {}}
    venues = dict(cfg.get("venues") or {})
    existing = dict(venues.get(row["id"]) or {})
    existing.update({
        "auth": row.get("auth"),
        "api_base": row.get("api_base"),
        "live_supported": bool(row.get("live_trading")),
    })
    existing.setdefault("endpoints", {
        "account": {"method": "GET", "path": "/"},
        "order_market": {"method": "POST", "path": "/"},
    })
    venues[row["id"]] = existing
    cfg["venues"] = venues
    _write(_VENUE_API_PATH, cfg)


def companion_services_status() -> Dict[str, Any]:
    """Probe recommended companion services for the local control panel."""
    reg = load_registry()
    catalog = list(reg.get("recommended_services") or [])
    rows: List[Dict[str, Any]] = []
    for svc in catalog:
        if not isinstance(svc, dict):
            continue
        sid = str(svc.get("id") or "")
        row = dict(svc)
        row["status"] = _probe_service(sid, svc)
        rows.append(row)
    return {
        "success": True,
        "ts": time.time(),
        "services": rows,
        "ok": sum(1 for r in rows if (r.get("status") or {}).get("ok")),
        "total": len(rows),
    }


def _probe_service(sid: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if sid == "local_control":
            return {"ok": True, "detail": "this panel"}
        if sid == "redis_bus":
            return _probe_redis(os.environ.get("EXCHANGE_REDIS_URL") or spec.get("default") or "")
        if sid == "prometheus":
            port = int(os.environ.get("EXCHANGE_METRICS_PORT") or spec.get("port") or 9108)
            return _probe_http(f"http://127.0.0.1:{port}/metrics", expect_substr="PROCESS")
        if sid == "grafana":
            port = int(spec.get("port") or 3030)
            return _probe_tcp("127.0.0.1", port)
        if sid == "secrets_vault":
            from backend.services.exchange_secrets_vault_service import encryption_available
            ok = encryption_available()
            return {"ok": ok, "detail": "EXCHANGE_VAULT_KEY set" if ok else "vault key missing"}
        if sid == "binance_ws_feed":
            try:
                from backend.services.exchange_market_feed_service import cached_top
                top = cached_top("XRP", max_age_sec=120.0) or {}
                ok = bool(top.get("bid") or top.get("ask") or top.get("mid"))
                return {"ok": ok, "detail": "cache warm" if ok else "no cached top yet"}
            except Exception as exc:
                return {"ok": False, "detail": str(exc)}
        if sid == "heartbeat":
            from backend.services.profit_daemon_paths import heartbeat_path
            path = heartbeat_path()
            if not os.path.isfile(path):
                return {"ok": False, "detail": "no heartbeat yet"}
            age = round(time.time() - os.path.getmtime(path), 1)
            return {"ok": age < 600, "detail": f"age {age}s", "age_sec": age}
        if sid == "sales_api":
            return {"ok": True, "detail": "available via /api/sales on this panel"}
        if sid == "docker_compose":
            path = os.path.join(ex._BASE, "profit_daemon_jon", "docker-compose.yml")
            return {"ok": os.path.isfile(path), "detail": path if os.path.isfile(path) else "missing"}
        return {"ok": False, "detail": "unknown_service"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}


def _probe_tcp(host: str, port: int, timeout: float = 0.4) -> Dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"ok": True, "detail": f"{host}:{port} open"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}


def _probe_http(url: str, *, expect_substr: str = "", timeout: float = 0.8) -> Dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read(2048).decode("utf-8", errors="ignore")
            ok = resp.status == 200 and (not expect_substr or expect_substr.lower() in body.lower() or "python" in body.lower() or "#" in body)
            # prometheus_client often starts with process_ or # HELP
            if resp.status == 200 and not expect_substr:
                ok = True
            if resp.status == 200 and ("#" in body or "process_" in body or "exchange_" in body):
                ok = True
            return {"ok": ok, "detail": f"HTTP {resp.status}"}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}


def _probe_redis(url: str) -> Dict[str, Any]:
    if not url:
        return {"ok": False, "detail": "EXCHANGE_REDIS_URL unset"}
    try:
        import redis  # type: ignore
        client = redis.Redis.from_url(url, socket_connect_timeout=0.4, socket_timeout=0.4)
        client.ping()
        return {"ok": True, "detail": "PING ok"}
    except Exception as exc:
        # File fallback still works — mark degraded not fatal
        return {"ok": False, "detail": f"unreachable ({exc}); file bus fallback OK"}


def control_snapshot() -> Dict[str, Any]:
    """Full snapshot for the local browser control panel."""
    out: Dict[str, Any] = {
        "brand": "The Profit Daemon Jon",
        "ts": time.time(),
        "exchanges": list_exchanges(),
        "parsers": known_parsers(),
        "auth_modes": known_auth_modes(),
        "ladder_venues": list(ladder_venues()),
        "services": companion_services_status(),
        "control": (load_registry().get("control") or {}),
    }
    try:
        from backend.services.profit_daemon_jon_product_service import status_report, product_improvement_backlog
        out["tech"] = status_report()
        out["backlog"] = product_improvement_backlog()
    except Exception as exc:
        out["tech_error"] = str(exc)
    try:
        from scripts.exchange_sales_report import build_report
        out["sales_3h"] = build_report(3.0)
    except Exception as exc:
        out["sales_error"] = str(exc)
    try:
        from backend.services.profit_daemon_paths import heartbeat_path
        path = heartbeat_path()
        if os.path.isfile(path):
            out["heartbeat_age_sec"] = round(time.time() - os.path.getmtime(path), 1)
            out["heartbeat_path"] = path
    except Exception as exc:
        out["heartbeat_error"] = str(exc)
    live = os.environ.get("EXCHANGE_ARBITRAGE_LIVE", "").strip().lower() in ("1", "true", "yes")
    out["mode"] = {
        "live": live,
        "profile": os.environ.get("EXCHANGE_PROFIT_PROFILE") or "standard",
        "paper_default": not live,
    }
    return out
