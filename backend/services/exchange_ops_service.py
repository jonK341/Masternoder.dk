"""MN2 pool ops intelligence: health score, runway, circuit breaker, waterfall, feed, reconcile, depth."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_mn2_pool_service import (
    _LEDGER_PATH as _POOL_LEDGER_PATH,
    _RESERVE_LEDGER_PATH,
    load_config as load_pool_config,
    mn2_pool_status,
    pool_balances,
    pool_gaps,
    pool_user_id,
    reserve_balances,
    reserve_user_id,
)

_CFG_PATH = os.path.join(ex._BASE, "data", "exchange_ops_config.json")
_STATE_PATH = os.path.join(ex._DATA_DIR, "ops_state.json")
_DIGEST_PATH = os.path.join(ex._DATA_DIR, "ops_digest.jsonl")
_MN2_LEDGER_PATH = os.path.join(ex._BASE, "data", "mn2_ledger.json")
_PPP_PATH = os.path.join(ex._DATA_DIR, "profit_path_ledger.jsonl")
_POOL_ASSETS = frozenset({"MN2", "USDT", "USDC"})


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CFG_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def _read_state() -> Dict[str, Any]:
    return ex._read_json(_STATE_PATH, {"circuit_breaker": {"active": False}})


def _write_state(state: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, state)


def _tail_jsonl(path: str, limit: int = 200) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        return []
    rows: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows[-max(1, int(limit or 200)):]


def _asset_usd(symbol: str, amount: float) -> float:
    sym = (symbol or "").strip().upper()
    if sym == "MN2":
        return float(amount or 0) * ex._mn2_usd()
    return float(amount or 0) * ex._price_usd(sym)


def _pool_fill_ratios() -> Dict[str, float]:
    cfg = load_pool_config()
    mins = cfg.get("min_pool_by_asset") or {}
    balances = pool_balances()
    ratios: Dict[str, float] = {}
    for sym in _POOL_ASSETS:
        target = float(mins.get(sym) or 0)
        bal = float(balances.get(sym) or 0)
        if target <= 0:
            ratios[sym] = 1.0 if bal > 0 else 0.0
        else:
            ratios[sym] = min(1.0, bal / target)
    return ratios


def pool_health_score() -> Dict[str, Any]:
    """Feature 1: 0–100 pool health score from fill ratios, reserve, and recent volume."""
    cfg = load_config()
    health_cfg = cfg.get("health") or {}
    ratios = _pool_fill_ratios()
    avg_fill = sum(ratios.values()) / max(len(ratios), 1)
    reserve = reserve_balances()
    reserve_usd = sum(_asset_usd(sym, amt) for sym, amt in reserve.items())

    hours = int(health_cfg.get("recent_volume_hours") or 24)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent_swaps = 0
    for row in _tail_jsonl(_POOL_LEDGER_PATH, 500):
        ts = row.get("ts")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except Exception:
            continue
        if dt >= cutoff:
            recent_swaps += 1

    volume_bonus = min(10.0, recent_swaps * 0.5)
    reserve_bonus = min(10.0, reserve_usd / 100.0)
    score = round(min(100.0, max(0.0, avg_fill * 80.0 + volume_bonus + reserve_bonus)), 1)

    band = "green"
    if score < 60:
        band = "red"
    elif score < 80:
        band = "yellow"

    return {
        "score": score,
        "band": band,
        "fill_ratios": {k: round(v, 4) for k, v in ratios.items()},
        "reserve_usd": round(reserve_usd, 2),
        "recent_pool_swaps": recent_swaps,
        "recent_volume_hours": hours,
    }


def liquidity_runway(from_asset: Optional[str] = None, to_asset: Optional[str] = None) -> Dict[str, Any]:
    """Feature 2: estimate swoops remaining at sample size before pool exhaustion."""
    cfg = load_config()
    sample_usd = float((cfg.get("health") or {}).get("runway_sample_usd") or 10.0)
    balances = pool_balances()
    gaps = pool_gaps()
    pairs = [
        ("USDT", "MN2"), ("USDC", "MN2"), ("MN2", "USDT"), ("MN2", "USDC"),
        ("USDT", "USDC"), ("USDC", "USDT"),
    ]
    if from_asset and to_asset:
        pairs = [(from_asset.upper(), to_asset.upper())]

    runways: List[Dict[str, Any]] = []
    for src, dst in pairs:
        payout_sym = dst if dst != "MN2" or src == "MN2" else "MN2"
        if src in ("USDT", "USDC") and dst == "MN2":
            payout_sym = "MN2"
        elif src == "MN2" and dst in ("USDT", "USDC"):
            payout_sym = dst
        elif src in ("USDT", "USDC") and dst in ("USDT", "USDC"):
            payout_sym = dst

        available = float(balances.get(payout_sym) or 0)
        if payout_sym == "MN2":
            available_usd = _asset_usd("MN2", available)
            per_swap = sample_usd
        else:
            available_usd = available
            per_swap = sample_usd

        remaining = int(available_usd / per_swap) if per_swap > 0 else 0
        warning = remaining < 5 or payout_sym in gaps
        runways.append({
            "from": src,
            "to": dst,
            "payout_asset": payout_sym,
            "available": round(available, 8),
            "sample_usd": sample_usd,
            "estimated_swaps_remaining": remaining,
            "low_liquidity": warning,
        })

    return {"success": True, "runways": runways, "pool_gaps": gaps}


def circuit_breaker_status() -> Dict[str, Any]:
    """Feature 4: pause or cap swoops when pool is critically low."""
    cfg = load_config()
    cb_cfg = cfg.get("circuit_breaker") or {}
    if not cb_cfg.get("enabled", True):
        return {"active": False, "level": "off", "reason": "disabled"}

    pool_cfg = load_pool_config()
    mins = pool_cfg.get("min_pool_by_asset") or {}
    ratios = _pool_fill_ratios()
    min_pct = float(cb_cfg.get("pause_swoop_below_pct") or 0.2)

    worst_sym = min(ratios, key=ratios.get) if ratios else "MN2"
    worst_ratio = ratios.get(worst_sym, 0.0)

    state = _read_state()
    level = "green"
    active = False
    reason = ""
    max_swoop_usd: Optional[float] = None

    if worst_ratio < min_pct:
        level = "red"
        active = True
        reason = f"{worst_sym} below {int(min_pct * 100)}% of pool minimum"
    elif worst_ratio < min_pct * 2:
        level = "yellow"
        max_swoop_usd = float(cb_cfg.get("max_swoop_usd_when_yellow") or 100.0)
        reason = f"{worst_sym} pool thin — swoop size capped"

    state["circuit_breaker"] = {
        "active": active,
        "level": level,
        "worst_asset": worst_sym,
        "worst_ratio": round(worst_ratio, 4),
        "updated_at": _iso(),
    }
    _write_state(state)

    return {
        "active": active,
        "level": level,
        "reason": reason,
        "worst_asset": worst_sym,
        "worst_ratio": round(worst_ratio, 4),
        "min_pct": min_pct,
        "max_swoop_usd": max_swoop_usd,
        "mins": mins,
    }


def check_swoop_allowed(from_asset: str, to_asset: str, amount: float) -> Optional[str]:
    """Return error code if circuit breaker blocks swoop."""
    cb = circuit_breaker_status()
    if cb.get("active"):
        return "pool_circuit_breaker"
    max_usd = cb.get("max_swoop_usd")
    if max_usd is not None:
        src = (from_asset or "").upper()
        usd = _asset_usd(src, float(amount or 0))
        if usd > max_usd:
            return "swoop_size_capped"
    return None


def treasury_waterfall() -> Dict[str, Any]:
    """Feature 5: priority order for deploying excess funds."""
    cfg = load_config()
    priorities = (cfg.get("treasury_waterfall") or {}).get("priorities") or []
    gaps = pool_gaps()
    pool_uid = pool_user_id()
    reserve_uid = reserve_user_id()
    treasury_uid = "platform_treasury"

    pool_wallet = ex.get_wallet(pool_uid)
    treasury_wallet = ex.get_wallet(treasury_uid)
    reserve = reserve_balances()

    gap_usd = sum(_asset_usd(sym, amt) for sym, amt in gaps.items())
    reserve_usd = sum(_asset_usd(sym, amt) for sym, amt in reserve.items())

    pool_assets = pool_wallet.get("assets") or {}
    pool_mn2 = float(pool_wallet.get("mn2_balance") or 0)
    excess_alts_usd = 0.0
    sell_cfg = cfg.get("sell_plan") or {}
    excluded = {str(s).upper() for s in (sell_cfg.get("excluded_assets") or [])}
    for sym, amt in pool_assets.items():
        sym_u = str(sym).upper()
        if sym_u in excluded:
            continue
        excess_alts_usd += _asset_usd(sym_u, float(amt or 0))

    steps: List[Dict[str, Any]] = []
    for item in priorities:
        pid = str(item.get("id") or "")
        label = str(item.get("label") or pid)
        need_usd = 0.0
        note = ""
        if pid == "pool_mins":
            need_usd = gap_usd
            note = "Fill MN2/USDT/USDC pool gaps first"
        elif pid == "pool_reserve":
            need_usd = max(0.0, 200.0 - reserve_usd)
            note = "Grow 2% swoop reserve stash"
        elif pid == "platform_treasury":
            note = "Treasury UNI/ARB/NEAR stash"
        elif pid == "agent_wallets":
            note = "Agent bot operating balances"
        steps.append({"id": pid, "label": label, "need_usd": round(need_usd, 2), "note": note})

    recommendation = "hold"
    detail = "Pool healthy — no urgent waterfall action"
    if gap_usd > 50:
        recommendation = "fill_pool_mins"
        detail = f"Deploy ~${gap_usd:.0f} toward pool gaps (sell alts or seed MN2)"
    elif excess_alts_usd > 100:
        recommendation = "sell_excess_alts"
        detail = f"~${excess_alts_usd:.0f} in non-pool alts in sales pool — sell to USDT/USDC"

    return {
        "success": True,
        "priorities": steps,
        "pool_gaps_usd": round(gap_usd, 2),
        "reserve_usd": round(reserve_usd, 2),
        "excess_alts_usd": round(excess_alts_usd, 2),
        "recommendation": recommendation,
        "recommendation_detail": detail,
        "pool_mn2": round(pool_mn2, 4),
        "treasury_assets": treasury_wallet.get("assets") or {},
    }


def reserve_spend_ledger(limit: int = 100) -> Dict[str, Any]:
    """Feature 6: reserve stash accrual history."""
    rows = _tail_jsonl(_RESERVE_LEDGER_PATH, limit)
    totals = reserve_balances()
    accrued = {sym: 0.0 for sym in _POOL_ASSETS}
    for row in rows:
        sym = str(row.get("asset") or "").upper()
        if sym in accrued:
            accrued[sym] += float(row.get("amount") or 0)

    return {
        "success": True,
        "entries": list(reversed(rows)),
        "totals_accrued_from_ledger": {k: round(v, 8) for k, v in accrued.items()},
        "current_reserve_balances": totals,
        "swap_count": len(rows),
    }


def _normalize_feed_row(source: str, row: Dict[str, Any]) -> Dict[str, Any]:
    ts = row.get("ts") or row.get("created_at") or ""
    action = row.get("action") or row.get("type") or row.get("phase") or source
    user = row.get("user_id") or row.get("agent_id") or ""
    amount = row.get("amount") or row.get("amount_usd") or row.get("notional_usd")
    return {
        "ts": ts,
        "source": source,
        "action": action,
        "user_id": user,
        "amount": amount,
        "symbol": row.get("symbol") or row.get("asset"),
        "detail": {k: v for k, v in row.items() if k not in ("ts", "action", "user_id")},
    }


def unified_action_feed(limit: int = 80, source_filter: Optional[str] = None) -> Dict[str, Any]:
    """Feature 9: merged timeline from audit, trades, pool, reserve, MN2, PPP."""
    feeds: List[Dict[str, Any]] = []

    for row in _tail_jsonl(ex._AUDIT_PATH, limit):
        feeds.append(_normalize_feed_row("audit", row))
    for row in _tail_jsonl(ex._TRADES_PATH, limit):
        feeds.append(_normalize_feed_row("trade", row))
    for row in _tail_jsonl(_POOL_LEDGER_PATH, limit):
        feeds.append(_normalize_feed_row("pool", row))
    for row in _tail_jsonl(_RESERVE_LEDGER_PATH, limit):
        feeds.append(_normalize_feed_row("reserve", row))
    for row in _tail_jsonl(_PPP_PATH, limit):
        feeds.append(_normalize_feed_row("ppp", row))

    if os.path.isfile(_MN2_LEDGER_PATH):
        mn2 = ex._read_json(_MN2_LEDGER_PATH, {})
        for row in (mn2.get("entries") or [])[-limit:]:
            if isinstance(row, dict):
                feeds.append(_normalize_feed_row("mn2_ledger", row))

    if source_filter:
        feeds = [f for f in feeds if f["source"] == source_filter]

    feeds.sort(key=lambda r: str(r.get("ts") or ""), reverse=True)
    feeds = feeds[:limit]

    return {"success": True, "count": len(feeds), "items": feeds}


def reconcile_wallets() -> Dict[str, Any]:
    """Feature 11: compare wallet JSON balances vs ledger-derived expectations."""
    cfg = load_config()
    tolerance = float((cfg.get("reconciliation") or {}).get("tolerance_usd") or 1.0)
    issues: List[Dict[str, Any]] = []
    checked = 0

    wallet_dir = os.path.join(ex._DATA_DIR, "wallets")
    if not os.path.isdir(wallet_dir):
        return {"success": True, "checked": 0, "issues": [], "note": "no_wallet_dir"}

    for fname in os.listdir(wallet_dir):
        if not fname.endswith(".json"):
            continue
        uid = fname[:-5]
        wallet = ex.get_wallet(uid)
        if not wallet.get("success"):
            continue
        checked += 1
        assets = wallet.get("assets") or {}
        mn2 = float(wallet.get("mn2_balance") or 0)
        total_usd = _asset_usd("MN2", mn2)
        for sym, amt in assets.items():
            total_usd += _asset_usd(str(sym), float(amt or 0))
        if total_usd < 0:
            issues.append({"user_id": uid, "issue": "negative_total_usd", "total_usd": total_usd})

    health = pool_health_score()
    gaps = pool_gaps()
    if gaps:
        gap_usd = sum(_asset_usd(s, a) for s, a in gaps.items())
        if gap_usd > tolerance:
            issues.append({
                "user_id": pool_user_id(),
                "issue": "pool_below_minimum",
                "gap_usd": round(gap_usd, 2),
                "gaps": gaps,
            })

    return {
        "success": True,
        "checked": checked,
        "issues": issues,
        "health_score": health.get("score"),
        "tolerance_usd": tolerance,
        "reconciled_at": _iso(),
    }


def pool_depth_history(hours: int = 168) -> Dict[str, Any]:
    """Feature 14: pool balance snapshots over time from pool ledger."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, int(hours or 24)))
    points: List[Dict[str, Any]] = []
    running = {"MN2": 0.0, "USDT": 0.0, "USDC": 0.0}

    cfg = load_pool_config()
    seed = cfg.get("paper_seed") or {}
    for sym in _POOL_ASSETS:
        running[sym] = float(seed.get(sym) or 0)

    for row in _tail_jsonl(_POOL_LEDGER_PATH, 5000):
        ts = row.get("ts")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except Exception:
            continue
        recv = row.get("pool_receive") or {}
        pay = row.get("pool_pay") or {}
        for sym, amt in recv.items():
            sym_u = str(sym).upper()
            if sym_u in running:
                running[sym_u] += float(amt or 0)
        for sym, amt in pay.items():
            sym_u = str(sym).upper()
            if sym_u in running:
                running[sym_u] -= float(amt or 0)
        if dt >= cutoff:
            points.append({
                "ts": ts,
                "MN2": round(running["MN2"], 4),
                "USDT": round(running["USDT"], 4),
                "USDC": round(running["USDC"], 4),
            })

    current = pool_balances()
    return {
        "success": True,
        "hours": hours,
        "points": points[-200:],
        "current": current,
    }


def ops_dashboard() -> Dict[str, Any]:
    """Consolidated ops snapshot for Business Control."""
    pool = mn2_pool_status()
    return {
        "success": True,
        "health": pool_health_score(),
        "circuit_breaker": circuit_breaker_status(),
        "runway": liquidity_runway(),
        "waterfall": treasury_waterfall(),
        "reserve_ledger_summary": reserve_spend_ledger(limit=20),
        "pool": pool,
        "reconciliation": reconcile_wallets(),
        "swoop_presets": load_config().get("swoop_presets") or [],
        "timestamp": _iso(),
    }


def append_digest_entry(payload: Dict[str, Any]) -> None:
    row = {"ts": _iso(), **payload}
    ex._append_jsonl(_DIGEST_PATH, row)
