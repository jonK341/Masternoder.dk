"""Profit daemon monitor — heartbeat, payout, PPP summary for UI/API."""
from __future__ import annotations

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_HEARTBEAT = os.path.join(ex._BASE, "logs", "daemon_all_profit_heartbeat.json")
_STATE = os.path.join(ex._DATA_DIR, "profit_daemon_server_state.json")
_PAYOUT_PATH = os.path.join(ex._DATA_DIR, "payout_config.json")
_TREASURY_CFG_PATH = os.path.join(ex._BASE, "data", "exchange_treasury_config.json")
_TREASURY_LEDGER_PATH = os.path.join(ex._DATA_DIR, "treasury_stash_ledger.jsonl")
_PPP_LEDGER_PATH = os.path.join(ex._DATA_DIR, "profit_path_ledger.jsonl")
_VENUE_CACHE_FILE = os.path.join(ex._DATA_DIR, "venue_balance_monitor_cache.json")
_VENUE_CACHE_TTL_SEC = float(os.environ.get("PROFIT_MONITOR_VENUE_CACHE_SEC", "300"))
_VENUE_FETCH_TIMEOUT_SEC = float(os.environ.get("PROFIT_MONITOR_VENUE_TIMEOUT_SEC", "5"))
_MONITOR_STEP_TIMEOUT_SEC = float(os.environ.get("PROFIT_MONITOR_STEP_TIMEOUT_SEC", "6"))
_MONITOR_CACHE_TTL_SEC = float(os.environ.get("PROFIT_MONITOR_CACHE_SEC", "45"))
_MONITOR_CACHE: Dict[str, Any] = {}


def _run_timed(fn, *, timeout: Optional[float] = None, fallback: Any = None) -> Any:
    t = timeout if timeout is not None else _MONITOR_STEP_TIMEOUT_SEC
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(fn)
        try:
            return fut.result(timeout=t)
        except FuturesTimeout:
            return fallback if fallback is not None else {"success": False, "error": "timeout"}
        except Exception as exc:
            return fallback if fallback is not None else {"success": False, "error": str(exc)}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_summary_kv(summary: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for part in (summary or "").split():
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        out[k.strip()] = v.strip()
    return out


def _age_sec(ts: str) -> Optional[float]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds())
    except Exception:
        return None


def _stale_threshold_sec() -> float:
    return float(os.environ.get("PROFIT_DAEMON_STALE_SEC", "300"))


def _float_or_none(v: Any) -> Optional[float]:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _int_or_none(v: Any) -> Optional[int]:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _stat(
    stat_id: str,
    label: str,
    value: Any,
    *,
    unit: str = "",
    category: str = "daemon",
    status: str = "neutral",
    hint: str = "",
) -> Dict[str, Any]:
    return {
        "id": stat_id,
        "label": label,
        "value": value,
        "unit": unit,
        "category": category,
        "status": status,
        "hint": hint,
    }


def _fetch_venue_balance(vid: str) -> Dict[str, Any]:
    try:
        from backend.services import exchange_venue_api_service as vapi

        if not vapi.venue_has_credentials(vid):
            return {"ok": False, "reason": "no_creds"}
        bals = vapi.parse_spot_balances(vid, dry_run=False)
        quote = vapi.venue_quote_asset(vid)
        row: Dict[str, Any] = {
            "ok": True,
            "quote": quote,
            "quote_free": float(bals.get(quote) or 0),
            "usdc": float(bals.get("USDC") or 0),
            "usdt": float(bals.get("USDT") or 0),
            "doge": float(bals.get("DOGE") or 0),
            "fetched_at": _iso(),
        }
        if vid == "nonkyc":
            px = float(ex._price_usd("DOGE") or 0)
            row["doge_usd"] = round(row["doge"] * px, 2)
        return row
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _read_venue_cache_file() -> Dict[str, Any]:
    data = ex._read_json(_VENUE_CACHE_FILE, {})
    return data if isinstance(data, dict) else {}


def _write_venue_cache_file(payload: Dict[str, Any]) -> None:
    try:
        ex._write_json(_VENUE_CACHE_FILE, payload)
    except Exception:
        pass


def _monitor_cached(key: str, loader, *, ttl: Optional[float] = None) -> Any:
    """Short-lived in-process cache so repeated monitor polls stay under budget."""
    t = ttl if ttl is not None else _MONITOR_CACHE_TTL_SEC
    now = time.time()
    entry = _MONITOR_CACHE.get(key)
    if entry and now - float(entry.get("t") or 0) < t:
        return entry.get("v")
    val = loader()
    _MONITOR_CACHE[key] = {"t": now, "v": val}
    return val


def _venue_balances(*, cache_only: bool = False) -> Dict[str, Any]:
    cached = _read_venue_cache_file()
    cached_at = str(cached.get("cached_at") or "")
    age = _age_sec(cached_at)
    if cached.get("venues") and age is not None and age < _VENUE_CACHE_TTL_SEC:
        out = dict(cached.get("venues") or {})
        out["_meta"] = {"cached": True, "cache_age_sec": round(age, 1)}
        return out

    if cache_only:
        if cached.get("venues"):
            out = dict(cached.get("venues") or {})
            out["_meta"] = {
                "cached": True,
                "cache_age_sec": round(age, 1) if age is not None else None,
                "stale_fallback": True,
            }
            return out
        return {"_meta": {"cached": False, "skipped": "cache_only_no_data"}}

    out: Dict[str, Any] = {}
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(_fetch_venue_balance, vid): vid for vid in ("binance", "nonkyc")}
            for fut, vid in futures.items():
                try:
                    out[vid] = fut.result(timeout=_VENUE_FETCH_TIMEOUT_SEC)
                except FuturesTimeout:
                    stale = (cached.get("venues") or {}).get(vid)
                    out[vid] = stale if stale else {"ok": False, "error": "timeout"}
                except Exception as exc:
                    out[vid] = {"ok": False, "error": str(exc)}
        _write_venue_cache_file({"cached_at": _iso(), "venues": out})
        out["_meta"] = {"cached": False, "cache_age_sec": 0}
    except Exception as exc:
        out["error"] = str(exc)
        if cached.get("venues"):
            out = dict(cached.get("venues") or {})
            out["_meta"] = {"cached": True, "stale_fallback": True}
    return out


def _connectors_snapshot() -> Dict[str, Any]:
    cfg = ex._read_json(os.path.join(ex._BASE, "data", "exchange_connectors_config.json"), {})
    xeggex_live = False
    for v in cfg.get("venues") or []:
        if isinstance(v, dict) and str(v.get("id")) == "xeggex":
            xeggex_live = bool(v.get("live_trading"))
            break
    return {
        "min_margin_bps": float(cfg.get("min_margin_bps") or 14),
        "paper_trade_usd": float(cfg.get("paper_trade_usd") or 75),
        "prefunded_transfer_bps": float(cfg.get("prefunded_transfer_cost_bps") or 6),
        "xeggex_live_trading": xeggex_live,
    }


def _build_stats(
    *,
    loop_rows: List[Dict[str, Any]],
    running: bool,
    mode: Optional[str],
    profile: Optional[str],
    em: Dict[str, Any],
    fm: Dict[str, Any],
    cm: Dict[str, Any],
    payout: Dict[str, Any],
    treasury: Dict[str, Any],
    ppp: Dict[str, Any],
    venues: Dict[str, Any],
    conn: Dict[str, Any],
    critical_open: int,
    critical_done: int,
    hb_extra: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    stats: List[Dict[str, Any]] = []
    hb_extra = hb_extra or {}
    ex_age = next((r.get("age_sec") for r in loop_rows if r["loop"] == "exchange"), None)
    fa_age = next((r.get("age_sec") for r in loop_rows if r["loop"] == "fast"), None)
    ca_age = next((r.get("age_sec") for r in loop_rows if r["loop"] == "casino"), None)

    arb_exec = str(em.get("arb_exec") or "0/11")
    m = re.match(r"(\d+)/(\d+)", arb_exec)
    arb_fills = int(m.group(1)) if m else 0
    best_bps = _float_or_none(em.get("best_bps"))
    min_margin = _float_or_none(em.get("min_margin")) or conn.get("min_margin_bps")
    funded = str(em.get("funded") or "").lower()
    near = best_bps is not None and min_margin is not None and best_bps >= min_margin - 2

    stats.append(_stat("daemon_online", "Daemon online", "yes" if running else "no", category="daemon",
                       status="good" if running else "bad", hint="Server systemd heartbeat"))
    stats.append(_stat("mode", "Trading mode", mode or "?", category="daemon",
                       status="good" if mode == "live" else "warn"))
    stats.append(_stat("profile", "Profit profile", profile or "max", category="daemon"))
    stats.append(_stat("exchange_tick_age", "Exchange tick", round(ex_age) if ex_age is not None else "—",
                       unit="s", category="daemon", status="good" if ex_age and ex_age < 180 else "warn"))
    stats.append(_stat("fast_tick_age", "Fast rescan", round(fa_age) if fa_age is not None else "—",
                       unit="s", category="daemon", status="good" if fa_age and fa_age < 120 else "warn"))
    stats.append(_stat("casino_tick_age", "Casino tick", round(ca_age) if ca_age is not None else "—",
                       unit="s", category="casino"))

    stats.append(_stat("arb_fills", "Arb fills", arb_exec, category="arb",
                       status="good" if arb_fills > 0 else ("warn" if near else "neutral"),
                       hint="Spatial agents executed this tick"))
    stats.append(_stat("best_bps", "Best spread", best_bps if best_bps is not None else "—",
                       unit="bps", category="arb",
                       status="good" if best_bps and min_margin and best_bps >= min_margin else "neutral"))
    stats.append(_stat("best_net", "Best net", em.get("best_net", "—"), unit="bps", category="arb"))
    stats.append(_stat("best_agent", "Top agent", em.get("best_agent", "—"), category="arb"))
    stats.append(_stat("min_margin", "Min margin", min_margin, unit="bps", category="arb"))
    stats.append(_stat("arb_funded", "Buy leg funded", funded or "?", category="arb",
                       status="good" if funded == "yes" else "warn"))
    stats.append(_stat("arb_block", "Arb blocker", em.get("arb_block", "—"), category="arb",
                       status="warn" if em.get("arb_block") else "good"))
    stats.append(_stat("arb_skip", "Skip reason", em.get("arb_skip", "—"), category="arb"))
    stats.append(_stat("live_trades", "Live arb legs", em.get("live_trades", 0), category="arb"))

    ai = em.get("ai_exec")
    stats.append(_stat("ai_exec", "AI trader", ai if ai is not None else "—", category="arb",
                       status="good" if str(ai).lower() in ("true", "1") else "neutral"))
    stats.append(_stat("cross_actions", "Cross-trade swaps", em.get("cross_actions", 0), category="arb",
                       status="good" if _int_or_none(em.get("cross_actions")) and _int_or_none(em.get("cross_actions")) >= 7 else "neutral"))
    stats.append(_stat("ext_exec", "Extended strategies", em.get("ext_exec", "—"), category="arb"))
    stats.append(_stat("user_agents", "User marketplace ticks", em.get("user_agents", 0), category="arb"))

    zfs = em.get("zero_fill_streak") or hb_extra.get("zero_fill_streak")
    stats.append(_stat("zero_fill_streak", "Zero-fill streak", zfs if zfs is not None else 0, category="arb",
                       status="bad" if zfs and int(zfs) >= 3 else "good",
                       hint="Hot ticks with arb_exec=0"))
    ps_hot = em.get("pair_search") or em.get("search_hot") or "—"
    stats.append(_stat("pair_search_hot", "Pair search hot", ps_hot, category="search",
                       status="good" if ps_hot and ps_hot != "—" else "neutral",
                       hint="Top symbols from ledger+catalog ranking"))
    stats.append(_stat("hot_prefund", "Hot prefund", em.get("hot_prefund", "—"), category="search",
                       status="good" if str(em.get("hot_prefund") or "").startswith("ok") else "neutral"))
    shared_hot = hb_extra.get("hot_symbols") or []
    if shared_hot:
        stats.append(_stat("shared_hot", "Shared hot symbols", ",".join(shared_hot[:4]), category="search",
                           hint="Exchange+fast loop merged index"))

    stats.append(_stat("fast_best_bps", "Fast best spread", fm.get("best_bps", "—"), unit="bps", category="fast"))
    stats.append(_stat("fast_threshold", "Fast threshold", fm.get("threshold", "—"), unit="bps", category="fast"))
    stats.append(_stat("fast_ready", "Fast near ready", fm.get("ready", "—"), category="fast",
                       status="good" if str(fm.get("ready")).lower() in ("yes", "true", "1") else "neutral"))
    stats.append(_stat("fast_ext_exec", "Fast ext exec", fm.get("ext_exec", "—"), category="fast"))

    casino_ran = str(cm.get("ran") or "")
    stats.append(_stat("casino_ran", "Casino agents", casino_ran or "—", category="casino",
                       status="good" if "3/3" in casino_ran else "warn"))

    bn = venues.get("binance") or {}
    nk = venues.get("nonkyc") or {}
    vmeta = venues.get("_meta") or {}
    usdc = bn.get("usdc") or bn.get("quote_free")
    stats.append(_stat("binance_usdc", "Binance USDC", round(usdc, 2) if usdc is not None else "—",
                       unit="USD", category="funding",
                       status="good" if usdc and usdc >= 25 else "warn", hint="Buy-leg quote balance"))
    stats.append(_stat("nonkyc_usdt", "NonKYC USDT", round(nk.get("usdt") or nk.get("quote_free") or 0, 2),
                       unit="USD", category="funding"))
    stats.append(_stat("nonkyc_doge_usd", "NonKYC DOGE", nk.get("doge_usd", "—"),
                       unit="USD", category="funding",
                       status="good" if nk.get("doge_usd") and nk["doge_usd"] >= 25 else "warn"))
    if vmeta.get("cached"):
        stats.append(_stat("venue_cache_age", "Balance cache", vmeta.get("cache_age_sec", "—"),
                           unit="s", category="funding", hint="Live venue API cached for fast monitor"))
    stats.append(_stat("paper_trade_usd", "Notional cap", conn.get("paper_trade_usd"), unit="USD", category="funding"))
    stats.append(_stat("prefunded_bps", "Prefunded cost", conn.get("prefunded_transfer_bps"), unit="bps", category="funding"))

    stash = treasury.get("ledger_stashed_usd_live") or treasury.get("live_stash_usd")
    stats.append(_stat("live_stash", "Live stash", round(float(stash), 4) if stash else 0,
                       unit="USD", category="treasury",
                       status="good" if stash and float(stash) > 0 else "neutral"))
    stats.append(_stat("compound", "Treasury compound", "on" if treasury.get("compound_on_trade") or treasury.get("auto_stash_on_trade") else "off",
                       category="treasury"))

    stats.append(_stat("ppp_fills_24h", "PPP fills 24h", ppp.get("fill_count", 0), category="ppp"))
    stats.append(_stat("ppp_scans_24h", "PPP scans 24h", ppp.get("scan_count", 0), category="ppp"))
    stats.append(_stat("ppp_hit_rate", "PPP hit rate", ppp.get("hit_rate_pct", 0), unit="%", category="ppp"))
    stats.append(_stat("ppp_avg_bps", "PPP avg net", ppp.get("avg_net_bps", 0), unit="bps", category="ppp"))
    top_skip = (ppp.get("top_skip_reasons") or [{}])[0]
    stats.append(_stat("ppp_top_skip", "Top skip", f"{top_skip.get('reason', '—')}×{top_skip.get('count', 0)}",
                       category="ppp"))

    pay_mode = payout.get("mode")
    stats.append(_stat("payout_mode", "Payout mode", pay_mode or "?", category="payout",
                       status="good" if pay_mode == "live" else "warn"))
    stats.append(_stat("paypal_live", "PayPal live", "yes" if (payout.get("paypal") or {}).get("live_enabled") else "no",
                       category="payout", status="good" if (payout.get("paypal") or {}).get("live_enabled") else "warn"))
    stats.append(_stat("auto_sweep", "Auto sweep", "on" if payout.get("auto_sweep") else "off", category="payout",
                       status="good" if payout.get("auto_sweep") else "warn"))
    stats.append(_stat("sweepable_usd", "Sweepable", round(float(payout.get("paypal_sweepable_usd") or 0), 2),
                       unit="USD", category="payout"))
    stats.append(_stat("min_sweep", "Sweep minimum", payout.get("min_sweep_usd", 100), unit="USD", category="payout"))

    xeggex = "live" if conn.get("xeggex_live_trading") else "blocked (401)"
    stats.append(_stat("xeggex", "XeggeX venue", xeggex, category="venues",
                       status="good" if conn.get("xeggex_live_trading") else "bad",
                       hint="Dual-venue farm needs XeggeX probe OK"))
    stats.append(_stat("critical_open", "Critical open", critical_open, category="ops",
                       status="good" if critical_open <= 3 else "warn"))
    stats.append(_stat("critical_done", "Critical done", critical_done, category="ops", status="good"))

    readiness = max(0, min(100, int(100 * critical_done / max(1, critical_done + critical_open))))
    if not running:
        readiness = max(0, readiness - 25)
    if funded == "no":
        readiness = max(0, readiness - 10)
    if best_bps is not None and min_margin is not None and best_bps < min_margin:
        readiness = max(0, readiness - 5)
    stats.append(_stat("profit_readiness", "Profit readiness", readiness, unit="%", category="ops",
                       status="good" if readiness >= 75 else ("warn" if readiness >= 50 else "bad"),
                       hint="Higher when criticals closed, daemon live, spreads near threshold"))

    return stats


def _sum_treasury_ledger() -> Dict[str, float]:
    cached = _monitor_cached("treasury_ledger_sums", _sum_treasury_ledger_uncached, ttl=60)
    return cached if isinstance(cached, dict) else _sum_treasury_ledger_uncached()


def _sum_treasury_ledger_uncached() -> Dict[str, float]:
    stashed_usd = 0.0
    stashed_paper_usd = 0.0
    stashed_live_usd = 0.0
    if os.path.isfile(_TREASURY_LEDGER_PATH):
        try:
            with open(_TREASURY_LEDGER_PATH, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    amount = float(row.get("amount_usd") or 0)
                    stashed_usd += amount
                    if str(row.get("mode") or "paper").lower() == "live":
                        stashed_live_usd += amount
                    else:
                        stashed_paper_usd += amount
        except Exception:
            pass
    return {
        "ledger_stashed_usd": round(stashed_usd, 4),
        "ledger_stashed_usd_paper": round(stashed_paper_usd, 4),
        "ledger_stashed_usd_live": round(stashed_live_usd, 4),
        "live_stash_usd": round(stashed_live_usd, 4),
    }


def _light_treasury_snapshot() -> Dict[str, Any]:
    """Fast treasury summary — config + ledger only (no wallet/points DB)."""
    cfg = ex._read_json(_TREASURY_CFG_PATH, {})
    sums = _sum_treasury_ledger()
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "compound_on_trade": bool(cfg.get("auto_stash_on_trade", True)),
        "auto_stash_on_trade": bool(cfg.get("auto_stash_on_trade", True)),
        **sums,
    }


def _light_payout_snapshot() -> Dict[str, Any]:
    """Fast payout summary — config + ledger only (no Binance/PayPal API probes)."""
    cfg = ex._read_json(_PAYOUT_PATH, {})
    paypal = cfg.get("paypal") if isinstance(cfg.get("paypal"), dict) else {}
    email = (os.environ.get("EXCHANGE_PAYOUT_PAYPAL_EMAIL") or paypal.get("email") or "").strip()
    share = float(paypal.get("share_pct") or 1.0)
    min_usd = float(cfg.get("min_sweep_usd") or 100)
    auto_sweep = bool(cfg.get("auto_sweep"))
    dest = str(cfg.get("destination") or ("paypal" if email else "binance"))
    paypal_live = os.environ.get("EXCHANGE_PAYOUT_PAYPAL_LIVE", "").strip().lower() in ("1", "true", "yes")
    sums = _sum_treasury_ledger()
    mode_ledger = "live" if paypal_live else "paper"
    pool = sums["ledger_stashed_usd_live"] if mode_ledger == "live" else sums["ledger_stashed_usd_paper"]
    swept_key = f"swept_total_usd_{mode_ledger}"
    swept = float(cfg.get(swept_key) or cfg.get("swept_total_usd") or 0)
    net = round(max(0.0, pool - swept), 4)
    sweepable = round(net * share, 4) if email else net
    ready = bool(email and sweepable >= min_usd) if dest == "paypal" else False
    return {
        "success": True,
        "destination": dest,
        "mode": "live" if paypal_live else "paper",
        "auto_sweep": auto_sweep,
        "min_sweep_usd": min_usd,
        "paypal": {
            "email": email,
            "connected": bool(email),
            "live_enabled": paypal_live,
        },
        "paypal_sweepable_usd": sweepable,
        "ready_to_sweep": ready,
        "light_snapshot": True,
    }


def _tail_jsonl(path: str, max_lines: int = 2500) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        return []
    from collections import deque

    buf: deque = deque(maxlen=max(1, max_lines))
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                buf.append(row)
    return list(buf)


def _light_ppp_snapshot(*, hours: float = 24) -> Dict[str, Any]:
    """Tail PPP ledger only — avoids full profit_path_service import."""
    from collections import Counter
    from datetime import timedelta

    rows = _tail_jsonl(_PPP_LEDGER_PATH, 2500)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=float(hours))
    filtered: List[Dict[str, Any]] = []
    for row in reversed(rows):
        ts_raw = str(row.get("ts") or "")
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except Exception:
            ts = None
        if ts and ts < cutoff:
            break
        filtered.append(row)
    scans = [r for r in filtered if r.get("phase") == "scan"]
    attempts = [r for r in filtered if r.get("phase") == "execute"]
    fills = [
        r for r in attempts
        if r.get("decision") in ("fill", "paper", "live") and (r.get("execution") or {}).get("success")
    ]
    skip_reasons = Counter(
        str(r.get("skip_reason") or "unknown")
        for r in filtered
        if r.get("decision") == "skip" and r.get("skip_reason")
    )
    hit_rate = round(100.0 * len(fills) / len(attempts), 1) if attempts else 0.0
    net_rows = [r for r in filtered if float(r.get("net_bps") or 0) != 0]
    avg_net = round(sum(float(r.get("net_bps") or 0) for r in net_rows) / len(net_rows), 2) if net_rows else 0.0
    return {
        "success": True,
        "window_hours": hours,
        "scan_count": len(scans),
        "attempt_count": len(attempts),
        "fill_count": len(fills),
        "hit_rate_pct": hit_rate,
        "avg_net_bps": avg_net,
        "top_skip_reasons": [{"reason": k, "count": v} for k, v in skip_reasons.most_common(8)],
    }


def _critical_snapshot() -> Dict[str, Any]:
    """Fast critical list from on-disk store (no PPP recompute or heavy imports)."""
    path = os.path.join(ex._DATA_DIR, "profit_critical_top25.json")
    store = ex._read_json(path, {})
    problems = store.get("problems") if isinstance(store.get("problems"), list) else []
    if problems:
        open_count = sum(1 for p in problems if not p.get("checked"))
        return {
            "open_count": open_count,
            "done_count": len(problems) - open_count,
            "problems": problems,
        }
    return {
        "open_count": int(store.get("open_count") or 0),
        "done_count": int(store.get("done_count") or 0),
        "problems": [],
    }


def monitor_status() -> Dict[str, Any]:
    hb = ex._read_json(_HEARTBEAT, {})
    loops = hb.get("loops") if isinstance(hb.get("loops"), dict) else {}
    stale_sec = _stale_threshold_sec()
    loop_rows: List[Dict[str, Any]] = []
    any_recent = False

    for name in ("exchange", "fast", "casino"):
        row = loops.get(name) if isinstance(loops.get(name), dict) else {}
        updated = str(row.get("updated_at") or "")
        age = _age_sec(updated)
        recent = age is not None and age <= stale_sec
        any_recent = any_recent or recent
        parsed = _parse_summary_kv(str(row.get("summary") or ""))
        loop_rows.append({
            "loop": name,
            "updated_at": updated,
            "age_sec": round(age, 1) if age is not None else None,
            "stale": not recent,
            "summary": row.get("summary"),
            "metrics": parsed,
        })

    server_state = ex._read_json(_STATE, {})

    def _load_payout() -> Dict[str, Any]:
        return _light_payout_snapshot()

    def _load_treasury() -> Dict[str, Any]:
        return _monitor_cached("treasury", _light_treasury_snapshot)

    def _load_ppp() -> Dict[str, Any]:
        return _monitor_cached("ppp_24h", lambda: _light_ppp_snapshot(hours=24))

    payout = _load_payout()
    treasury = _load_treasury()
    ppp = _load_ppp()
    critical = _critical_snapshot()

    exchange_m = next((r for r in loop_rows if r["loop"] == "exchange"), {})
    fast_m = next((r for r in loop_rows if r["loop"] == "fast"), {})
    casino_m = next((r for r in loop_rows if r["loop"] == "casino"), {})
    em = exchange_m.get("metrics") or {}
    fm = fast_m.get("metrics") or {}
    cm = casino_m.get("metrics") or {}
    venues = _venue_balances(cache_only=True)
    conn = _connectors_snapshot()

    arb_exec = str(em.get("arb_exec") or "")
    m = re.match(r"(\d+)/(\d+)", arb_exec)
    arb_fills = int(m.group(1)) if m else 0
    arb_agents = int(m.group(2)) if m else 0

    open_count = int(critical.get("open_count") or 0)
    done_count = int(critical.get("done_count") or 0)
    blockers = [
        {"id": p.get("id"), "priority": p.get("priority"), "title": p.get("title"), "category": p.get("category")}
        for p in (critical.get("problems") or [])
        if not p.get("checked")
    ][:8]

    stats = _build_stats(
        loop_rows=loop_rows,
        running=any_recent,
        mode=hb.get("mode") or server_state.get("mode"),
        profile=hb.get("profile") or server_state.get("profile"),
        em=em,
        fm=fm,
        cm=cm,
        payout=payout,
        treasury=treasury,
        ppp=ppp,
        venues=venues,
        conn=conn,
        critical_open=open_count,
        critical_done=done_count,
        hb_extra={
            k: v for k, v in hb.items()
            if k in ("zero_fill_streak", "hot_symbols", "hot_prefund", "profit_kill")
        },
    )

    readiness_stat = next((s for s in stats if s["id"] == "profit_readiness"), {})

    return {
        "success": True,
        "host": os.environ.get("DEPLOY_HOST", "masternoder.dk"),
        "running": any_recent,
        "stale_threshold_sec": stale_sec,
        "mode": hb.get("mode") or server_state.get("mode"),
        "profile": hb.get("profile") or server_state.get("profile"),
        "heartbeat_updated_at": hb.get("updated_at"),
        "loops": loop_rows,
        "stats": stats,
        "stat_count": len(stats),
        "blockers": blockers,
        "profit_readiness_pct": readiness_stat.get("value"),
        "highlights": {
            "arb_exec": arb_exec or None,
            "arb_fills": arb_fills,
            "arb_agents": arb_agents,
            "best_bps": _float_or_none(em.get("best_bps")),
            "cross_actions": _int_or_none(em.get("cross_actions")),
            "ext_exec": _int_or_none(em.get("ext_exec")),
            "ai_exec": em.get("ai_exec"),
            "funded": em.get("funded"),
            "sweep": em.get("sweep"),
        },
        "payout": {
            "mode": payout.get("mode"),
            "auto_sweep": payout.get("auto_sweep"),
            "min_sweep_usd": payout.get("min_sweep_usd"),
            "paypal_live": (payout.get("paypal") or {}).get("live_enabled"),
            "paypal_sweepable_usd": payout.get("paypal_sweepable_usd"),
            "ready_to_sweep": payout.get("ready_to_sweep"),
        },
        "treasury": {
            "live_stash_usd": treasury.get("ledger_stashed_usd_live") or treasury.get("live_stash_usd"),
            "compound_enabled": treasury.get("compound_on_trade") or treasury.get("auto_stash_on_trade"),
        },
        "ppp_24h": {
            "fill_count": ppp.get("fill_count"),
            "scan_count": ppp.get("scan_count"),
            "hit_rate_pct": ppp.get("hit_rate_pct"),
            "avg_net_bps": ppp.get("avg_net_bps"),
            "top_skip_reasons": ppp.get("top_skip_reasons"),
        },
        "venues": venues,
        "config": conn,
        "critical": {"open": open_count, "done": done_count},
        "profit_kill": bool(hb.get("profit_kill")),
        "zero_fill_streak": hb.get("zero_fill_streak"),
        "hot_symbols": hb.get("hot_symbols") or [],
        "server": server_state,
        "checked_at": _iso(),
    }


def record_server_install(*, profile: str = "max", mode: str = "live") -> Dict[str, Any]:
    state = {
        "installed_at": _iso(),
        "profile": profile,
        "mode": mode,
        "systemd_unit": "masternoder-profit-daemon.service",
    }
    ex._write_json(_STATE, state)
    return {"success": True, "state": state}
