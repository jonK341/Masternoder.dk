"""Profit Pair Search — rank trading pairs for execution using ledger history,
cross-venue catalog intersection, and live spread snapshots."""
from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.services import crypto_exchange_service as ex
from backend.services import external_exchange_connector_service as conn
from backend.services import exchange_venue_api_service as vapi

_INDEX_PATH = os.path.join(ex._DATA_DIR, "profit_pair_search_index.json")
_CATALOG_CACHE_PATH = os.path.join(ex._DATA_DIR, "profit_pair_catalog_cache.json")
_CFG_KEY = "profit_pair_search"


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def search_config() -> Dict[str, Any]:
    from backend.services.exchange_profit_path_service import load_config

    ppp = load_config()
    cfg = dict(ppp.get(_CFG_KEY) or {})
    cfg.setdefault("enabled", False)
    cfg.setdefault("top_n", 12)
    cfg.setdefault("ledger_lookback_hours", 24)
    cfg.setdefault("ledger_min_attempts", 1)
    cfg.setdefault("catalog_venues", ["binance", "nonkyc"])
    cfg.setdefault("live_scan_top", 24)
    cfg.setdefault("ledger_weight", 0.55)
    cfg.setdefault("live_weight", 0.45)
    cfg.setdefault("skip_agent_symbols_when_hot", True)
    cfg.setdefault("min_live_net_bps", 8.0)
    return cfg


def enabled() -> bool:
    env = os.environ.get("EXCHANGE_PROFIT_PAIR_SEARCH", "").strip().lower()
    if env in ("0", "false", "no", "off"):
        return False
    if env in ("1", "true", "yes", "on"):
        return True
    return bool(search_config().get("enabled", False))


def _venue_search_eligible(venue_id: str) -> bool:
    """Execution-eligible venue: creds + exchange_venue_api_config entry (excludes scan-only bingx)."""
    return vapi.venue_execution_eligible(venue_id)


def _execution_eligible_route(buy_venue: str, sell_venue: str) -> bool:
    buy_v = str(buy_venue or "").lower()
    sell_v = str(sell_venue or "").lower()
    if not buy_v or not sell_v:
        return False
    return _venue_search_eligible(buy_v) and _venue_search_eligible(sell_v)


def _filter_execution_hits(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep only routes tradable on private API venues (scan-only venues excluded)."""
    return [
        row for row in hits
        if _execution_eligible_route(str(row.get("buy_venue") or ""), str(row.get("sell_venue") or ""))
    ]


def read_index() -> Dict[str, Any]:
    data = ex._read_json(_INDEX_PATH, {})
    return data if isinstance(data, dict) else {}


def _write_index(payload: Dict[str, Any]) -> None:
    ex._write_json(_INDEX_PATH, payload)


def get_hot_symbols(*, limit: Optional[int] = None) -> List[str]:
    idx = read_index()
    hits = idx.get("hits") or []
    n = limit or int(search_config().get("top_n") or 12)
    out: List[str] = []
    seen: Set[str] = set()
    for row in hits:
        if not isinstance(row, dict):
            continue
        sym = str(row.get("symbol") or "").upper()
        if sym and sym not in seen:
            seen.add(sym)
            out.append(sym)
        if len(out) >= n:
            break
    return out


def _route_key(symbol: str, buy_venue: str, sell_venue: str) -> str:
    return f"{symbol.upper()}:{buy_venue.lower()}→{sell_venue.lower()}"


def ledger_ranked_routes(
    *,
    hours: Optional[float] = None,
    min_attempts: Optional[int] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Aggregate PPP ledger rows into route scores (hit_rate × avg_net_bps)."""
    from backend.services.exchange_profit_path_service import search_paths

    cfg = search_config()
    lookback = float(hours if hours is not None else cfg.get("ledger_lookback_hours") or 24)
    min_att = int(min_attempts if min_attempts is not None else cfg.get("ledger_min_attempts") or 1)
    rows = search_paths(hours=lookback, limit=10000).get("paths") or []

    stats: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "symbol": "",
            "buy_venue": "",
            "sell_venue": "",
            "attempts": 0,
            "fills": 0,
            "net_bps_sum": 0.0,
            "scan_net_sum": 0.0,
            "scans": 0,
            "last_profit_usd": 0.0,
        }
    )

    for row in rows:
        sym = str(row.get("symbol") or "").upper()
        venues = row.get("venues") or {}
        buy_v = str(venues.get("buy") or "")
        sell_v = str(venues.get("sell") or "")
        if not sym or not buy_v or not sell_v:
            continue
        key = _route_key(sym, buy_v, sell_v)
        st = stats[key]
        st["symbol"] = sym
        st["buy_venue"] = buy_v
        st["sell_venue"] = sell_v
        nb = float(row.get("net_bps") or 0)
        if row.get("phase") == "scan":
            st["scans"] += 1
            st["scan_net_sum"] += nb
        elif row.get("phase") == "execute":
            st["attempts"] += 1
            st["net_bps_sum"] += nb
            exec_block = row.get("execution") or {}
            if exec_block.get("success"):
                st["fills"] += 1
                st["last_profit_usd"] = max(
                    st["last_profit_usd"],
                    float(exec_block.get("realized_pnl_usd") or exec_block.get("est_profit_usd") or 0),
                )

    ranked: List[Dict[str, Any]] = []
    for key, st in stats.items():
        attempts = int(st["attempts"])
        fills = int(st["fills"])
        scans = int(st["scans"])
        if attempts < min_att and fills == 0 and scans < 2:
            continue
        avg_net = 0.0
        if attempts:
            avg_net = st["net_bps_sum"] / attempts
        elif scans:
            avg_net = st["scan_net_sum"] / scans
        hit_rate = (100.0 * fills / attempts) if attempts else (50.0 if scans >= 3 else 0.0)
        score = avg_net * (0.5 + hit_rate / 200.0)
        ranked.append({
            "route": key,
            "symbol": st["symbol"],
            "buy_venue": st["buy_venue"],
            "sell_venue": st["sell_venue"],
            "avg_net_bps": round(avg_net, 2),
            "hit_rate_pct": round(hit_rate, 1),
            "fill_count": fills,
            "attempt_count": attempts,
            "scan_count": scans,
            "last_profit_usd": round(st["last_profit_usd"], 4),
            "ledger_score": round(score, 2),
            "source": "ledger",
        })
    ranked.sort(key=lambda r: (r["fill_count"], r["ledger_score"], r["avg_net_bps"]), reverse=True)
    return ranked[: max(1, limit)]


def _fetch_binance_usdc_bases() -> Set[str]:
    cached = ex._read_json(_CATALOG_CACHE_PATH, {})
    if isinstance(cached, dict):
        age_ok = False
        try:
            fetched = cached.get("fetched_at") or ""
            if fetched:
                age = (
                    datetime.now(timezone.utc)
                    - datetime.fromisoformat(fetched.replace("Z", "+00:00"))
                ).total_seconds()
                age_ok = age < 3600
        except Exception:
            age_ok = False
        bases = cached.get("binance_usdc_bases")
        if age_ok and isinstance(bases, list):
            return {str(b).upper() for b in bases}

    bases: Set[str] = set()
    try:
        import requests
        from backend.services.exchange_http_util import force_ipv4_outbound_if_configured

        force_ipv4_outbound_if_configured()
        resp = requests.get(
            "https://api.binance.com/api/v3/exchangeInfo",
            timeout=8,
            headers={"User-Agent": "masternoder-pair-search/1.0"},
        )
        if resp.status_code == 200:
            for sym in (resp.json() or {}).get("symbols") or []:
                if not isinstance(sym, dict):
                    continue
                if sym.get("status") != "TRADING":
                    continue
                if str(sym.get("quoteAsset") or "").upper() != "USDC":
                    continue
                base = str(sym.get("baseAsset") or "").upper()
                if base and base not in ("USDC", "USDT", "BUSD"):
                    bases.add(base)
    except Exception:
        pass

    if not bases:
        cfg = conn.load_connectors_config()
        bases = {str(s).upper() for s in (cfg.get("supported_symbols") or [])}

    try:
        ex._write_json(
            _CATALOG_CACHE_PATH,
            {"fetched_at": _iso(), "binance_usdc_bases": sorted(bases)},
        )
    except Exception:
        pass
    return bases


def _fetch_nonkyc_usdt_bases() -> Set[str]:
    cached = ex._read_json(_CATALOG_CACHE_PATH, {})
    if isinstance(cached, dict):
        bases = cached.get("nonkyc_usdt_bases")
        fetched = cached.get("fetched_at") or ""
        try:
            age = (
                datetime.now(timezone.utc)
                - datetime.fromisoformat(fetched.replace("Z", "+00:00"))
            ).total_seconds()
            if age < 3600 and isinstance(bases, list):
                return {str(b).upper() for b in bases}
        except Exception:
            pass

    bases: Set[str] = set()
    try:
        import requests
        from backend.services.exchange_http_util import force_ipv4_outbound_if_configured

        force_ipv4_outbound_if_configured()
        resp = requests.get(
            "https://api.nonkyc.io/api/v2/markets",
            timeout=8,
            headers={"User-Agent": "masternoder-pair-search/1.0"},
        )
        if resp.status_code == 200:
            body = resp.json()
            markets = body if isinstance(body, list) else (body or {}).get("markets") or []
            for m in markets:
                if isinstance(m, dict):
                    name = str(m.get("name") or m.get("symbol") or "")
                else:
                    name = str(m or "")
                if "_USDT" in name.upper():
                    base = name.upper().split("_")[0]
                    if base:
                        bases.add(base)
                elif "-USDT" in name.upper():
                    base = name.upper().split("-")[0]
                    if base:
                        bases.add(base)
    except Exception:
        pass

    if not bases:
        cfg = conn.load_connectors_config()
        for sym in cfg.get("supported_symbols") or []:
            if conn.fetch_ticker("nonkyc", str(sym).upper(), timeout=4.0):
                bases.add(str(sym).upper())

    try:
        prev = ex._read_json(_CATALOG_CACHE_PATH, {})
        if not isinstance(prev, dict):
            prev = {}
        prev["fetched_at"] = _iso()
        prev["nonkyc_usdt_bases"] = sorted(bases)
        ex._write_json(_CATALOG_CACHE_PATH, prev)
    except Exception:
        pass
    return bases


def catalog_intersection(
    venues: Optional[List[str]] = None,
) -> List[str]:
    """Symbols tradable on all catalog venues (Binance USDC ∩ NonKYC USDT)."""
    cfg = search_config()
    catalog_venues = [str(v).lower() for v in (venues or cfg.get("catalog_venues") or ["binance", "nonkyc"])]
    conn_cfg = conn.load_connectors_config()
    fallback = {str(s).upper() for s in (conn_cfg.get("supported_symbols") or [])}

    if "binance" in catalog_venues and "nonkyc" in catalog_venues:
        common = _fetch_binance_usdc_bases() & _fetch_nonkyc_usdt_bases()
        if common:
            return sorted(common)
    if len(catalog_venues) >= 2:
        return sorted(fallback)

    vmap = conn._venue_map(conn_cfg)
    out = set(fallback)
    for vid in catalog_venues:
        if vid not in vmap:
            continue
        probe = sorted(out)[:30]
        priced = {s for s in probe if conn.fetch_ticker(vid, s, timeout=4.0)}
        if priced:
            out &= priced
    return sorted(out) if out else sorted(fallback)


def live_spread_rank(
    symbols: List[str],
    venues: Optional[List[str]] = None,
    *,
    notional_usd: Optional[float] = None,
    min_net_bps: Optional[float] = None,
    limit: int = 30,
    injected: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None,
) -> List[Dict[str, Any]]:
    """Live scan_opportunities on symbol subset, ranked by net_bps."""
    from backend.services import exchange_arbitrage_service as arb

    cfg = search_config()
    catalog_venues = list(venues or cfg.get("catalog_venues") or ["binance", "nonkyc"])
    min_nb = float(min_net_bps if min_net_bps is not None else cfg.get("min_live_net_bps") or 8)
    conn_cfg = conn.load_connectors_config()
    notional = float(notional_usd or conn_cfg.get("paper_trade_usd") or 25)

    scan = arb.scan_opportunities(
        symbols=symbols,
        venues=catalog_venues,
        notional_usd=notional,
        injected=injected,
    )
    hits: List[Dict[str, Any]] = []
    for opp in scan.get("opportunities") or []:
        nb = float(opp.get("net_bps") or 0)
        if nb < min_nb:
            continue
        hits.append({
            "symbol": str(opp.get("symbol") or "").upper(),
            "buy_venue": str(opp.get("buy_venue") or ""),
            "sell_venue": str(opp.get("sell_venue") or ""),
            "avg_net_bps": round(nb, 2),
            "est_profit_usd": round(float(opp.get("est_profit_usd") or 0), 4),
            "live_score": round(nb, 2),
            "fill_count": 0,
            "source": "live",
        })
    hits.sort(key=lambda r: (r["live_score"], r["est_profit_usd"]), reverse=True)
    return hits[: max(1, limit)]


def _merge_rankings(
    ledger_rows: List[Dict[str, Any]],
    live_rows: List[Dict[str, Any]],
    *,
    top_n: int,
) -> List[Dict[str, Any]]:
    cfg = search_config()
    lw = float(cfg.get("ledger_weight") or 0.55)
    sw = float(cfg.get("live_weight") or 0.45)

    combined: Dict[str, Dict[str, Any]] = {}

    def _upsert(row: Dict[str, Any], *, from_ledger: bool) -> None:
        sym = str(row.get("symbol") or "").upper()
        buy_v = str(row.get("buy_venue") or "")
        sell_v = str(row.get("sell_venue") or "")
        if not sym:
            return
        key = _route_key(sym, buy_v, sell_v) if buy_v and sell_v else sym
        cur = combined.setdefault(key, {
            "symbol": sym,
            "buy_venue": buy_v,
            "sell_venue": sell_v,
            "avg_net_bps": 0.0,
            "hit_rate_pct": 0.0,
            "fill_count": 0,
            "last_profit_usd": 0.0,
            "live_score": 0.0,
            "est_profit_usd": 0.0,
            "sources": [],
        })
        if from_ledger:
            cur["avg_net_bps"] = float(row.get("avg_net_bps") or cur["avg_net_bps"])
            cur["hit_rate_pct"] = float(row.get("hit_rate_pct") or cur["hit_rate_pct"])
            cur["fill_count"] = max(int(cur["fill_count"]), int(row.get("fill_count") or 0))
            cur["last_profit_usd"] = max(float(cur["last_profit_usd"]), float(row.get("last_profit_usd") or 0))
            if "ledger" not in cur["sources"]:
                cur["sources"].append("ledger")
        else:
            cur["live_score"] = max(float(cur["live_score"]), float(row.get("live_score") or 0))
            cur["est_profit_usd"] = max(float(cur["est_profit_usd"]), float(row.get("est_profit_usd") or 0))
            if not cur["buy_venue"]:
                cur["buy_venue"] = buy_v
            if not cur["sell_venue"]:
                cur["sell_venue"] = sell_v
            if "live" not in cur["sources"]:
                cur["sources"].append("live")

    for row in ledger_rows:
        _upsert(row, from_ledger=True)
    for row in live_rows:
        _upsert(row, from_ledger=False)

    ranked: List[Dict[str, Any]] = []
    for key, row in combined.items():
        ledger_part = float(row.get("avg_net_bps") or 0) * (0.5 + float(row.get("hit_rate_pct") or 0) / 200.0)
        live_part = float(row.get("live_score") or 0)
        score = lw * ledger_part + sw * live_part
        if row.get("fill_count"):
            score += min(15.0, float(row["fill_count"]) * 3.0)
        ranked.append({
            **row,
            "route": key,
            "search_score": round(score, 2),
        })
    ranked.sort(key=lambda r: (r["search_score"], r["fill_count"], r["live_score"]), reverse=True)
    return ranked[: max(1, top_n)]


def run_profit_pair_search(
    *,
    injected: Optional[Dict[str, Dict[str, Dict[str, float]]]] = None,
    venues: Optional[List[str]] = None,
    top_n: Optional[int] = None,
) -> Dict[str, Any]:
    """Run ledger + catalog + live search; persist index; return top hits."""
    if not enabled():
        return {"success": False, "error": "profit_pair_search_disabled", "enabled": False}

    cfg = search_config()
    n = int(top_n or cfg.get("top_n") or 12)
    catalog_venues = list(venues or cfg.get("catalog_venues") or ["binance", "nonkyc"])
    live_top = int(cfg.get("live_scan_top") or 24)

    ledger_rows = ledger_ranked_routes(limit=max(n * 2, 20))
    catalog_syms = catalog_intersection(catalog_venues)

    ledger_syms = [r["symbol"] for r in ledger_rows if r.get("symbol")]
    scan_pool = list(dict.fromkeys(ledger_syms + catalog_syms))[: max(live_top, n * 2)]

    live_rows = live_spread_rank(
        scan_pool,
        catalog_venues,
        limit=live_top,
        injected=injected,
    )

    hits = _merge_rankings(ledger_rows, live_rows, top_n=n)
    hits = _filter_execution_hits(hits)
    hot_symbols = list(dict.fromkeys(r["symbol"] for r in hits if r.get("symbol")))

    payload = {
        "updated_at": _iso(),
        "enabled": True,
        "top_n": n,
        "catalog_venues": catalog_venues,
        "catalog_symbol_count": len(catalog_syms),
        "ledger_route_count": len(ledger_rows),
        "live_hit_count": len(live_rows),
        "hot_symbols": hot_symbols,
        "hits": hits,
    }
    _write_index(payload)

    return {
        "success": True,
        "enabled": True,
        "updated_at": payload["updated_at"],
        "top_n": n,
        "hot_symbols": hot_symbols,
        "hit_count": len(hits),
        "hits": hits,
        "catalog_symbol_count": len(catalog_syms),
        "ledger_route_count": len(ledger_rows),
        "live_hit_count": len(live_rows),
    }


def resolve_agent_symbols(
    agent_symbols: List[str],
    *,
    hot_symbols: Optional[List[str]] = None,
) -> List[str]:
    """When search is hot, prefer search symbols over fixed agent lists."""
    cfg = search_config()
    if not enabled() or not cfg.get("skip_agent_symbols_when_hot", True):
        return agent_symbols
    hot = hot_symbols if hot_symbols is not None else get_hot_symbols()
    if hot:
        return hot
    return agent_symbols
