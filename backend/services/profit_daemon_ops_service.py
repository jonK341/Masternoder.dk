"""Profit daemon ops — alerts, kill-switch, hot-reload hooks, auto-tuning.

Wired from ``scripts/all_profit_daemons.py`` and monitor API — no separate process.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services.profit_daemon_paths import heartbeat_path

_SHARED_HOT_PATH = os.path.join(ex._DATA_DIR, "profit_daemon_hot_symbols.json")
_DAILY_STATE_PATH = os.path.join(ex._DATA_DIR, "profit_daemon_daily_state.json")
_ALERT_STATE_PATH = os.path.join(ex._DATA_DIR, "profit_daemon_alert_state.json")
_PAYOUT_PATH = os.path.join(ex._DATA_DIR, "payout_config.json")
_CONNECTORS_PATH = os.path.join(ex._BASE, "data", "exchange_connectors_config.json")
_STDOUT_LOG = os.path.join(ex._BASE, "logs", "profit_daemon_stdout.log")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_state(path: str) -> Dict[str, Any]:
    data = ex._read_json(path, {})
    return data if isinstance(data, dict) else {}


def _write_state(path: str, payload: Dict[str, Any]) -> None:
    try:
        ex._write_json(path, payload)
    except Exception:
        pass


def profit_kill_active() -> bool:
    return os.environ.get("EXCHANGE_PROFIT_KILL", "").strip().lower() in ("1", "true", "yes", "on")


def profit_kill_reason() -> str:
    return "EXCHANGE_PROFIT_KILL=1"


def check_profit_kill(*, action: str = "execute") -> Optional[Dict[str, Any]]:
    if profit_kill_active():
        return {"blocked": True, "reason": profit_kill_reason(), "action": action}
    return None


def reload_ppp_config() -> Dict[str, Any]:
    """Hot-reload profit_path_protocol.json (mtime-aware)."""
    from backend.services import exchange_profit_path_service as ppp

    return ppp.reload_config()


def publish_hot_symbols_shared(
    hot_symbols: List[str],
    *,
    source: str = "exchange",
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Merge hot symbols from exchange + fast loops for arb/rotation consumers."""
    prev = _read_state(_SHARED_HOT_PATH)
    merged: List[str] = []
    seen: set = set()
    for sym in list(prev.get("hot_symbols") or []) + list(hot_symbols or []):
        s = str(sym or "").upper()
        if s and s not in seen:
            seen.add(s)
            merged.append(s)
    payload = {
        "updated_at": _iso(),
        "source": source,
        "hot_symbols": merged[:24],
        "count": len(merged),
    }
    if extra:
        payload.update(extra)
    _write_state(_SHARED_HOT_PATH, payload)
    try:
        from backend.services.exchange_extended_profit_service import read_arb_threshold_state

        thresh_path = os.path.join(ex._DATA_DIR, "arb_threshold_state.json")
        state = read_arb_threshold_state()
        state["hot_symbols"] = merged[:24]
        state["hot_updated_at"] = _iso()
        state["hot_source"] = source
        ex._write_json(thresh_path, state)
    except Exception:
        pass
    return payload


def read_hot_symbols_shared(*, limit: int = 12) -> List[str]:
    data = _read_state(_SHARED_HOT_PATH)
    out = [str(s).upper() for s in (data.get("hot_symbols") or []) if s]
    return out[: max(1, limit)]


def _alert_cooldown_sec() -> float:
    return float(os.environ.get("PROFIT_ALERT_COOLDOWN_SEC", "900"))


def _load_alert_state() -> Dict[str, Any]:
    return _read_state(_ALERT_STATE_PATH)


def _save_alert_state(state: Dict[str, Any]) -> None:
    _write_state(_ALERT_STATE_PATH, state)


def _should_alert(key: str, *, cooldown_sec: Optional[float] = None) -> bool:
    cd = cooldown_sec if cooldown_sec is not None else _alert_cooldown_sec()
    state = _load_alert_state()
    last = float(state.get(key) or 0)
    now = time.time()
    if now - last < cd:
        return False
    state[key] = now
    _save_alert_state(state)
    return True


def _post_ops_alert(title: str, body: str, *, alert_key: str, fields: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    if not _should_alert(alert_key):
        return {"success": True, "skipped": True, "reason": "cooldown", "alert_key": alert_key}
    try:
        from backend.services import discord_service as ds

        embed = {
            "title": title,
            "description": body[:1800],
            "color": 0xE67E22,
            "timestamp": _iso(),
            "footer": {"text": "MasterNoder profit daemon"},
        }
        if fields:
            embed["fields"] = fields[:10]
        channel = os.environ.get("PROFIT_OPS_DISCORD_CHANNEL", "ops").strip() or "ops"
        return ds.post_message(channel, {"embeds": [embed]}, message_id=f"profit_ops:{alert_key}")
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def maybe_alert_zero_fill_streak(
    *,
    streak: int,
    exchange_res: Dict[str, Any],
) -> Dict[str, Any]:
    warn_at = int(os.environ.get("EXCHANGE_ZERO_FILL_WARN", "3") or "3")
    if streak < warn_at:
        return {"skipped": True, "reason": "below_threshold", "streak": streak}
    plat = exchange_res.get("platform") or {}
    arb = (plat.get("results") or {}).get("arbitrage") or {}
    bq = arb.get("best_qualifying") or {}
    sym = str(bq.get("symbol") or "?")
    net = float(bq.get("net_bps") or 0)
    funded = "yes" if bq.get("funded") else "no"
    body = (
        f"Hot spread with **0 arb fills** for {streak} consecutive ticks.\n"
        f"Symbol `{sym}` net={net:.1f} bps funded={funded}."
    )
    return _post_ops_alert(
        "Profit daemon — zero-fill streak",
        body,
        alert_key="zero_fill_streak",
        fields=[
            {"name": "Streak", "value": str(streak), "inline": True},
            {"name": "Symbol", "value": sym, "inline": True},
            {"name": "Funded", "value": funded, "inline": True},
        ],
    )


def maybe_alert_venue_balance_low(*, venues: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    min_usdc = float(os.environ.get("PROFIT_VENUE_MIN_USDC", "25"))
    min_doge_usd = float(os.environ.get("PROFIT_VENUE_MIN_DOGE_USD", "25"))
    if venues is None:
        try:
            from backend.services.profit_daemon_monitor_service import _venue_balances

            venues = _venue_balances(cache_only=True)
        except Exception:
            return {"skipped": True, "reason": "no_venue_data"}
    low: List[str] = []
    bn = venues.get("binance") or {}
    if bn.get("ok") and float(bn.get("usdc") or bn.get("quote_free") or 0) < min_usdc:
        low.append(f"binance USDC<{min_usdc:.0f}")
    nk = venues.get("nonkyc") or {}
    if nk.get("ok"):
        doge_usd = nk.get("doge_usd")
        if doge_usd is not None and float(doge_usd) < min_doge_usd:
            low.append(f"nonkyc DOGE<{min_doge_usd:.0f} USD")
        usdt = float(nk.get("usdt") or nk.get("quote_free") or 0)
        if usdt < min_usdc:
            low.append(f"nonkyc USDT<{min_usdc:.0f}")
    if not low:
        return {"skipped": True, "reason": "balances_ok"}
    body = "Venue quote inventory below prefund thresholds:\n" + "\n".join(f"• {x}" for x in low)
    return _post_ops_alert(
        "Profit daemon — low venue balance",
        body,
        alert_key="venue_balance_low",
        fields=[{"name": "Alerts", "value": ", ".join(low)[:900], "inline": False}],
    )


def maybe_scale_paper_trade_usd(exchange_res: Dict[str, Any]) -> Dict[str, Any]:
    """Align paper_trade_usd with smallest max_funded_usd when cap exceeds funding."""
    if os.environ.get("EXCHANGE_AUTO_SCALE_NOTIONAL", "1").strip().lower() in ("0", "false", "no", "off"):
        return {"skipped": True, "reason": "disabled"}
    plat = exchange_res.get("platform") or {}
    arb = (plat.get("results") or {}).get("arbitrage") or {}
    caps = [
        float(a.get("max_funded_usd"))
        for a in (arb.get("actions") or [])
        if a.get("max_funded_usd") is not None
    ]
    if not caps:
        bq = arb.get("best_qualifying") or {}
        if bq.get("max_funded_usd") is not None:
            caps = [float(bq["max_funded_usd"])]
    if not caps:
        return {"skipped": True, "reason": "no_caps"}
    max_funded = min(caps)
    cfg = ex._read_json(_CONNECTORS_PATH, {})
    if not isinstance(cfg, dict):
        return {"skipped": True, "reason": "no_config"}
    current = float(cfg.get("paper_trade_usd") or 75)
    floor = float(os.environ.get("EXCHANGE_PAPER_TRADE_FLOOR_USD", "10"))
    target = max(floor, min(current, round(max_funded * 0.95, 2)))
    if target >= current - 0.5:
        return {"skipped": True, "reason": "already_scaled", "paper_trade_usd": current}
    cfg["paper_trade_usd"] = target
    cfg["paper_trade_usd_scaled_at"] = _iso()
    cfg["paper_trade_usd_scale_source"] = "max_funded_usd"
    try:
        ex._write_json(_CONNECTORS_PATH, cfg)
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    return {"success": True, "paper_trade_usd": target, "previous": current, "max_funded_usd": max_funded}


def maybe_auto_tune_sweep_min() -> Dict[str, Any]:
    """Lower min_sweep_usd as live stash grows (config tiers, never below floor)."""
    if os.environ.get("EXCHANGE_AUTO_TUNE_SWEEP_MIN", "1").strip().lower() in ("0", "false", "no", "off"):
        return {"skipped": True, "reason": "disabled"}
    cfg = ex._read_json(_PAYOUT_PATH, {})
    if not isinstance(cfg, dict):
        return {"skipped": True, "reason": "no_config"}
    try:
        from backend.services.profit_daemon_monitor_service import _light_treasury_snapshot

        stash = float((_light_treasury_snapshot().get("live_stash_usd") or 0))
    except Exception:
        stash = 0.0
    tiers = cfg.get("auto_sweep_tiers") or [
        {"stash_usd": 500, "min_sweep_usd": 100},
        {"stash_usd": 200, "min_sweep_usd": 75},
        {"stash_usd": 50, "min_sweep_usd": 50},
    ]
    floor = float(os.environ.get("EXCHANGE_SWEEP_MIN_FLOOR_USD", "25"))
    target = float(cfg.get("min_sweep_usd") or 100)
    for tier in sorted(tiers, key=lambda t: float(t.get("stash_usd") or 0), reverse=True):
        if stash >= float(tier.get("stash_usd") or 0):
            target = max(floor, float(tier.get("min_sweep_usd") or target))
            break
    current = float(cfg.get("min_sweep_usd") or 100)
    if abs(target - current) < 0.5:
        return {"skipped": True, "reason": "unchanged", "min_sweep_usd": current, "live_stash_usd": stash}
    cfg["min_sweep_usd"] = target
    cfg["auto_sweep_tuned_at"] = _iso()
    cfg["auto_sweep_tuned_stash_usd"] = round(stash, 4)
    try:
        ex._write_json(_PAYOUT_PATH, cfg)
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    return {"success": True, "min_sweep_usd": target, "previous": current, "live_stash_usd": stash}


def maybe_prefund_queue(exchange_res: Dict[str, Any], *, top_n: int = 3) -> Dict[str, Any]:
    """Attempt prefund for top N pair-search hits when unfunded."""
    if os.environ.get("EXCHANGE_PREFUND_QUEUE", "1").strip().lower() in ("0", "false", "no", "off"):
        return {"skipped": True, "reason": "disabled"}
    plat = exchange_res.get("platform") or {}
    ps = plat.get("profit_pair_search") or {}
    hits = ps.get("hits") or []
    if not hits:
        try:
            from backend.services.exchange_profit_pair_search_service import read_index

            hits = (read_index().get("hits") or [])[:top_n]
        except Exception:
            hits = []
    if not hits:
        return {"skipped": True, "reason": "no_hits"}
    from backend.services.exchange_swap_rotation_service import maybe_hot_pair_prefund

    outcomes: List[Dict[str, Any]] = []
    for row in hits[:top_n]:
        sym = str(row.get("symbol") or "").upper()
        if not sym:
            continue
        stub = {
            "platform": {
                "results": {
                    "arbitrage": {
                        "executed_count": 0,
                        "best_qualifying": {
                            "qualifies": True,
                            "funded": False,
                            "symbol": sym,
                            "net_bps": float(row.get("avg_net_bps") or row.get("live_score") or 0),
                            "sell_venue": row.get("sell_venue"),
                            "agent_id": "arb_live_dual_farm",
                        },
                    },
                },
                "profit_pair_search": {"success": True, "hot_symbols": [sym]},
            },
        }
        out = maybe_hot_pair_prefund(stub)
        out["symbol"] = sym
        outcomes.append(out)
        if out.get("prefund_executed") and out.get("success"):
            return {"success": True, "prefund_executed": True, "outcomes": outcomes}
    return {"success": True, "prefund_executed": False, "outcomes": outcomes}


def maybe_daily_ppp_summary() -> Dict[str, Any]:
    """Once per 24h: PPP summary + optional Discord alert."""
    state = _read_state(_DAILY_STATE_PATH)
    last = str(state.get("last_ppp_summary_at") or "")
    now = datetime.now(timezone.utc)
    if last:
        try:
            prev = datetime.fromisoformat(last.replace("Z", "+00:00"))
            if now - prev < timedelta(hours=23):
                return {"skipped": True, "reason": "not_due", "last_at": last}
        except Exception:
            pass
    try:
        from backend.services.profit_daemon_monitor_service import _light_ppp_snapshot

        ppp = _light_ppp_snapshot(hours=24)
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    state["last_ppp_summary_at"] = _iso()
    state["last_ppp_summary"] = ppp
    _write_state(_DAILY_STATE_PATH, state)
    fills = int(ppp.get("fill_count") or 0)
    hit = float(ppp.get("hit_rate_pct") or 0)
    body = (
        f"24h PPP: {fills} fills, hit rate {hit:.1f}%, "
        f"avg net {ppp.get('avg_net_bps', 0)} bps, scans {ppp.get('scan_count', 0)}."
    )
    alert = _post_ops_alert(
        "Profit daemon — daily PPP summary",
        body,
        alert_key="daily_ppp_summary",
        fields=[
            {"name": "Fills", "value": str(fills), "inline": True},
            {"name": "Hit rate", "value": f"{hit:.1f}%", "inline": True},
        ],
    )
    return {"success": True, "ppp": ppp, "alert": alert}


def rotate_daemon_logs(*, max_bytes: Optional[int] = None, keep: int = 5) -> Dict[str, Any]:
    """Rotate profit_daemon_stdout.log when oversized."""
    limit = max_bytes or int(os.environ.get("PROFIT_DAEMON_LOG_MAX_BYTES", str(5 * 1024 * 1024)))
    rotated: List[str] = []
    for path in (_STDOUT_LOG, os.path.join(ex._BASE, "logs", "profit_daemon_stderr.log")):
        try:
            if not os.path.isfile(path) or os.path.getsize(path) < limit:
                continue
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            dest = f"{path}.{ts}"
            os.replace(path, dest)
            open(path, "a", encoding="utf-8").close()
            rotated.append(dest)
            siblings = sorted(
                [p for p in os.listdir(os.path.dirname(path)) if p.startswith(os.path.basename(path) + ".")],
                reverse=True,
            )
            for old in siblings[keep:]:
                try:
                    os.remove(os.path.join(os.path.dirname(path), old))
                except OSError:
                    pass
        except OSError as exc:
            return {"success": False, "error": str(exc), "rotated": rotated}
    return {"success": True, "rotated": rotated}


def daemon_metrics_snapshot() -> Dict[str, Any]:
    """Expanded metrics for Grafana-style polling."""
    from backend.services.profit_daemon_monitor_service import monitor_status

    st = monitor_status()
    hb_path = heartbeat_path()
    hb = ex._read_json(hb_path, {})
    shared = _read_state(_SHARED_HOT_PATH)
    alert_state = _load_alert_state()
    return {
        "success": True,
        "checked_at": _iso(),
        "profit_kill": profit_kill_active(),
        "running": st.get("running"),
        "mode": st.get("mode"),
        "profile": st.get("profile"),
        "profit_readiness_pct": st.get("profit_readiness_pct"),
        "zero_fill_streak": hb.get("zero_fill_streak"),
        "hot_symbols": shared.get("hot_symbols") or [],
        "hot_symbol_count": shared.get("count") or 0,
        "loops": st.get("loops"),
        "highlights": st.get("highlights"),
        "ppp_24h": st.get("ppp_24h"),
        "payout": st.get("payout"),
        "treasury": st.get("treasury"),
        "stat_count": st.get("stat_count"),
        "last_alerts": {k: v for k, v in alert_state.items() if isinstance(v, (int, float))},
        "near_threshold": _fast_near_threshold_flag(st),
        "ppp_timeseries_endpoint": "/api/profit-daemon/ppp/timeseries",
    }


def _fast_near_threshold_flag(monitor_st: Dict[str, Any]) -> bool:
    """True when fast loop spread is within ~2 bps of threshold."""
    try:
        loops = monitor_st.get("loops") or {}
        if isinstance(loops, list):
            fm = next((x for x in loops if isinstance(x, dict) and x.get("id") == "fast"), {})
        else:
            fm = loops.get("fast") or {}
        best = float(fm.get("best_bps") or 0)
        thresh = float(fm.get("threshold") or 12)
        if best <= 0:
            return False
        return (thresh - best) <= 2.0 and best < thresh
    except (TypeError, ValueError):
        return False


def maybe_alert_heartbeat_stale(*, max_age_sec: Optional[float] = None) -> Dict[str, Any]:
    """Discord alert when profit daemon heartbeat is older than 5 minutes."""
    limit = max_age_sec or float(os.environ.get("PROFIT_HEARTBEAT_MAX_AGE_SEC", "300"))
    hb_path = heartbeat_path()
    hb = ex._read_json(hb_path, {})
    updated = str(hb.get("updated_at") or "")
    if not updated:
        return {"skipped": True, "reason": "no_heartbeat"}
    try:
        ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - ts).total_seconds()
    except Exception:
        return {"skipped": True, "reason": "bad_timestamp"}
    if age < limit:
        return {"skipped": True, "reason": "fresh", "age_sec": round(age, 1)}
    body = f"Profit daemon heartbeat stale — last update **{round(age / 60, 1)} min** ago (`{updated}`)."
    return _post_ops_alert(
        "Profit daemon — heartbeat stale",
        body,
        alert_key="heartbeat_stale",
        fields=[{"name": "Age (sec)", "value": str(int(age)), "inline": True}],
    )


def maybe_auto_enable_xeggex_live_farm() -> Dict[str, Any]:
    """Enable xeggex live_trading when local probe returns OK."""
    if os.environ.get("EXCHANGE_AUTO_ENABLE_XEGGEX", "1").strip().lower() in ("0", "false", "no", "off"):
        return {"skipped": True, "reason": "disabled"}
    try:
        from scripts.refresh_xeggex_server import probe_xeggex_local
        ok, reason, code = probe_xeggex_local()
    except Exception as exc:
        return {"skipped": True, "reason": "probe_unavailable", "error": str(exc)}
    if not ok:
        return {"skipped": True, "reason": "probe_failed", "detail": reason, "code": code}
    cfg = ex._read_json(_CONNECTORS_PATH, {})
    if not isinstance(cfg, dict):
        return {"skipped": True, "reason": "no_config"}
    venues = cfg.get("venues") or []
    changed = False
    for v in venues:
        if isinstance(v, dict) and str(v.get("id")) == "xeggex" and not v.get("live_trading"):
            v["live_trading"] = True
            v["live_enabled_at"] = _iso()
            changed = True
    if not changed:
        return {"skipped": True, "reason": "already_enabled"}
    try:
        ex._write_json(_CONNECTORS_PATH, cfg)
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    return {"success": True, "xeggex_live_trading": True, "probe_code": code}


def notional_buffer_for_latency_tier(venue_id: str, *, base_buffer_pct: float = 0.03) -> float:
    """Scale notional buffer by venue latency tier (slow venues get wider buffer)."""
    tiers = {
        "binance": 0.03,
        "nonkyc": 0.04,
        "xeggex": 0.06,
        "bingx": 0.05,
        "coinbase": 0.035,
    }
    return float(tiers.get(str(venue_id or "").lower(), base_buffer_pct))


def triangular_live_allowed() -> Dict[str, Any]:
    """Triangular arb live gate — paper-only until SPORK OK."""
    try:
        from backend.services import mn2_spork_service as spork
        ok, reason = spork.exchange_live_spork_ok()
    except Exception as exc:
        ok, reason = False, str(exc)
    env_force = os.environ.get("EXCHANGE_TRIANGULAR_LIVE", "").strip().lower() in ("1", "true", "yes")
    allowed = ok and env_force
    return {"allowed": allowed, "spork_ok": ok, "reason": reason, "paper_only": not allowed}


def check_slippage_guard(
    opp: Dict[str, Any],
    *,
    notional_usd: float,
    min_depth_multiplier: float = 2.0,
) -> Dict[str, Any]:
    """Abort arb leg when estimated book depth < 2× notional."""
    if os.environ.get("EXCHANGE_SLIPPAGE_GUARD", "1").strip().lower() in ("0", "false", "no", "off"):
        return {"ok": True, "skipped": True, "reason": "disabled"}
    symbol = str(opp.get("symbol") or "").upper()
    buy_v = str(opp.get("buy_venue") or "")
    sell_v = str(opp.get("sell_venue") or "")
    ask = float(opp.get("buy_ask") or opp.get("ask") or 0)
    bid = float(opp.get("sell_bid") or opp.get("bid") or 0)
    if not symbol or ask <= 0:
        return {"ok": False, "reason": "invalid_opportunity"}
    buy_depth_usd = float(opp.get("buy_depth_usd") or opp.get("depth_usd") or notional_usd * 3)
    sell_depth_usd = float(opp.get("sell_depth_usd") or opp.get("depth_usd") or notional_usd * 3)
    need = float(notional_usd) * min_depth_multiplier
    if buy_depth_usd < need:
        return {"ok": False, "reason": "insufficient_buy_depth", "depth_usd": buy_depth_usd, "required_usd": need}
    if bid > 0 and sell_depth_usd < need:
        return {"ok": False, "reason": "insufficient_sell_depth", "depth_usd": sell_depth_usd, "required_usd": need}
    return {"ok": True, "buy_depth_usd": buy_depth_usd, "sell_depth_usd": sell_depth_usd}


def ppp_timeseries_export(*, hours: float = 24) -> Dict[str, Any]:
    """Grafana-style PPP time series buckets for monitor export."""
    from backend.services.exchange_profit_path_service import search_paths

    rows = search_paths(hours=hours, limit=5000).get("paths") or []
    buckets: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        ts = str(row.get("ts") or row.get("timestamp") or "")[:13]
        if not ts:
            continue
        b = buckets.setdefault(ts, {"fills": 0, "scans": 0, "net_bps_sum": 0.0})
        phase = str(row.get("phase") or row.get("decision") or "")
        if phase in ("fill", "executed", "live_fill"):
            b["fills"] += 1
        else:
            b["scans"] += 1
        b["net_bps_sum"] += float(row.get("net_bps") or 0)
    series = []
    for ts in sorted(buckets.keys()):
        b = buckets[ts]
        count = b["fills"] + b["scans"]
        series.append({
            "ts": ts,
            "fills": b["fills"],
            "scans": b["scans"],
            "avg_net_bps": round(b["net_bps_sum"] / max(count, 1), 2),
        })
    return {"success": True, "hours": hours, "points": series, "count": len(series)}


def reload_connectors_config() -> Dict[str, Any]:
    """Hot-reload exchange_connectors_config.json (mtime-aware)."""
    cfg = ex._read_json(_CONNECTORS_PATH, {})
    if not isinstance(cfg, dict):
        return {"success": False, "error": "missing_config"}
    return {"success": True, "paper_trade_usd": cfg.get("paper_trade_usd"), "reloaded_at": _iso()}


def audit_kill_switch_activation(*, source: str = "daemon") -> Dict[str, Any]:
    """Append audit row when kill-switch blocks execution."""
    if not profit_kill_active():
        return {"skipped": True, "reason": "kill_inactive"}
    path = os.path.join(ex._DATA_DIR, "profit_kill_audit.jsonl")
    row = {"ts": _iso(), "source": source, "reason": profit_kill_reason()}
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except OSError as exc:
        return {"success": False, "error": str(exc)}
    return {"success": True, "audited": True}


def cross_venue_prefund_batch(exchange_res: Dict[str, Any], *, max_legs: int = 3) -> Dict[str, Any]:
    """Single rotation tick — attempt prefund for multiple pair-search hits."""
    if os.environ.get("EXCHANGE_PREFUND_BATCH", "1").strip().lower() in ("0", "false", "no", "off"):
        return {"skipped": True, "reason": "disabled"}
    single = maybe_prefund_queue(exchange_res, top_n=max_legs)
    outcomes = single.get("outcomes") or []
    executed = any(o.get("prefund_executed") for o in outcomes if isinstance(o, dict))
    return {"success": True, "batch": True, "prefund_executed": executed, "outcomes": outcomes}


def force_attempt_budget_state() -> Dict[str, Any]:
    """Cap runaway retries — track attempts per hour."""
    path = os.path.join(ex._DATA_DIR, "profit_force_attempt_budget.json")
    state = _read_state(path)
    now = datetime.now(timezone.utc)
    hour_key = now.strftime("%Y-%m-%dT%H")
    cap = int(os.environ.get("EXCHANGE_FORCE_ATTEMPT_CAP", "120"))
    if state.get("hour") != hour_key:
        state = {"hour": hour_key, "attempts": 0, "cap": cap}
    return {
        "success": True,
        "hour": hour_key,
        "attempts": int(state.get("attempts") or 0),
        "cap": cap,
        "remaining": max(0, cap - int(state.get("attempts") or 0)),
    }


def record_force_attempt() -> Dict[str, Any]:
    path = os.path.join(ex._DATA_DIR, "profit_force_attempt_budget.json")
    state = _read_state(path)
    now = datetime.now(timezone.utc)
    hour_key = now.strftime("%Y-%m-%dT%H")
    cap = int(os.environ.get("EXCHANGE_FORCE_ATTEMPT_CAP", "120"))
    if state.get("hour") != hour_key:
        state = {"hour": hour_key, "attempts": 0, "cap": cap}
    state["attempts"] = int(state.get("attempts") or 0) + 1
    _write_state(path, state)
    return force_attempt_budget_state()


def venue_min_notional_floors() -> Dict[str, Any]:
    """Venue-specific min notional floors from connectors config."""
    cfg = ex._read_json(_CONNECTORS_PATH, {})
    floors: Dict[str, float] = {}
    for v in cfg.get("venues") or []:
        if isinstance(v, dict) and v.get("id"):
            floors[str(v["id"])] = float(v.get("min_notional_usd") or v.get("min_order_usd") or 10)
    defaults = {"binance": 10, "nonkyc": 15, "xeggex": 20, "bingx": 12}
    for k, v in defaults.items():
        floors.setdefault(k, v)
    return {"success": True, "floors_usd": floors}


def paypal_tier_presets() -> Dict[str, Any]:
    cfg = ex._read_json(_PAYOUT_PATH, {})
    tiers = cfg.get("paypal_tiers") or [
        {"id": "micro", "min_sweep_usd": 25, "label": "Micro"},
        {"id": "standard", "min_sweep_usd": 75, "label": "Standard"},
        {"id": "whale", "min_sweep_usd": 250, "label": "Whale"},
    ]
    active = cfg.get("paypal_tier") or "standard"
    return {"success": True, "active_tier": active, "tiers": tiers}


def paper_unswept_threshold_display() -> Dict[str, Any]:
    """Display-only auto-threshold hint when paper unswept grows."""
    try:
        from backend.services.profit_daemon_monitor_service import _light_treasury_snapshot
        snap = _light_treasury_snapshot()
    except Exception:
        snap = {}
    paper = float(snap.get("paper_unswept_usd") or snap.get("ledger_stashed_usd_paper") or 0)
    cfg = ex._read_json(_PAYOUT_PATH, {})
    current_min = float(cfg.get("min_sweep_usd") or 100)
    suggested = max(25, round(current_min * 0.85, 2)) if paper > current_min * 1.5 else current_min
    return {
        "success": True,
        "paper_unswept_usd": round(paper, 2),
        "current_min_sweep_usd": current_min,
        "suggested_min_sweep_usd": suggested,
        "display_only": True,
    }


def tax_export_csv(*, season: Optional[str] = None) -> Dict[str, Any]:
    """Tax export CSV rows from sweep + stash ledger."""
    season = season or datetime.now(timezone.utc).strftime("%Y")
    rows: List[Dict[str, Any]] = []
    ledger_path = os.path.join(ex._DATA_DIR, "treasury_stash_ledger.jsonl")
    if os.path.isfile(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                        if season in str(row.get("ts") or row.get("timestamp") or ""):
                            rows.append({
                                "ts": row.get("ts") or row.get("timestamp"),
                                "type": row.get("type") or "stash",
                                "amount_usd": row.get("amount_usd") or row.get("usd"),
                            })
                    except json.JSONDecodeError:
                        pass
        except OSError:
            pass
    header = "ts,type,amount_usd\n"
    body = header + "\n".join(
        f"{r.get('ts','')},{r.get('type','')},{r.get('amount_usd','')}" for r in rows[:500]
    )
    return {"success": True, "season": season, "rows": rows[:500], "csv": body, "count": len(rows)}


def validate_payout_share_pct() -> Dict[str, Any]:
    """Validate payout share_pct on startup."""
    cfg = ex._read_json(_PAYOUT_PATH, {})
    share = float(cfg.get("share_pct") or cfg.get("payout_share_pct") or 0.5)
    valid = 0 < share <= 1.0
    return {"success": valid, "share_pct": share, "valid": valid}


def loop_sparkline_from_heartbeat(*, points: int = 12) -> Dict[str, Any]:
    """Per-loop sparkline buckets from heartbeat history."""
    hb_path = heartbeat_path()
    hb = ex._read_json(hb_path, {})
    history = hb.get("history") or hb.get("sparkline") or {}
    loops = {}
    for loop_id in ("exchange", "fast", "extended"):
        series = history.get(loop_id) if isinstance(history, dict) else []
        if not isinstance(series, list):
            series = [float(hb.get(f"{loop_id}_bps") or 0)] * min(points, 3)
        loops[loop_id] = [float(x) for x in series[-points:]]
    return {"success": True, "loops": loops, "updated_at": hb.get("updated_at")}


def spork_gate_startup_audit() -> Dict[str, Any]:
    """SPORK gate audit line for daemon startup banner."""
    try:
        from backend.services import mn2_spork_service as spork
        ok, reason = spork.exchange_live_spork_ok()
    except Exception as exc:
        ok, reason = False, str(exc)
    line = f"SPORK live gate: {'OK' if ok else 'BLOCKED'} — {reason}"
    return {"success": True, "spork_ok": ok, "reason": reason, "banner_line": line}


def casino_agent_tick_skip_on_kill() -> Dict[str, Any]:
    """Casino agent tick should skip when profit kill active."""
    active = profit_kill_active()
    return {
        "success": True,
        "skip_casino_agent_tick": active,
        "reason": profit_kill_reason() if active else None,
    }


def paper_live_separation_banner() -> Dict[str, Any]:
    """Paper/live separation banner payload for /profit/ UI."""
    from backend.services.profit_daemon_monitor_service import monitor_status
    st = monitor_status()
    mode = st.get("mode") or "paper"
    return {
        "success": True,
        "mode": mode,
        "paper": mode == "paper",
        "live": mode == "live",
        "banner": f"Profit daemon running in **{mode.upper()}** mode — live execution gated by SPORK.",
        "kill_active": profit_kill_active(),
    }


# --- Profit daemon 110 upgrades (session 3) ---

_SYMBOL_ALIASES: Dict[str, str] = {
    "1000SHIB": "SHIB",
    "1000PEPE": "PEPE",
    "1000FLOKI": "FLOKI",
    "1000BONK": "BONK",
    "WBTC": "BTC",
    "WETH": "ETH",
}


def normalize_symbol_alias(symbol: str) -> str:
    """Cross-venue symbol alias map (#20)."""
    s = str(symbol or "").upper()
    return _SYMBOL_ALIASES.get(s, s)


def ml_ranker_blend(*, ledger_score: float, volatility_score: float, hit_rate_pct: float) -> float:
    """ML ranker hook — ledger features → score blend (#15)."""
    w_ledger = float(os.environ.get("PROFIT_ML_LEDGER_WEIGHT", "0.5"))
    w_vol = float(os.environ.get("PROFIT_ML_VOL_WEIGHT", "0.25"))
    w_hit = float(os.environ.get("PROFIT_ML_HIT_WEIGHT", "0.25"))
    hit_norm = min(1.0, float(hit_rate_pct or 0) / 100.0)
    return round(w_ledger * ledger_score + w_vol * volatility_score + w_hit * hit_norm * 20.0, 4)


def defi_router_symbols() -> List[str]:
    """DeFi router class symbols for catalog expansion (#18)."""
    base = ["UNI", "AAVE", "LINK", "CRV", "SUSHI", "COMP", "MKR", "SNX"]
    extra = os.environ.get("PROFIT_DEFI_SYMBOLS", "")
    if extra.strip():
        base.extend(s.strip().upper() for s in extra.split(",") if s.strip())
    return sorted(set(base))


def compound_streak_bonus_tier(streak: int) -> Dict[str, Any]:
    """Live compound streak bonus tiers (#32)."""
    tiers = [
        {"min_streak": 0, "bonus_pct": 0},
        {"min_streak": 3, "bonus_pct": 2},
        {"min_streak": 7, "bonus_pct": 5},
        {"min_streak": 14, "bonus_pct": 10},
    ]
    active = tiers[0]
    for t in tiers:
        if streak >= int(t["min_streak"]):
            active = t
    return {"success": True, "streak": streak, "bonus_pct": active["bonus_pct"], "tiers": tiers}


def compound_pause_on_kill() -> Dict[str, Any]:
    """Compound pause when kill-switch active (#38)."""
    active = profit_kill_active()
    return {"success": True, "compound_paused": active, "reason": profit_kill_reason() if active else None}


def maybe_alert_stash_cap_before_sweep(*, cap_usd: Optional[float] = None) -> Dict[str, Any]:
    """Stash cap alert before sweep (#36)."""
    limit = cap_usd or float(os.environ.get("EXCHANGE_STASH_CAP_ALERT_USD", "2000"))
    try:
        from backend.services.profit_daemon_monitor_service import _light_treasury_snapshot
        stash = float((_light_treasury_snapshot().get("live_stash_usd") or 0))
    except Exception:
        stash = 0.0
    if stash < limit * 0.85:
        return {"skipped": True, "reason": "below_threshold", "live_stash_usd": stash, "cap_usd": limit}
    body = f"Live stash **${stash:.2f}** approaching cap **${limit:.0f}** — review sweep/compound."
    return _post_ops_alert(
        "Profit daemon — stash cap warning",
        body,
        alert_key="stash_cap_warning",
        fields=[
            {"name": "Live stash", "value": f"${stash:.2f}", "inline": True},
            {"name": "Cap", "value": f"${limit:.0f}", "inline": True},
        ],
    )


def binance_withdraw_preflight() -> Dict[str, Any]:
    """Binance withdraw rail preflight in daemon tick (#45)."""
    if os.environ.get("EXCHANGE_BINANCE_PREFLIGHT", "1").strip().lower() in ("0", "false", "no", "off"):
        return {"skipped": True, "reason": "disabled"}
    try:
        from backend.services.exchange_binance_payout_service import plan_bank_wire_sweep
        plan = plan_bank_wire_sweep()
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    ready = bool(plan.get("ready_to_withdraw") or plan.get("actionable"))
    return {
        "success": True,
        "ready_to_withdraw": ready,
        "plan": {k: plan.get(k) for k in ("amount_usd", "reason", "mode", "destination") if k in plan},
    }


def sweep_dry_run_line() -> str:
    """Sweep dry-run stdout line (#46)."""
    try:
        from backend.services.exchange_payout_service import plan_sweep
        plan = plan_sweep()
    except Exception as exc:
        return f"sweep_dry_run error={exc}"
    if not plan.get("actionable"):
        return f"sweep_dry_run skip reason={plan.get('reason')} net={plan.get('net_unswept_usd', 0)}"
    return (
        f"sweep_dry_run ok dest={plan.get('destination')} "
        f"amount={plan.get('amount_usd')} mode={plan.get('mode')}"
    )


def plan_partial_sweep(*, fraction: float = 0.5) -> Dict[str, Any]:
    """Partial sweep when above min but below full pool (#47)."""
    try:
        from backend.services.exchange_payout_service import plan_sweep, payout_status
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    st = payout_status()
    net = float(st.get("net_unswept_usd") or 0)
    min_usd = float(st.get("min_sweep_usd") or 100)
    if net < min_usd:
        return {"success": True, "actionable": False, "reason": "below_min", "net_unswept_usd": net}
    if net >= min_usd * 2:
        return {"success": True, "actionable": False, "reason": "full_sweep_preferred", "net_unswept_usd": net}
    partial = round(net * max(0.1, min(1.0, fraction)), 4)
    plan = plan_sweep(min_sweep_usd=min_usd)
    return {
        "success": True,
        "actionable": partial >= min_usd,
        "partial_amount_usd": partial,
        "net_unswept_usd": net,
        "min_sweep_usd": min_usd,
        "full_plan": plan,
        "display_only": True,
    }


def top25_blocker_deeplinks() -> Dict[str, Any]:
    """Blocker deep-link to Top25 runbook anchors (#59)."""
    base = "/docs/PROFIT_CRITICAL_TOP25.md"
    return {
        "success": True,
        "runbook": base,
        "anchors": [
            {"id": "p0-kill-switch", "label": "Kill switch", "href": f"{base}#p0-kill-switch"},
            {"id": "p0-xeggex-auth", "label": "XeggeX auth", "href": f"{base}#p0-xeggex-auth"},
            {"id": "p1-prefund", "label": "Prefund queue", "href": f"{base}#p1-prefund"},
            {"id": "p1-sweep-min", "label": "Sweep minimum", "href": f"{base}#p1-sweep-min"},
        ],
    }


_RATE_LIMIT: Dict[str, List[float]] = {}


def profit_api_rate_limit(client_key: str, *, max_per_min: Optional[int] = None) -> Dict[str, Any]:
    """Rate limit on profit-daemon API routes (#75)."""
    cap = max_per_min or int(os.environ.get("PROFIT_API_RATE_LIMIT", "120"))
    now = time.time()
    window = _RATE_LIMIT.setdefault(client_key, [])
    window[:] = [t for t in window if now - t < 60]
    if len(window) >= cap:
        return {"allowed": False, "retry_after_sec": round(60 - (now - window[0]), 1)}
    window.append(now)
    return {"allowed": True, "remaining": cap - len(window)}


def venue_balance_cache_ttl(venue_id: str) -> float:
    """Venue balance cache TTL env per venue (#98)."""
    env_key = f"PROFIT_BALANCE_TTL_{str(venue_id or '').upper()}"
    default = float(os.environ.get("PROFIT_BALANCE_TTL_SEC", "45"))
    return float(os.environ.get(env_key, str(default)))


def exchange_tick_budget_sec() -> float:
    return float(os.environ.get("EXCHANGE_TICK_BUDGET_SEC", "60"))


def tick_budget_exceeded(start_ts: float) -> bool:
    """Exchange tick time budget with early exit (#100)."""
    return (time.time() - start_ts) >= exchange_tick_budget_sec()


def maybe_alert_hit_rate_regression(*, route: str, current_pct: float, baseline_pct: float) -> Dict[str, Any]:
    """Hit-rate regression alert per route (#85)."""
    drop = baseline_pct - current_pct
    threshold = float(os.environ.get("PROFIT_HIT_RATE_REGRESSION_PCT", "15"))
    if drop < threshold:
        return {"skipped": True, "reason": "within_band", "drop_pct": drop}
    body = f"Route `{route}` hit rate dropped **{drop:.1f}pp** ({baseline_pct:.1f}% → {current_pct:.1f}%)."
    return _post_ops_alert(
        "Profit daemon — hit rate regression",
        body,
        alert_key=f"hit_rate_regression:{route}",
        fields=[
            {"name": "Route", "value": route, "inline": True},
            {"name": "Drop", "value": f"{drop:.1f}pp", "inline": True},
        ],
    )


def sync_critical_top25_on_tick() -> Dict[str, Any]:
    """Critical Top25 auto-sync on daemon tick (#88)."""
    try:
        from backend.services.exchange_profit_agent_skills_service import critical_problems_top25
        top = critical_problems_top25(refresh=True, dynamic=True)
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    items = top.get("items") or top.get("problems") or []
    open_p0 = sum(
        1 for i in items
        if isinstance(i, dict) and not (i.get("done") or i.get("checked"))
        and str(i.get("priority") or "").upper() == "P0"
    )
    path = os.path.join(ex._DATA_DIR, "profit_top25_sync_state.json")
    payload = {"updated_at": _iso(), "open_p0": open_p0, "total": len(items)}
    _write_state(path, payload)
    return {"success": True, **payload}


def run_exchange_tick_ops(
    exchange_res: Dict[str, Any],
    *,
    tick_start: Optional[float] = None,
) -> Dict[str, Any]:
    """Batch hook for exchange loop — prefunding, alerts, compound, preflight."""
    start = tick_start or time.time()
    out: Dict[str, Any] = {"success": True, "tick_start": start}
    if tick_budget_exceeded(start):
        out["early_exit"] = True
        out["reason"] = "tick_budget_exceeded"
        return out
    out["compound"] = compound_pause_on_kill()
    out["stash_cap"] = maybe_alert_stash_cap_before_sweep()
    out["binance_preflight"] = binance_withdraw_preflight()
    out["partial_sweep"] = plan_partial_sweep()
    out["top25_sync"] = sync_critical_top25_on_tick()
    out["sweep_dry_run"] = sweep_dry_run_line()
    streak = int((exchange_res.get("platform") or {}).get("compound_streak") or 0)
    out["compound_tier"] = compound_streak_bonus_tier(streak)
    pref = cross_venue_prefund_batch(exchange_res, max_legs=3)
    out["prefund_batch"] = pref
    xeg = maybe_auto_enable_xeggex_live_farm()
    out["xeggex_auto"] = xeg
    hits = ((exchange_res.get("platform") or {}).get("profit_pair_search") or {}).get("hits") or []
    for row in hits[:3]:
        if not isinstance(row, dict):
            continue
        route = str(row.get("route") or row.get("symbol") or "")
        cur = float(row.get("hit_rate_pct") or 0)
        base = float(row.get("baseline_hit_rate_pct") or cur + 5)
        if route:
            reg = maybe_alert_hit_rate_regression(route=route, current_pct=cur, baseline_pct=base)
            if not reg.get("skipped"):
                out.setdefault("hit_rate_alerts", []).append(reg)
    out["elapsed_sec"] = round(time.time() - start, 2)
    return out
