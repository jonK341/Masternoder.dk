"""Profit daemon ops — alerts, kill-switch, hot-reload hooks, auto-tuning.

Wired from ``scripts/all_profit_daemons.py`` and monitor API — no separate process.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

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
    hb_path = os.path.join(ex._BASE, "logs", "daemon_all_profit_heartbeat.json")
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
    }
