"""Stuck inventory strategy — assets held too long on Binance / NonKYC without grid progress.

Scans spot balances, compares grid state (fills, age), recalculates grid / arb / rotation
options, and can merge winners into the grid bot multi-venue config.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.services import crypto_exchange_service as ex

_VENUES = ("binance", "nonkyc")
_STATE_PATH = os.path.join(ex._DATA_DIR, "stuck_inventory_state.json")
_CFG_PATH = os.path.join(ex._BASE, "data", "exchange_grid_bot_config.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_ts(ts: Any) -> Optional[datetime]:
    if not ts:
        return None
    try:
        s = str(ts).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def stuck_hours_threshold() -> float:
    raw = os.environ.get("EXCHANGE_STUCK_INVENTORY_HOURS", "72")
    try:
        return max(6.0, float(raw))
    except ValueError:
        return 72.0


def min_stuck_usd() -> float:
    raw = os.environ.get("EXCHANGE_STUCK_MIN_USD", "8")
    try:
        return max(1.0, float(raw))
    except ValueError:
        return 8.0


def _read_state() -> Dict[str, Any]:
    data = ex._read_json(_STATE_PATH, {})
    return data if isinstance(data, dict) else {}


def _write_state(data: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, data)


def _grid_state() -> Dict[str, Any]:
    from backend.services.exchange_grid_bot_service import _read_state as grid_read

    return grid_read()


def _venue_balances(venue: str) -> Dict[str, float]:
    from backend.services import exchange_venue_api_service as vapi

    if not vapi.venue_has_credentials(venue):
        return {}
    try:
        return vapi.parse_spot_balances(venue, dry_run=False) or {}
    except Exception:
        return {}


def _mid_usd(venue: str, asset: str) -> float:
    try:
        return float(ex._price_usd(asset) or 0)
    except Exception:
        return 0.0


def _asset_grid_row(venue: str, asset: str, st: Dict[str, Any]) -> Dict[str, Any]:
    key = f"{venue.upper()}:{asset.upper()}"
    row = st.get(key) if isinstance(st.get(key), dict) else {}
    return row or {}


def scan_stuck_assets(*, venues: Optional[List[str]] = None) -> Dict[str, Any]:
    """Find coins sitting on exchange wallets with little or no grid progress."""
    venues = [v.lower() for v in (venues or list(_VENUES)) if v]
    st = _grid_state()
    state = _read_state()
    first_seen = state.get("first_seen") if isinstance(state.get("first_seen"), dict) else {}
    now = datetime.now(timezone.utc)
    thr_h = stuck_hours_threshold()
    min_usd = min_stuck_usd()
    stuck: List[Dict[str, Any]] = []

    for venue in venues:
        bals = _venue_balances(venue)
        for asset, qty in (bals or {}).items():
            sym = str(asset or "").upper()
            if not sym or sym in ("USDT", "USDC", "USD", "BUSD", "EUR"):
                continue
            q = float(qty or 0)
            if q <= 0:
                continue
            mid = _mid_usd(venue, sym)
            usd = q * mid if mid > 0 else 0.0
            if usd < min_usd:
                continue
            g = _asset_grid_row(venue, sym, st)
            fills = int(g.get("fills") or 0)
            updated = _parse_ts(g.get("updated_at"))
            fs_key = f"{venue}:{sym}"
            if fs_key not in first_seen:
                first_seen[fs_key] = _iso()
            seen_at = _parse_ts(first_seen.get(fs_key)) or updated or now
            age_h = (now - seen_at).total_seconds() / 3600.0
            idle = fills == 0 and age_h >= thr_h
            slow = fills > 0 and age_h >= thr_h * 2 and float(g.get("realized_pnl_usd") or 0) <= 0
            if not idle and not slow:
                continue
            stuck.append({
                "venue": venue,
                "asset": sym,
                "qty": round(q, 8),
                "usd_est": round(usd, 2),
                "age_hours": round(age_h, 1),
                "grid_fills": fills,
                "realized_pnl_usd": float(g.get("realized_pnl_usd") or 0),
                "reason": "idle_no_fills" if idle else "slow_no_profit",
            })

    state["first_seen"] = first_seen
    state["last_scan_at"] = _iso()
    state["last_stuck_count"] = len(stuck)
    _write_state(state)

    return {
        "success": True,
        "stuck_hours_threshold": thr_h,
        "min_stuck_usd": min_usd,
        "stuck_assets": stuck,
        "count": len(stuck),
    }


def recalculate_options(
    stuck_assets: Optional[List[Dict[str, Any]]] = None,
    *,
    notional_usd: float = 75.0,
) -> Dict[str, Any]:
    """Rank exit/unstick paths: grid MM, cross-venue arb, rotation sell."""
    from backend.services.exchange_grid_bot_service import (
        rank_profit_pairs,
        scan_cross_venue_differences,
    )
    from backend.services.exchange_swap_rotation_service import suggest_swap_actions

    scan = scan_stuck_assets()
    assets = stuck_assets if stuck_assets is not None else (scan.get("stuck_assets") or [])
    ranked = rank_profit_pairs(include_live=True, min_score=1.0)
    cross = scan_cross_venue_differences(min_net_bps=5.0, notional_usd=notional_usd)
    cross_by_sym = {}
    for d in cross.get("differences") or []:
        cross_by_sym[str(d.get("symbol") or "").upper()] = d
    rank_by_sym = {r["symbol"]: r for r in ranked}
    rotation = suggest_swap_actions(hours=24, limit=8)
    rot_syms = {}
    for act in rotation.get("actions") or []:
        sym = str(act.get("symbol") or act.get("asset") or "").upper()
        if sym:
            rot_syms.setdefault(sym, []).append(act)

    plans: List[Dict[str, Any]] = []
    for row in assets:
        sym = row["asset"]
        rp = rank_by_sym.get(sym) or {}
        cx = cross_by_sym.get(sym) or {}
        rots = rot_syms.get(sym) or []
        strategy = "grid_maker"
        score = float(rp.get("score") or 0)
        if cx and float(cx.get("net_bps") or 0) >= 12:
            strategy = "cross_arb"
            score = max(score, float(cx.get("net_bps") or 0))
        elif rots:
            strategy = "rotation_unwind"
            score = max(score, 20.0)
        elif float(rp.get("net_edge_bps") or 0) >= 8:
            strategy = "grid_maker"
        plans.append({
            **row,
            "recommended_strategy": strategy,
            "strategy_score": round(score, 2),
            "profit_pair": rp,
            "cross_venue": cx,
            "rotation_actions": rots[:2],
            "grid_venues": rp.get("venues") or [row["venue"]],
        })
    plans.sort(key=lambda p: float(p.get("strategy_score") or 0), reverse=True)
    return {
        "success": True,
        "plans": plans,
        "plan_count": len(plans),
        "rotation_suggested": len(rotation.get("actions") or []),
    }


def apply_plans_to_grid(
    plans: Optional[List[Dict[str, Any]]] = None,
    *,
    top_n: int = 6,
    apply: bool = True,
) -> Dict[str, Any]:
    """Merge stuck-asset plans into grid bot venue asset lists."""
    from backend.services.exchange_grid_bot_service import load_config, grid_targets

    if plans is None:
        rec = recalculate_options()
        plans = rec.get("plans") or []
    cfg = load_config()
    venues = {k: list(v) for k, v in (cfg.get("venues") or {}).items()}
    legacy = {str(a).upper() for a in (cfg.get("assets") or [])}
    added: List[Tuple[str, str]] = []

    for p in (plans or [])[: max(1, top_n)]:
        sym = str(p.get("asset") or "").upper()
        if not sym:
            continue
        for v in p.get("grid_venues") or [p.get("venue")]:
            v = str(v or "").lower()
            if v not in _VENUES:
                continue
            existing = {str(x).upper() for x in (venues.get(v) or [])}
            if v == "binance":
                existing |= legacy
            if sym not in existing:
                venues.setdefault(v, [])
                venues[v].append(sym)
                added.append((v, sym))
            venues[v] = sorted(set(str(x).upper() for x in venues[v]))

    out: Dict[str, Any] = {
        "success": True,
        "added": [{"venue": v, "asset": a} for v, a in added],
        "applied": False,
        "targets_total": len(grid_targets(cfg)),
    }
    if apply and added:
        cfg["venues"] = venues
        ex._write_json(_CFG_PATH, cfg)
        out["applied"] = True
        out["targets_total"] = len(grid_targets(cfg))
    state = _read_state()
    state["last_apply_at"] = _iso()
    state["last_added"] = out["added"]
    _write_state(state)
    return out


def ops_state() -> Dict[str, Any]:
    return _read_state()


def run_stuck_strategy_tick(*, apply_grid: bool = True) -> Dict[str, Any]:
    """One ops tick: scan → recalculate → optionally patch grid config."""
    scan = scan_stuck_assets()
    rec = recalculate_options(stuck_assets=scan.get("stuck_assets"))
    apply_res = apply_plans_to_grid(rec.get("plans"), apply=apply_grid) if scan.get("count") else {
        "success": True,
        "applied": False,
        "added": [],
    }
    return {
        "success": True,
        "scan": scan,
        "recalculate": rec,
        "grid_apply": apply_res,
    }
