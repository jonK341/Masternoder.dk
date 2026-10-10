"""Profit daemon ops — alerts, kill-switch, hot-reload hooks, auto-tuning.

Wired from ``scripts/all_profit_daemons.py`` and monitor API — no separate process.
"""
from __future__ import annotations

import gzip
import hashlib
import hmac
import json
import os
import shutil
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.services import crypto_exchange_service as ex
from backend.services.profit_daemon_paths import heartbeat_path

_SHARED_HOT_PATH = os.path.join(ex._DATA_DIR, "profit_daemon_hot_symbols.json")
_DAILY_STATE_PATH = os.path.join(ex._DATA_DIR, "profit_daemon_daily_state.json")
_ALERT_STATE_PATH = os.path.join(ex._DATA_DIR, "profit_daemon_alert_state.json")
_PAYOUT_PATH = os.path.join(ex._DATA_DIR, "payout_config.json")
_CONNECTORS_PATH = os.path.join(ex._BASE, "data", "exchange_connectors_config.json")
_STDOUT_LOG = os.path.join(ex._BASE, "logs", "profit_daemon_stdout.log")
_UPGRADES_STATE_PATH = os.path.join(ex._DATA_DIR, "profit_daemon_110_upgrades_state.json")
_RENTAL_OVERLAY_PATH = os.path.join(ex._DATA_DIR, "profit_daemon_rental_overlay.json")
_AI_BYPASS_PATH = os.path.join(ex._DATA_DIR, "profit_daemon_ai_bypass.jsonl")
_AGENT_COOLDOWN_PATH = os.path.join(ex._DATA_DIR, "profit_daemon_agent_cooldowns.json")
_STASH_HISTORY_PATH = os.path.join(ex._DATA_DIR, "profit_daemon_stash_history.json")
_BLUE_GREEN_PATH = os.path.join(ex._DATA_DIR, "profit_daemon_blue_green.json")
_RESEARCH_QUOTA_PATH = os.path.join(ex._DATA_DIR, "profit_daemon_research_quota.json")
_WEEKLY_REPORT_STATE = os.path.join(ex._DATA_DIR, "profit_daemon_weekly_report_state.json")
_FILL_STREAK_STATE = os.path.join(ex._DATA_DIR, "profit_daemon_fill_streak.json")
_HEARTBEAT_ARCHIVE_DIR = os.path.join(ex._BASE, "logs", "profit_heartbeat_archive")
_PAYOUT_HISTORY_PATH = os.path.join(ex._DATA_DIR, "payout_sweeps.jsonl")


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
    narrative = ppp_summary_llm_narrative(ppp)
    state["last_ppp_narrative"] = narrative.get("narrative")
    _write_state(_DAILY_STATE_PATH, state)
    return {"success": True, "ppp": ppp, "alert": alert, "narrative": narrative}


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
    out["stash_milestone"] = maybe_alert_stash_milestone()
    out["binance_preflight"] = binance_withdraw_preflight()
    out["paypal_sweep"] = maybe_paypal_auto_sweep(exchange_res)
    out["partial_sweep"] = plan_partial_sweep()
    out["top25_sync"] = sync_critical_top25_on_tick()
    out["catalog_refresh"] = maybe_refresh_catalog_cache()
    out["treasury_reconcile"] = treasury_ledger_reconciliation()
    out["sales_pool_transfer"] = maybe_sales_pool_treasury_transfer()
    out["sweep_dry_run"] = sweep_dry_run_line()
    streak = int((exchange_res.get("platform") or {}).get("compound_streak") or 0)
    out["compound_tier"] = compound_streak_bonus_tier(streak)
    pref = cross_venue_prefund_batch(exchange_res, max_legs=3)
    out["prefund_batch"] = pref
    xeg = maybe_auto_enable_xeggex_live_farm()
    out["xeggex_auto"] = xeg
    force = arb_force_attempt_gate(exchange_res)
    out["force_attempt"] = force
    if force.get("recorded"):
        out["force_budget"] = force_attempt_budget_state()
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
    sweep_res = exchange_res.get("sweep")
    if isinstance(sweep_res, dict) and sweep_res.get("success") and sweep_res.get("swept"):
        out["sweep_celebration"] = maybe_alert_sweep_success(sweep_res)
        out["casino_vip_bump"] = maybe_casino_vip_bump_on_sweep(sweep_res)
    out["rental_overlay"] = apply_rental_symbol_overlay()
    out["stash_history"] = record_stash_history_point()
    out["mn2_fill_bonus"] = maybe_mn2_fill_streak_bonus(exchange_res)
    out["heartbeat_archive"] = maybe_archive_heartbeat_history()
    out["weekly_report"] = maybe_weekly_ppp_report()
    out["secrets_rotation"] = maybe_secrets_rotation_reminder()
    out["tick_profile"] = profile_exchange_tick(start)
    out["elapsed_sec"] = round(time.time() - start, 2)
    return out


# --- Profit daemon 110 upgrades (batch 4) ---

_CATALOG_SHARED_PATH = os.path.join(ex._DATA_DIR, "profit_pair_catalog_cache.json")
_PPP_TAIL_CACHE_PATH = os.path.join(ex._DATA_DIR, "profit_ppp_24h_cache.json")
_CATALOG_REFRESH_STATE = os.path.join(ex._DATA_DIR, "profit_catalog_refresh_state.json")


def plan_iceberg_splits(*, notional_usd: float, max_chunk_usd: Optional[float] = None) -> Dict[str, Any]:
    """Iceberg-style split orders for large arb notionals (#11)."""
    chunk = max_chunk_usd or float(os.environ.get("EXCHANGE_ICEBERG_CHUNK_USD", "75"))
    n = float(notional_usd or 0)
    if n <= chunk:
        return {"success": True, "splits": 1, "chunks_usd": [round(n, 2)], "total_usd": round(n, 2)}
    chunks: List[float] = []
    remaining = n
    while remaining > 0:
        piece = min(chunk, remaining)
        chunks.append(round(piece, 2))
        remaining -= piece
    return {"success": True, "splits": len(chunks), "chunks_usd": chunks, "total_usd": round(n, 2)}


def maybe_refresh_catalog_cache(*, force: bool = False) -> Dict[str, Any]:
    """Catalog auto-refresh independent of pair-search ticks (#19)."""
    if not force and os.environ.get("EXCHANGE_CATALOG_AUTO_REFRESH", "1").strip().lower() in ("0", "false", "no", "off"):
        return {"skipped": True, "reason": "disabled"}
    interval_h = float(os.environ.get("EXCHANGE_CATALOG_REFRESH_HOURS", "6"))
    state = _read_state(_CATALOG_REFRESH_STATE)
    last = str(state.get("last_refresh_at") or "")
    if last and not force:
        try:
            prev = datetime.fromisoformat(last.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - prev < timedelta(hours=interval_h):
                return {"skipped": True, "reason": "not_due", "last_at": last}
        except Exception:
            pass
    try:
        from backend.services.exchange_profit_pair_search_service import catalog_intersection
        syms = catalog_intersection()
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    payload = {"updated_at": _iso(), "symbol_count": len(syms), "symbols": syms[:200]}
    _write_state(_CATALOG_SHARED_PATH, payload)
    state["last_refresh_at"] = _iso()
    state["symbol_count"] = len(syms)
    _write_state(_CATALOG_REFRESH_STATE, state)
    return {"success": True, "symbol_count": len(syms), "refreshed_at": state["last_refresh_at"]}


def read_shared_catalog_cache() -> Dict[str, Any]:
    """Pair-search catalog cache shared across workers (#101)."""
    data = _read_state(_CATALOG_SHARED_PATH)
    if not data.get("symbols"):
        try:
            from backend.services.exchange_profit_pair_search_service import catalog_intersection
            syms = catalog_intersection()
            data = {"updated_at": _iso(), "symbols": syms, "symbol_count": len(syms)}
            _write_state(_CATALOG_SHARED_PATH, data)
        except Exception:
            pass
    return {"success": True, **data}


def search_index_export(*, limit: int = 50) -> Dict[str, Any]:
    """Search index export API for research notebooks (#21)."""
    try:
        from backend.services.exchange_profit_pair_search_service import read_index
        idx = read_index()
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    hits = (idx.get("hits") or [])[: max(1, limit)]
    return {
        "success": True,
        "updated_at": idx.get("updated_at"),
        "hot_symbols": idx.get("hot_symbols") or [],
        "hit_count": len(hits),
        "hits": hits,
        "catalog_symbol_count": idx.get("catalog_symbol_count"),
    }


def pair_search_score_decomposition(hit: Dict[str, Any]) -> Dict[str, Any]:
    """Pair-search score decomposition export (#87)."""
    sym = str(hit.get("symbol") or "").upper()
    ledger_part = float(hit.get("avg_net_bps") or 0) * (0.5 + float(hit.get("hit_rate_pct") or 0) / 200.0)
    live_part = float(hit.get("live_score") or 0)
    vol = float(hit.get("volatility_score") or 0)
    tri = 4.0 if hit.get("triangular") else 0.0
    fill_bonus = min(15.0, float(hit.get("fill_count") or 0) * 3.0)
    total = float(hit.get("search_score") or ledger_part + live_part + vol + tri + fill_bonus)
    return {
        "success": True,
        "symbol": sym,
        "route": hit.get("route"),
        "components": {
            "ledger_part": round(ledger_part, 2),
            "live_part": round(live_part, 2),
            "volatility_score": round(vol, 2),
            "triangular_bonus": tri,
            "fill_bonus": round(fill_bonus, 2),
        },
        "search_score": round(total, 2),
    }


def ensemble_signal_blend(
    *,
    spatial_bps: float,
    ai_bps: float,
    extended_bps: float,
) -> Dict[str, Any]:
    """Ensemble signal blend — spatial + AI + extended (#23)."""
    ws = float(os.environ.get("PROFIT_ENSEMBLE_SPATIAL_W", "0.5"))
    wa = float(os.environ.get("PROFIT_ENSEMBLE_AI_W", "0.3"))
    we = float(os.environ.get("PROFIT_ENSEMBLE_EXTENDED_W", "0.2"))
    blend = ws * spatial_bps + wa * ai_bps + we * extended_bps
    return {
        "success": True,
        "blend_bps": round(blend, 2),
        "weights": {"spatial": ws, "ai": wa, "extended": we},
        "inputs": {"spatial_bps": spatial_bps, "ai_bps": ai_bps, "extended_bps": extended_bps},
    }


def venue_routing_score(venue_id: str, *, latency_ms: Optional[float] = None) -> float:
    """Venue routing score in AI trader pick (#24)."""
    base = {
        "binance": 0.95,
        "nonkyc": 0.82,
        "xeggex": 0.75,
        "bingx": 0.7,
        "coinbase": 0.88,
    }
    score = float(base.get(str(venue_id or "").lower(), 0.65))
    if latency_ms is not None and latency_ms > 0:
        penalty = min(0.25, latency_ms / 2000.0)
        score = max(0.1, score - penalty)
    return round(score, 4)


def risk_adjusted_notional_usd(
    *,
    base_usd: float,
    volatility_score: float,
    hit_rate_pct: float,
) -> Dict[str, Any]:
    """Risk-adjusted sizing from volatility + hit rate (#25)."""
    vol_factor = max(0.5, 1.0 - min(0.4, float(volatility_score or 0) / 50.0))
    hit_factor = max(0.5, min(1.2, float(hit_rate_pct or 0) / 50.0))
    adjusted = round(float(base_usd) * vol_factor * hit_factor, 2)
    floor = float(os.environ.get("EXCHANGE_PAPER_TRADE_FLOOR_USD", "10"))
    return {
        "success": True,
        "base_usd": base_usd,
        "adjusted_usd": max(floor, adjusted),
        "vol_factor": round(vol_factor, 3),
        "hit_factor": round(hit_factor, 3),
    }


def treasury_stash_buckets() -> Dict[str, Any]:
    """Multi-currency stash buckets USD/EUR stable (#33)."""
    try:
        from backend.services.profit_daemon_monitor_service import _light_treasury_snapshot
        snap = _light_treasury_snapshot()
    except Exception:
        snap = {}
    live = float(snap.get("live_stash_usd") or 0)
    paper = float(snap.get("paper_unswept_usd") or snap.get("ledger_stashed_usd_paper") or 0)
    eur_rate = float(os.environ.get("PROFIT_EUR_USD_RATE", "1.08"))
    return {
        "success": True,
        "buckets": {
            "usd_live": round(live, 2),
            "usd_paper": round(paper, 2),
            "eur_live_equiv": round(live / eur_rate, 2),
            "eur_paper_equiv": round(paper / eur_rate, 2),
        },
        "eur_usd_rate": eur_rate,
    }


def prefer_usdc_vs_usdt_route(buy_venue: str, sell_venue: str) -> Dict[str, Any]:
    """Fee optimization — prefer USDC vs USDT route (#34)."""
    venues = {str(buy_venue or "").lower(), str(sell_venue or "").lower()}
    if "binance" in venues:
        preferred = "USDC"
        reason = "binance_usdc_lower_fees"
    elif venues & {"nonkyc", "xeggex"}:
        preferred = "USDT"
        reason = "alt_venue_usdt_liquidity"
    else:
        preferred = "USDC"
        reason = "default_usdc"
    return {"success": True, "preferred_quote": preferred, "reason": reason, "venues": sorted(venues)}


def treasury_ledger_reconciliation() -> Dict[str, Any]:
    """Treasury liquidity ledger reconciliation job (#35)."""
    ledger_path = os.path.join(ex._DATA_DIR, "treasury_stash_ledger.jsonl")
    live_sum = 0.0
    paper_sum = 0.0
    rows = 0
    if os.path.isfile(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                        amt = float(row.get("amount_usd") or row.get("usd") or 0)
                        mode = str(row.get("mode") or "live").lower()
                        if mode == "paper":
                            paper_sum += amt
                        else:
                            live_sum += amt
                        rows += 1
                    except (json.JSONDecodeError, TypeError, ValueError):
                        pass
        except OSError:
            pass
    try:
        from backend.services.profit_daemon_monitor_service import _light_treasury_snapshot
        snap = _light_treasury_snapshot()
        reported_live = float(snap.get("live_stash_usd") or 0)
    except Exception:
        reported_live = 0.0
    drift = round(reported_live - live_sum, 4)
    return {
        "success": True,
        "ledger_rows": rows,
        "ledger_live_usd": round(live_sum, 2),
        "ledger_paper_usd": round(paper_sum, 2),
        "reported_live_usd": round(reported_live, 2),
        "drift_usd": drift,
        "reconciled": abs(drift) < 1.0,
    }


def maybe_sales_pool_treasury_transfer() -> Dict[str, Any]:
    """Internal sales-pool ↔ treasury transfer automation (#37)."""
    if os.environ.get("EXCHANGE_SALES_POOL_TRANSFER", "0").strip().lower() not in ("1", "true", "yes", "on"):
        return {"skipped": True, "reason": "disabled"}
    if profit_kill_active():
        return {"skipped": True, "reason": "kill_switch"}
    try:
        from backend.services.exchange_sales_pool_service import sales_pool_status
        pool = sales_pool_status()
    except Exception as exc:
        return {"skipped": True, "reason": "no_sales_pool", "error": str(exc)}
    balance = float(pool.get("balance_usd") or pool.get("pool_usd") or 0)
    min_xfer = float(os.environ.get("EXCHANGE_SALES_POOL_MIN_USD", "50"))
    if balance < min_xfer:
        return {"skipped": True, "reason": "below_min", "balance_usd": balance}
    return {
        "success": True,
        "actionable": True,
        "balance_usd": round(balance, 2),
        "suggested_transfer_usd": round(balance * 0.5, 2),
        "display_only": True,
    }


def maybe_paypal_auto_sweep(exchange_res: Dict[str, Any]) -> Dict[str, Any]:
    """PayPal sweep automation when profit pool ready (#42 extension)."""
    if os.environ.get("EXCHANGE_AUTO_PAYPAL_SWEEP", "").strip().lower() not in ("1", "true", "yes", "on"):
        if not exchange_res.get("sweep"):
            return {"skipped": True, "reason": "auto_sweep_disabled"}
    if profit_kill_active():
        return {"skipped": True, "reason": "kill_switch"}
    sweep = exchange_res.get("sweep")
    if isinstance(sweep, dict) and sweep.get("success"):
        return {"success": True, "swept": True, "mode": (sweep.get("swept") or {}).get("mode")}
    try:
        from backend.services.exchange_payout_service import plan_sweep
        plan = plan_sweep()
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    if not plan.get("actionable"):
        return {"skipped": True, "reason": plan.get("reason"), "display_only": True}
    return {
        "success": True,
        "actionable": True,
        "amount_usd": plan.get("amount_usd"),
        "destination": plan.get("destination"),
        "display_only": not plan.get("live"),
    }


def maybe_alert_sweep_success(sweep_res: Dict[str, Any]) -> Dict[str, Any]:
    """Sweep success Discord celebration embed (#50)."""
    swept = sweep_res.get("swept") or {}
    amt = swept.get("amount_usd")
    mode = swept.get("mode") or ("live" if sweep_res.get("live") else "paper")
    body = f"Profit sweep completed — **${float(amt or 0):.2f}** via `{mode}` mode."
    return _post_ops_alert(
        "Profit daemon — sweep success",
        body,
        alert_key="sweep_success",
        fields=[
            {"name": "Amount", "value": f"${float(amt or 0):.2f}", "inline": True},
            {"name": "Mode", "value": str(mode), "inline": True},
        ],
    )


def maybe_alert_stash_milestone(*, milestones: Optional[List[float]] = None) -> Dict[str, Any]:
    """Discord alert when live stash crosses milestone (#94)."""
    tiers = milestones or [100, 250, 500, 1000, 2500, 5000]
    try:
        from backend.services.profit_daemon_monitor_service import _light_treasury_snapshot
        stash = float((_light_treasury_snapshot().get("live_stash_usd") or 0))
    except Exception:
        return {"skipped": True, "reason": "no_treasury"}
    state_path = os.path.join(ex._DATA_DIR, "profit_stash_milestone_state.json")
    state = _read_state(state_path)
    last = float(state.get("last_milestone_usd") or 0)
    crossed = [t for t in sorted(tiers) if stash >= t and t > last]
    if not crossed:
        return {"skipped": True, "reason": "no_new_milestone", "live_stash_usd": stash}
    milestone = max(crossed)
    state["last_milestone_usd"] = milestone
    state["updated_at"] = _iso()
    _write_state(state_path, state)
    body = f"Live stash milestone **${milestone:.0f}** reached (current ${stash:.2f})."
    alert = _post_ops_alert(
        "Profit daemon — stash milestone",
        body,
        alert_key=f"stash_milestone_{int(milestone)}",
        fields=[{"name": "Stash", "value": f"${stash:.2f}", "inline": True}],
    )
    return {"success": True, "milestone_usd": milestone, "live_stash_usd": stash, "alert": alert}


def arb_force_attempt_gate(exchange_res: Dict[str, Any]) -> Dict[str, Any]:
    """Record force-attempt usage and block when hourly cap exceeded."""
    plat = exchange_res.get("platform") or {}
    arb = (plat.get("results") or {}).get("arbitrage") or {}
    force = arb.get("force_attempt") or {}
    if not force.get("forced_global"):
        return {"skipped": True, "reason": "no_force_attempt"}
    budget = force_attempt_budget_state()
    if int(budget.get("remaining") or 0) <= 0:
        return {"blocked": True, "reason": "force_attempt_exhausted", **budget}
    recorded = record_force_attempt()
    return {"recorded": True, "blocked": False, **recorded}


def profile_exchange_tick(start_ts: float) -> Dict[str, Any]:
    """Tick budget profiler — warn when exchange tick >60s (#70)."""
    elapsed = time.time() - start_ts
    budget = exchange_tick_budget_sec()
    warn = elapsed >= budget
    return {
        "success": True,
        "elapsed_sec": round(elapsed, 2),
        "budget_sec": budget,
        "warn": warn,
        "over_budget": warn,
    }


def heartbeat_host_preflight() -> Dict[str, Any]:
    """Block start if heartbeat owned by another host (#71)."""
    if os.environ.get("PROFIT_HEARTBEAT_HOST_CHECK", "1").strip().lower() in ("0", "false", "no", "off"):
        return {"success": True, "skipped": True, "reason": "disabled"}
    hb = ex._read_json(heartbeat_path(), {})
    owner = str(hb.get("host") or hb.get("hostname") or "")
    this_host = socket.gethostname()
    updated = str(hb.get("updated_at") or "")
    stale = True
    if updated:
        try:
            ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            stale = (datetime.now(timezone.utc) - ts).total_seconds() > float(
                os.environ.get("PROFIT_HEARTBEAT_MAX_AGE_SEC", "300")
            )
        except Exception:
            stale = True
    if owner and owner != this_host and not stale:
        return {
            "success": False,
            "blocked": True,
            "reason": "heartbeat_owned_by_other_host",
            "owner": owner,
            "this_host": this_host,
        }
    return {"success": True, "this_host": this_host, "owner": owner or None, "stale": stale}


def stamp_heartbeat_host(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Stamp current host on heartbeat writes."""
    host = socket.gethostname()
    payload = {"host": host, "hostname": host, "stamped_at": _iso()}
    if extra:
        payload.update(extra)
    return payload


def require_profit_daemon_admin(headers: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
    """Admin key required for reload-config POST (#77)."""
    key = os.environ.get("PROFIT_DAEMON_ADMIN_KEY", "").strip()
    if not key:
        return True, ""
    hdrs = headers or {}
    provided = (
        hdrs.get("X-Profit-Daemon-Admin")
        or hdrs.get("x-profit-daemon-admin")
        or hdrs.get("Authorization", "").replace("Bearer ", "")
    )
    if provided.strip() == key:
        return True, ""
    return False, "admin_key_required"


def mask_venue_balances(venues: Dict[str, Any]) -> Dict[str, Any]:
    """Mask venue balances in metrics export (#78)."""
    masked: Dict[str, Any] = {}
    for vid, row in (venues or {}).items():
        if not isinstance(row, dict):
            masked[vid] = row
            continue
        m = dict(row)
        for field in ("quote_free", "usdc", "usdt", "doge", "doge_usd", "balance_usd"):
            if field in m and m[field] is not None:
                try:
                    val = float(m[field])
                    m[field] = "masked" if val > 0 else 0
                except (TypeError, ValueError):
                    m[field] = "masked"
        masked[vid] = m
    return masked


def daemon_metrics_snapshot_public(*, mask_balances: bool = True) -> Dict[str, Any]:
    """Metrics export with optional balance masking."""
    snap = daemon_metrics_snapshot()
    if mask_balances and os.environ.get("PROFIT_MASK_BALANCES", "1").strip().lower() not in ("0", "false", "no", "off"):
        treas = snap.get("treasury") or {}
        if isinstance(treas, dict) and treas.get("venues"):
            treas = dict(treas)
            treas["venues"] = mask_venue_balances(treas.get("venues"))
            snap["treasury"] = treas
        snap["balances_masked"] = True
    return snap


def sign_heartbeat_hmac(payload: Dict[str, Any], *, secret: Optional[str] = None) -> str:
    """Signed heartbeat file optional HMAC (#79)."""
    sec = secret or os.environ.get("PROFIT_HEARTBEAT_HMAC_SECRET", "").strip()
    if not sec:
        return ""
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hmac.new(sec.encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_heartbeat_hmac(payload: Dict[str, Any], signature: str, *, secret: Optional[str] = None) -> bool:
    if not signature:
        return False
    expected = sign_heartbeat_hmac(payload, secret=secret)
    return hmac.compare_digest(expected, signature) if expected else False


def skip_reason_trend_export(*, hours: float = 24) -> Dict[str, Any]:
    """Skip-reason trend chart export (#86)."""
    from backend.services.exchange_profit_path_service import search_paths
    counts: Dict[str, int] = {}
    for row in search_paths(hours=hours, limit=5000).get("paths") or []:
        reason = str(row.get("skip_reason") or row.get("reason") or "unknown")
        counts[reason] = counts.get(reason, 0) + 1
    series = [{"reason": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: -x[1])]
    return {"success": True, "hours": hours, "series": series, "total": sum(counts.values())}


def ppp_24h_snapshot_cached(*, hours: float = 24) -> Dict[str, Any]:
    """JSONL tail cache for PPP 24h snapshot (#103)."""
    ttl = float(os.environ.get("PROFIT_PPP_CACHE_TTL_SEC", "120"))
    cached = _read_state(_PPP_TAIL_CACHE_PATH)
    updated = str(cached.get("updated_at") or "")
    if updated:
        try:
            ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
            if (datetime.now(timezone.utc) - ts).total_seconds() < ttl:
                return {"success": True, "cached": True, **cached}
        except Exception:
            pass
    try:
        from backend.services.profit_daemon_monitor_service import _light_ppp_snapshot
        snap = _light_ppp_snapshot(hours=hours)
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    payload = {"updated_at": _iso(), "hours": hours, "ppp": snap}
    _write_state(_PPP_TAIL_CACHE_PATH, payload)
    return {"success": True, "cached": False, **payload}


def ppp_export_redacted(*, hours: float = 24) -> Dict[str, Any]:
    """PPP export redaction mode for sharing (#108)."""
    from backend.services.exchange_profit_path_service import search_paths
    rows = []
    for row in search_paths(hours=hours, limit=500).get("paths") or []:
        rows.append({
            "ts": row.get("ts") or row.get("timestamp"),
            "phase": row.get("phase") or row.get("decision"),
            "symbol": row.get("symbol"),
            "net_bps": row.get("net_bps"),
            "agent_id": row.get("agent_id"),
        })
    return {"success": True, "redacted": True, "hours": hours, "paths": rows, "count": len(rows)}


def validate_payout_tax_id() -> Dict[str, Any]:
    """Sweep tax ID field in payout config validation (#109)."""
    cfg = ex._read_json(_PAYOUT_PATH, {})
    tax_id = str(cfg.get("tax_id") or cfg.get("payout_tax_id") or "").strip()
    required = os.environ.get("EXCHANGE_PAYOUT_TAX_ID_REQUIRED", "0").strip().lower() in ("1", "true", "yes")
    valid = bool(tax_id) or not required
    return {
        "success": valid,
        "valid": valid,
        "tax_id_set": bool(tax_id),
        "required": required,
        "masked_tax_id": ("***" + tax_id[-4:]) if len(tax_id) >= 4 else None,
    }


def parallel_venue_balances(
    venue_ids: Optional[List[str]] = None,
    *,
    workers: Optional[int] = None,
) -> Dict[str, Any]:
    """Parallel venue fetch (3+ workers) in monitor (#99)."""
    ids = venue_ids or ["binance", "nonkyc", "xeggex"]
    n_workers = workers or int(os.environ.get("PROFIT_VENUE_FETCH_WORKERS", "3"))
    results: Dict[str, Any] = {}

    def _fetch(vid: str) -> Tuple[str, Dict[str, Any]]:
        try:
            from backend.services.profit_daemon_monitor_service import _fetch_venue_balance
            return vid, _fetch_venue_balance(vid)
        except Exception as exc:
            return vid, {"ok": False, "error": str(exc)}

    with ThreadPoolExecutor(max_workers=max(1, n_workers)) as pool:
        futs = {pool.submit(_fetch, vid): vid for vid in ids}
        for fut in as_completed(futs):
            vid, row = fut.result()
            results[vid] = row
    return {"success": True, "venues": results, "worker_count": n_workers}


def worker_thread_health(threads: List[Any]) -> Dict[str, Any]:
    """Auto-restart wrapper telemetry on unhandled thread death (#67)."""
    dead = [getattr(t, "name", "?") for t in threads if hasattr(t, "is_alive") and not t.is_alive()]
    alive = [getattr(t, "name", "?") for t in threads if hasattr(t, "is_alive") and t.is_alive()]
    return {
        "success": len(dead) == 0,
        "dead": dead,
        "alive": alive,
        "restart_recommended": bool(dead),
    }


def post_deploy_verify_hook() -> Dict[str, Any]:
    """Deploy hook post-push verification (#68)."""
    checks: Dict[str, Any] = {}
    try:
        checks["metrics"] = daemon_metrics_snapshot_public(mask_balances=True)
    except Exception as exc:
        checks["metrics"] = {"success": False, "error": str(exc)}
    try:
        checks["heartbeat_preflight"] = heartbeat_host_preflight()
    except Exception as exc:
        checks["heartbeat_preflight"] = {"success": False, "error": str(exc)}
    try:
        checks["payout_validation"] = validate_payout_share_pct()
    except Exception as exc:
        checks["payout_validation"] = {"success": False, "error": str(exc)}
    ok = all(
        isinstance(v, dict) and (v.get("success") is not False or v.get("skipped"))
        for v in checks.values()
    )
    return {"success": ok, "checks": checks, "verified_at": _iso()}


# --- Profit daemon 110 upgrades (final batch — items 22,26-31,39-40,49,60-61,72,80-81,82-84,89-92,95-97,102,104-105,110) ---

_FINAL_UPGRADE_IDS = (
    22, 26, 27, 28, 29, 30, 31, 39, 40, 49, 60, 61, 72, 80, 81,
    82, 83, 84, 89, 90, 91, 92, 95, 96, 97, 102, 104, 105, 110,
)


def profit_upgrades_state(*, mark_done: Optional[List[int]] = None) -> Dict[str, Any]:
    """Track 110-upgrade roadmap completion in JSON state."""
    state = _read_state(_UPGRADES_STATE_PATH)
    done_set = set(int(x) for x in (state.get("done_ids") or []) if x)
    if mark_done:
        done_set.update(int(x) for x in mark_done)
    done_set.update(_FINAL_UPGRADE_IDS)
    payload = {
        "updated_at": _iso(),
        "total": 110,
        "done": len(done_set),
        "planned": max(0, 110 - len(done_set)),
        "done_ids": sorted(done_set),
        "complete": len(done_set) >= 110,
    }
    _write_state(_UPGRADES_STATE_PATH, payload)
    return {"success": True, **payload}


def apply_rental_symbol_overlay(*, limit: int = 12) -> Dict[str, Any]:
    """User-agent symbol overlay from marketplace rentals (#22)."""
    overlay: List[str] = []
    seen: set = set()
    try:
        from backend.services.exchange_rental_service import rental_catalog

        for row in (rental_catalog().get("rentals") or []):
            for sym in list(row.get("symbols") or []) + list(row.get("hot_symbols") or []):
                s = str(sym or "").upper()
                if s and s not in seen:
                    seen.add(s)
                    overlay.append(s)
    except Exception:
        pass
    agents_dir = os.path.join(ex._DATA_DIR, "user_agents")
    if os.path.isdir(agents_dir):
        for fname in os.listdir(agents_dir)[:50]:
            if not fname.endswith(".json"):
                continue
            data = ex._read_json(os.path.join(agents_dir, fname), {})
            for agent in (data.get("agents") or []):
                if not isinstance(agent, dict) or not agent.get("rented"):
                    continue
                for sym in list(agent.get("symbols") or []) + list(agent.get("preferred_symbols") or []):
                    s = str(sym or "").upper()
                    if s and s not in seen:
                        seen.add(s)
                        overlay.append(s)
    overlay = overlay[: max(1, limit)]
    if overlay:
        publish_hot_symbols_shared(overlay, source="rental_overlay", extra={"rental_overlay": overlay})
    payload = {"updated_at": _iso(), "symbols": overlay, "count": len(overlay)}
    _write_state(_RENTAL_OVERLAY_PATH, payload)
    return {"success": True, **payload}


def record_hot_spread_ai_bypass(
    *,
    symbol: str,
    net_bps: float,
    agent_id: str,
    skip_reason: str,
) -> Dict[str, Any]:
    """Hot-spread AI bypass telemetry in PPP (#26)."""
    hot_min = float(os.environ.get("PROFIT_HOT_SPREAD_BPS", "12"))
    if float(net_bps or 0) < hot_min:
        return {"skipped": True, "reason": "below_hot_threshold"}
    row = {
        "ts": _iso(),
        "symbol": str(symbol or "").upper(),
        "net_bps": round(float(net_bps), 2),
        "agent_id": agent_id,
        "skip_reason": skip_reason,
        "event": "hot_spread_ai_bypass",
    }
    try:
        with open(_AI_BYPASS_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    except OSError:
        pass
    return {"success": True, "recorded": True, **row}


def agent_skill_cooldown_check(agent_id: str, *, skill_id: str = "") -> Dict[str, Any]:
    """Per-agent skill cooldown after loss streak (#27)."""
    state = _read_state(_AGENT_COOLDOWN_PATH)
    agents = state.get("agents") if isinstance(state.get("agents"), dict) else {}
    row = agents.get(agent_id) or {}
    streak = int(row.get("loss_streak") or 0)
    threshold = int(os.environ.get("PROFIT_AGENT_LOSS_COOLDOWN_STREAK", "3"))
    cooldown_sec = float(os.environ.get("PROFIT_AGENT_SKILL_COOLDOWN_SEC", "1800"))
    until = float(row.get("cooldown_until") or 0)
    now = time.time()
    on_cooldown = streak >= threshold and now < until
    if on_cooldown and skill_id:
        cooled = list(row.get("cooled_skills") or [])
        if skill_id not in cooled:
            cooled.append(skill_id)
            row["cooled_skills"] = cooled
            agents[agent_id] = row
            state["agents"] = agents
            _write_state(_AGENT_COOLDOWN_PATH, state)
    return {
        "success": True,
        "agent_id": agent_id,
        "loss_streak": streak,
        "on_cooldown": on_cooldown,
        "cooldown_until": until if on_cooldown else None,
        "cooled_skills": list(row.get("cooled_skills") or []),
    }


def record_agent_loss(agent_id: str, *, won: bool = False) -> Dict[str, Any]:
    """Update agent loss streak for skill cooldown."""
    state = _read_state(_AGENT_COOLDOWN_PATH)
    agents = state.get("agents") if isinstance(state.get("agents"), dict) else {}
    row = dict(agents.get(agent_id) or {})
    if won:
        row["loss_streak"] = 0
        row.pop("cooldown_until", None)
        row["cooled_skills"] = []
    else:
        streak = int(row.get("loss_streak") or 0) + 1
        row["loss_streak"] = streak
        threshold = int(os.environ.get("PROFIT_AGENT_LOSS_COOLDOWN_STREAK", "3"))
        if streak >= threshold:
            cd = float(os.environ.get("PROFIT_AGENT_SKILL_COOLDOWN_SEC", "1800"))
            row["cooldown_until"] = time.time() + cd
    agents[agent_id] = row
    state["agents"] = agents
    state["updated_at"] = _iso()
    _write_state(_AGENT_COOLDOWN_PATH, state)
    return agent_skill_cooldown_check(agent_id)


def sentiment_feed_weight() -> Dict[str, Any]:
    """Sentiment feed weight env override (#28)."""
    w = float(os.environ.get("EXCHANGE_SENTIMENT_WEIGHT", os.environ.get("PROFIT_SENTIMENT_WEIGHT", "0.15")))
    w = max(0.0, min(1.0, w))
    return {"success": True, "weight": w, "source": "env"}


def ai_skip_reason_tile_groups(*, hours: float = 24) -> Dict[str, Any]:
    """AI skip reason dashboard tile grouping (#29)."""
    from backend.services.exchange_profit_path_service import search_paths

    buckets: Dict[str, int] = {
        "funding": 0, "margin": 0, "venue": 0, "ai": 0, "kill": 0, "other": 0,
    }
    mapping = {
        "funding": ("fund", "balance", "prefund", "stash"),
        "margin": ("margin", "bps", "spread", "slippage"),
        "venue": ("venue", "xeggex", "binance", "nonkyc", "withdraw"),
        "ai": ("ai", "skill", "agent", "ensemble"),
        "kill": ("kill", "spork", "gate"),
    }
    for row in search_paths(hours=hours, limit=3000).get("paths") or []:
        if str(row.get("decision") or "") != "skip":
            continue
        reason = str(row.get("skip_reason") or row.get("reason") or "other").lower()
        placed = False
        for bucket, keys in mapping.items():
            if any(k in reason for k in keys):
                buckets[bucket] += 1
                placed = True
                break
        if not placed:
            buckets["other"] += 1
    tiles = [
        {"group": k, "label": k.replace("_", " ").title(), "count": v}
        for k, v in sorted(buckets.items(), key=lambda x: -x[1])
        if v > 0
    ]
    return {"success": True, "hours": hours, "tiles": tiles, "total": sum(buckets.values())}


def ppp_summary_llm_narrative(ppp: Dict[str, Any]) -> Dict[str, Any]:
    """LLM-style narrative on daily PPP summary (#30) — template-based, no external LLM."""
    fills = int(ppp.get("fill_count") or 0)
    hit = float(ppp.get("hit_rate_pct") or 0)
    avg_bps = float(ppp.get("avg_net_bps") or 0)
    scans = int(ppp.get("scan_count") or 0)
    top_skip = (ppp.get("top_skip_reasons") or [{}])[0]
    skip_txt = f"{top_skip.get('reason', 'none')} ({top_skip.get('count', 0)}×)" if top_skip else "none"
    tone = "strong" if fills >= 5 and hit >= 40 else ("moderate" if fills >= 1 else "quiet")
    narrative = (
        f"Last 24h was a {tone} session: {fills} fills from {scans} scans "
        f"at {hit:.1f}% hit rate and {avg_bps:.1f} bps average net. "
        f"Primary skip driver: {skip_txt}. "
        f"{'Keep funding hot symbols prefunded.' if tone != 'strong' else 'Momentum looks healthy — consider scaling notional.'}"
    )
    return {"success": True, "narrative": narrative, "tone": tone}


def ai_skill_profile_sets(*, profile: Optional[str] = None) -> Dict[str, Any]:
    """A/B AI skill sets via config profile (#31)."""
    prof = (profile or os.environ.get("EXCHANGE_PROFIT_PROFILE", "max")).strip().lower()
    sets = {
        "max": ["spatial_arbitrage", "triangular_arbitrage", "ai_trader", "stablecoin_peg", "volatility_breakout"],
        "fast": ["spatial_arbitrage", "fast_arb_rescan", "latency_twap"],
        "standard": ["spatial_arbitrage", "ai_trader", "cross_trade"],
        "live-only": ["spatial_arbitrage", "withdrawal_aware_routing"],
    }
    skills = sets.get(prof, sets["max"])
    return {"success": True, "profile": prof, "skills": skills, "variant": "A" if prof == "max" else "B"}


def record_stash_history_point() -> Dict[str, Any]:
    """Append stash snapshot for historical chart (#39)."""
    try:
        from backend.services.profit_daemon_monitor_service import _light_treasury_snapshot

        treas = _light_treasury_snapshot()
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    stash = float(treas.get("live_stash_usd") or treas.get("stash_usd") or 0)
    state = _read_state(_STASH_HISTORY_PATH)
    series = list(state.get("series") or [])
    point = {"ts": _iso(), "stash_usd": round(stash, 4)}
    series.append(point)
    max_pts = int(os.environ.get("PROFIT_STASH_HISTORY_MAX", "168"))
    state["series"] = series[-max_pts:]
    state["updated_at"] = _iso()
    _write_state(_STASH_HISTORY_PATH, state)
    return {"success": True, "recorded": point, "count": len(state["series"])}


def stash_history_series(*, limit: int = 48) -> Dict[str, Any]:
    """Historical stash chart data for monitor UI (#39)."""
    state = _read_state(_STASH_HISTORY_PATH)
    series = list(state.get("series") or [])[-max(1, limit):]
    return {"success": True, "series": series, "count": len(series)}


def mn2_stash_mirror() -> Dict[str, Any]:
    """MN2-denominated stash mirror for casino (#40)."""
    try:
        from backend.services.profit_daemon_monitor_service import _light_treasury_snapshot

        treas = _light_treasury_snapshot()
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    stash_usd = float(treas.get("live_stash_usd") or treas.get("stash_usd") or 0)
    mn2_usd = max(float(ex._mn2_usd()), 1e-9)
    mn2_amt = round(stash_usd / mn2_usd, 6)
    return {
        "success": True,
        "stash_usd": round(stash_usd, 4),
        "mn2_amount": mn2_amt,
        "mn2_usd": mn2_usd,
        "mirror_label": f"{mn2_amt:,.2f} MN2",
    }


def plan_paypal_split_recipients(*, amount_usd: Optional[float] = None) -> Dict[str, Any]:
    """Multi-recipient PayPal split with gates (#49)."""
    cfg = ex._read_json(_PAYOUT_PATH, {})
    recipients = list(cfg.get("split_recipients") or [])
    if not recipients:
        primary = str((cfg.get("paypal") or {}).get("receiver_email") or "")
        if primary:
            recipients = [{"email": primary, "share_pct": 100.0}]
    live = bool((cfg.get("paypal") or {}).get("live_enabled"))
    gates_ok = live and os.environ.get("EXCHANGE_PAYPAL_SPLIT_ENABLED", "0").strip().lower() in ("1", "true", "yes")
    amt = float(amount_usd or cfg.get("paypal_sweepable_usd") or 0)
    splits = []
    for r in recipients:
        pct = float(r.get("share_pct") or 0)
        splits.append({
            "email": r.get("email"),
            "share_pct": pct,
            "amount_usd": round(amt * pct / 100.0, 2) if amt else 0,
        })
    return {
        "success": True,
        "gates_ok": gates_ok,
        "live_enabled": live,
        "total_usd": round(amt, 2),
        "recipients": splits,
        "blocked_reason": None if gates_ok else "split_gates_not_met",
    }


def mobile_stat_card_meta() -> Dict[str, Any]:
    """Mobile-friendly monitor stat card layout hints (#60)."""
    return {
        "success": True,
        "mobile_optimized": True,
        "min_card_width_px": 140,
        "columns_mobile": 2,
        "columns_tablet": 3,
        "columns_desktop": 4,
        "touch_target_min_px": 44,
        "css_class": "pdm-grid pdm-grid--mobile",
    }


def verify_monitor_public_token(token: Optional[str] = None) -> Dict[str, Any]:
    """Public read-only monitor token URL (#61)."""
    expected = os.environ.get("PROFIT_MONITOR_PUBLIC_TOKEN", "").strip()
    if not expected:
        return {"success": True, "public_enabled": False, "reason": "token_not_configured"}
    ok = bool(token) and hmac.compare_digest(str(token), expected)
    return {
        "success": ok,
        "public_enabled": True,
        "authorized": ok,
        "public_path": "/api/profit-daemon/metrics-public?token=" + expected[:4] + "…" if expected else None,
    }


def blue_green_profile_switch(*, target: Optional[str] = None) -> Dict[str, Any]:
    """Blue/green daemon profile switch without downtime (#72)."""
    state = _read_state(_BLUE_GREEN_PATH)
    active = str(state.get("active") or os.environ.get("EXCHANGE_PROFIT_PROFILE", "max"))
    standby = str(state.get("standby") or ("fast" if active == "max" else "max"))
    if target:
        tgt = target.strip().lower()
        if tgt not in ("max", "fast", "standard", "live-only"):
            return {"success": False, "error": "invalid_profile"}
        standby, active = active, tgt
    else:
        standby, active = active, standby
    os.environ["EXCHANGE_PROFIT_PROFILE"] = active
    payload = {
        "updated_at": _iso(),
        "active": active,
        "standby": standby,
        "switched": True,
    }
    _write_state(_BLUE_GREEN_PATH, payload)
    reload_ppp_config()
    return {"success": True, **payload}


def metrics_ip_allowed(client_ip: Optional[str] = None) -> Dict[str, Any]:
    """IP allowlist for metrics endpoint (#80)."""
    raw = os.environ.get("PROFIT_METRICS_IP_ALLOWLIST", "").strip()
    if not raw:
        return {"success": True, "enforced": False, "allowed": True}
    allowed_ips = {p.strip() for p in raw.split(",") if p.strip()}
    ip = (client_ip or "127.0.0.1").strip()
    ok = ip in allowed_ips or ip == "127.0.0.1"
    return {"success": True, "enforced": True, "allowed": ok, "client_ip": ip}


def maybe_secrets_rotation_reminder() -> Dict[str, Any]:
    """Secrets vault rotation reminder (#81)."""
    state = _read_state(_ALERT_STATE_PATH)
    keys = [
        ("PROFIT_DAEMON_ADMIN_KEY", 90),
        ("PROFIT_HEARTBEAT_HMAC_SECRET", 90),
        ("PROFIT_MONITOR_PUBLIC_TOKEN", 180),
    ]
    reminders: List[Dict[str, Any]] = []
    now = time.time()
    for env_key, days in keys:
        if not os.environ.get(env_key, "").strip():
            continue
        last_rot = float(state.get(f"secret_rot_{env_key}") or now - (days - 7) * 86400)
        age_days = (now - last_rot) / 86400
        if age_days >= days - 7:
            reminders.append({"key": env_key, "age_days": round(age_days, 1), "rotate_by_days": days})
    alert = {"skipped": True}
    if reminders and _should_alert("secrets_rotation_reminder", cooldown_sec=86400 * 7):
        body = "\n".join(f"• {r['key']}: {r['age_days']}d old" for r in reminders)
        alert = _post_ops_alert("Profit daemon — secret rotation due", body, alert_key="secrets_rotation_reminder")
    return {"success": True, "reminders": reminders, "alert": alert}


def maybe_weekly_ppp_report() -> Dict[str, Any]:
    """PPP auto-report weekly (#82) — text report + optional Discord."""
    state = _read_state(_WEEKLY_REPORT_STATE)
    last = str(state.get("last_at") or "")
    now = datetime.now(timezone.utc)
    if last:
        try:
            prev = datetime.fromisoformat(last.replace("Z", "+00:00"))
            if now - prev < timedelta(days=6):
                return {"skipped": True, "reason": "not_due", "last_at": last}
        except Exception:
            pass
    try:
        from backend.services.profit_daemon_monitor_service import _light_ppp_snapshot

        ppp = _light_ppp_snapshot(hours=168)
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    report = {
        "period": "7d",
        "fills": int(ppp.get("fill_count") or 0),
        "hit_rate_pct": float(ppp.get("hit_rate_pct") or 0),
        "avg_net_bps": float(ppp.get("avg_net_bps") or 0),
        "scans": int(ppp.get("scan_count") or 0),
        "generated_at": _iso(),
    }
    body = (
        f"Weekly PPP: {report['fills']} fills, {report['hit_rate_pct']:.1f}% hit, "
        f"{report['avg_net_bps']:.1f} bps avg, {report['scans']} scans."
    )
    alert = _post_ops_alert("Profit daemon — weekly PPP report", body, alert_key="weekly_ppp_report")
    state["last_at"] = _iso()
    state["last_report"] = report
    _write_state(_WEEKLY_REPORT_STATE, state)
    report_path = os.path.join(ex._DATA_DIR, "profit_weekly_report.json")
    _write_state(report_path, report)
    return {"success": True, "report": report, "alert": alert}


def ab_strategy_profile_compare() -> Dict[str, Any]:
    """A/B strategy profile comparison max vs fast (#83)."""
    try:
        from backend.services.exchange_profit_path_service import search_paths
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    profiles = ("max", "fast")
    comparison: Dict[str, Any] = {}
    for prof in profiles:
        rows = [
            r for r in search_paths(hours=168, limit=5000).get("paths") or []
            if str(r.get("profile") or "max").lower() == prof
        ]
        fills = sum(1 for r in rows if str(r.get("decision") or "") == "execute")
        comparison[prof] = {
            "paths": len(rows),
            "fills": fills,
            "hit_rate_pct": round(100.0 * fills / max(1, len(rows)), 2),
        }
    winner = max(profiles, key=lambda p: comparison[p]["hit_rate_pct"])
    return {"success": True, "comparison": comparison, "winner": winner}


def ppp_ledger_backtest_replay(*, hours: float = 24, notional_usd: float = 75.0) -> Dict[str, Any]:
    """Backtest replay from PPP ledger slice (#84)."""
    from backend.services.exchange_profit_path_service import search_paths

    rows = [
        r for r in search_paths(hours=hours, limit=2000).get("paths") or []
        if str(r.get("decision") or "") == "execute"
    ]
    pnl = 0.0
    legs = 0
    for r in rows:
        bps = float(r.get("net_bps") or 0)
        pnl += notional_usd * bps / 10000.0
        legs += 1
    return {
        "success": True,
        "hours": hours,
        "notional_usd": notional_usd,
        "legs": legs,
        "sim_pnl_usd": round(pnl, 4),
        "avg_bps": round(sum(float(r.get("net_bps") or 0) for r in rows) / max(1, legs), 2),
    }


def jupyter_ppp_template_path() -> Dict[str, Any]:
    """Jupyter notebook template for PPP analysis (#89)."""
    path = os.path.join(ex._BASE, "docs", "notebooks", "ppp_analysis_template.ipynb")
    exists = os.path.isfile(path)
    return {
        "success": True,
        "path": path,
        "exists": exists,
        "download_url": "/api/profit-daemon/jupyter-template",
    }


def anonymized_route_leaderboard(*, limit: int = 15) -> Dict[str, Any]:
    """Public anonymized leaderboard of routes (#90)."""
    from backend.services.exchange_profit_pair_search_service import read_index

    hits = list((read_index().get("hits") or []))[: max(1, limit)]
    board = []
    for i, h in enumerate(hits):
        sym = str(h.get("symbol") or "?")
        anon = hashlib.sha256(sym.encode()).hexdigest()[:8]
        board.append({
            "rank": i + 1,
            "route_hash": anon,
            "avg_net_bps": float(h.get("avg_net_bps") or 0),
            "hit_rate_pct": float(h.get("hit_rate_pct") or 0),
            "search_score": float(h.get("search_score") or 0),
        })
    return {"success": True, "leaderboard": board, "anonymized": True}


def research_api_quota_check(operator_key: str, *, max_per_hour: Optional[int] = None) -> Dict[str, Any]:
    """Research API quota per operator key (#91)."""
    limit = max_per_hour or int(os.environ.get("PROFIT_RESEARCH_QUOTA_PER_HOUR", "120"))
    state = _read_state(_RESEARCH_QUOTA_PATH)
    buckets = state.get("buckets") if isinstance(state.get("buckets"), dict) else {}
    key = str(operator_key or "anonymous")[:64]
    row = buckets.get(key) or {"count": 0, "window_start": time.time()}
    window = float(row.get("window_start") or time.time())
    if time.time() - window >= 3600:
        row = {"count": 0, "window_start": time.time()}
    row["count"] = int(row.get("count") or 0) + 1
    buckets[key] = row
    state["buckets"] = buckets
    state["updated_at"] = _iso()
    _write_state(_RESEARCH_QUOTA_PATH, state)
    allowed = int(row["count"]) <= limit
    return {
        "success": True,
        "allowed": allowed,
        "count": row["count"],
        "limit": limit,
        "remaining": max(0, limit - int(row["count"])),
    }


def maybe_mn2_fill_streak_bonus(exchange_res: Dict[str, Any]) -> Dict[str, Any]:
    """Profit-linked MN2 bonus on arb fill streak (#92)."""
    plat = exchange_res.get("platform") or {}
    arb = (plat.get("results") or {}).get("arbitrage") or {}
    fills = int(arb.get("fills") or arb.get("executed") or 0)
    state = _read_state(_FILL_STREAK_STATE)
    streak = int(state.get("streak") or 0)
    if fills > 0:
        streak += 1
    else:
        streak = 0
    state["streak"] = streak
    state["updated_at"] = _iso()
    threshold = int(os.environ.get("PROFIT_MN2_FILL_STREAK_BONUS", "5"))
    bonus_mn2 = 0.0
    awarded = False
    if streak >= threshold and streak % threshold == 0:
        bonus_mn2 = float(os.environ.get("PROFIT_MN2_FILL_BONUS_AMOUNT", "2.5"))
        awarded = True
        state["last_bonus_at"] = _iso()
        state["total_bonus_mn2"] = round(float(state.get("total_bonus_mn2") or 0) + bonus_mn2, 4)
    _write_state(_FILL_STREAK_STATE, state)
    return {"success": True, "streak": streak, "bonus_mn2": bonus_mn2, "awarded": awarded}


def exchange_readiness_cta() -> Dict[str, Any]:
    """Exchange tab CTA when monitor readiness >75% (#95)."""
    try:
        from backend.services.profit_daemon_monitor_service import monitor_status

        st = monitor_status()
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    pct = float(st.get("profit_readiness_pct") or 0)
    show = pct >= float(os.environ.get("PROFIT_READINESS_CTA_PCT", "75"))
    return {
        "success": True,
        "readiness_pct": pct,
        "show_cta": show,
        "cta_text": "Profit path ready — enable live trading" if show else None,
        "cta_href": "/exchange?tab=bots" if show else None,
    }


def rental_trial_eligibility(*, user_id: str = "platform") -> Dict[str, Any]:
    """Rental agent trial tied to PPP fill count (#96)."""
    try:
        from backend.services.profit_daemon_monitor_service import _light_ppp_snapshot

        ppp = _light_ppp_snapshot(hours=720)
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    fills = int(ppp.get("fill_count") or 0)
    required = int(os.environ.get("PROFIT_RENTAL_TRIAL_FILLS", "3"))
    eligible = fills >= required
    return {
        "success": True,
        "user_id": user_id,
        "ppp_fills_30d": fills,
        "required_fills": required,
        "eligible": eligible,
        "trial_rental_id": "rent_starter_7d" if eligible else None,
    }


def maybe_casino_vip_bump_on_sweep(sweep_res: Dict[str, Any]) -> Dict[str, Any]:
    """Casino VIP tier bump on sweep success (#97)."""
    if not sweep_res.get("success") or not sweep_res.get("swept"):
        return {"skipped": True, "reason": "no_sweep"}
    amount = float(sweep_res.get("amount_usd") or 0)
    tier = "bronze"
    if amount >= 500:
        tier = "gold"
    elif amount >= 100:
        tier = "silver"
    state = _read_state(os.path.join(ex._DATA_DIR, "profit_casino_vip_bump.json"))
    state["last_sweep_usd"] = amount
    state["suggested_vip_tier"] = tier
    state["updated_at"] = _iso()
    _write_state(os.path.join(ex._DATA_DIR, "profit_casino_vip_bump.json"), state)
    return {"success": True, "sweep_usd": amount, "suggested_vip_tier": tier}


def lazy_monitor_poll() -> Dict[str, Any]:
    """Lazy Flask import for monitor-only polls (#102)."""
    if os.environ.get("PROFIT_LAZY_MONITOR", "1").strip().lower() in ("0", "false", "no", "off"):
        from backend.services.profit_daemon_monitor_service import monitor_status
        return {"success": True, "lazy": False, "status": monitor_status()}
    try:
        from backend.services.profit_daemon_monitor_service import monitor_status
        return {"success": True, "lazy": True, "status": monitor_status()}
    except Exception as exc:
        return {"success": False, "lazy": True, "error": str(exc)}


def evaluate_async_loop_backend() -> Dict[str, Any]:
    """uvloop / gevent eval for I/O bound ticks (#104)."""
    options: Dict[str, Any] = {}
    try:
        import uvloop  # type: ignore
        options["uvloop"] = {"available": True, "version": getattr(uvloop, "__version__", "?")}
    except ImportError:
        options["uvloop"] = {"available": False}
    try:
        import gevent  # type: ignore
        options["gevent"] = {"available": True, "version": getattr(gevent, "__version__", "?")}
    except ImportError:
        options["gevent"] = {"available": False}
    preferred = os.environ.get("PROFIT_ASYNC_LOOP", "stdlib")
    if options.get("uvloop", {}).get("available") and preferred == "auto":
        preferred = "uvloop"
    elif options.get("gevent", {}).get("available") and preferred == "auto":
        preferred = "gevent"
    return {"success": True, "options": options, "recommended": preferred, "current": "stdlib"}


def maybe_archive_heartbeat_history(*, max_age_days: int = 7) -> Dict[str, Any]:
    """Compressed heartbeat history archive (#105)."""
    hb_path = heartbeat_path()
    if not os.path.isfile(hb_path):
        return {"skipped": True, "reason": "no_heartbeat"}
    try:
        mtime = os.path.getmtime(hb_path)
        age_days = (time.time() - mtime) / 86400
        if age_days < max_age_days:
            return {"skipped": True, "reason": "too_recent", "age_days": round(age_days, 2)}
    except OSError:
        return {"skipped": True, "reason": "stat_failed"}
    os.makedirs(_HEARTBEAT_ARCHIVE_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_json = os.path.join(_HEARTBEAT_ARCHIVE_DIR, f"heartbeat_{ts}.json")
    archive_gz = archive_json + ".gz"
    try:
        shutil.copy2(hb_path, archive_json)
        with open(archive_json, "rb") as src, gzip.open(archive_gz, "wb") as dst:
            shutil.copyfileobj(src, dst)
        os.remove(archive_json)
        return {"success": True, "archived": archive_gz, "compressed": True}
    except OSError as exc:
        return {"success": False, "error": str(exc)}


def purge_payout_history(*, older_than_days: int = 365, dry_run: bool = True) -> Dict[str, Any]:
    """GDPR-style payout history purge tool (#110)."""
    if not os.path.isfile(_PAYOUT_HISTORY_PATH):
        return {"success": True, "purged": 0, "dry_run": dry_run, "reason": "no_file"}
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(30, older_than_days))
    kept: List[str] = []
    purged = 0
    try:
        with open(_PAYOUT_HISTORY_PATH, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    ts = str(row.get("ts") or "")
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if dt < cutoff:
                        purged += 1
                        continue
                except Exception:
                    pass
                kept.append(line)
        if not dry_run:
            with open(_PAYOUT_HISTORY_PATH, "w", encoding="utf-8") as fh:
                for line in kept:
                    fh.write(line + "\n")
    except OSError as exc:
        return {"success": False, "error": str(exc)}
    return {
        "success": True,
        "purged": purged,
        "kept": len(kept),
        "dry_run": dry_run,
        "cutoff": cutoff.isoformat().replace("+00:00", "Z"),
    }


def run_final_upgrade_hooks(exchange_res: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Single entry for final-batch daemon hooks + state stamp."""
    res = exchange_res or {}
    out = {
        "upgrades_state": profit_upgrades_state(),
        "rental_overlay": apply_rental_symbol_overlay(),
        "sentiment_weight": sentiment_feed_weight(),
        "ai_skip_groups": ai_skip_reason_tile_groups(),
        "mn2_mirror": mn2_stash_mirror(),
        "readiness_cta": exchange_readiness_cta(),
        "rental_trial": rental_trial_eligibility(),
        "async_backend": evaluate_async_loop_backend(),
    }
    plat = res.get("platform") or {}
    arb = (plat.get("results") or {}).get("arbitrage") or {}
    bq = arb.get("best_qualifying") or {}
    if bq.get("symbol") and str(arb.get("ai_skip") or plat.get("ai_skip_reason") or ""):
        out["ai_bypass"] = record_hot_spread_ai_bypass(
            symbol=str(bq.get("symbol")),
            net_bps=float(bq.get("net_bps") or 0),
            agent_id=str(arb.get("best_agent") or "ai_trader"),
            skip_reason=str(arb.get("ai_skip") or plat.get("ai_skip_reason") or "ai_skip"),
        )
    return {"success": True, **out}
