"""Profit pipeline — signal search → grid/winnable/stuck alignment (Business Control + daemon)."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex


def pipeline_status(*, light: bool = True) -> Dict[str, Any]:
    """Read-only snapshot for Business Control (no mutations)."""
    out: Dict[str, Any] = {"success": True, "light": light}
    try:
        from backend.services.exchange_profit_pair_search_service import read_index, enabled

        idx = read_index()
        out["pair_search"] = {
            "enabled": enabled(),
            "updated_at": idx.get("updated_at"),
            "hot_symbols": list(idx.get("hot_symbols") or [])[:16],
            "hit_count": len(idx.get("hits") or []),
            "live_hit_count": idx.get("live_hit_count"),
            "top_hits": (idx.get("hits") or [])[:8],
        }
    except Exception as exc:
        out["pair_search"] = {"success": False, "error": str(exc)[:200]}

    try:
        from backend.services.exchange_extended_profit_service import read_arb_threshold_state

        out["arb_threshold"] = read_arb_threshold_state()
    except Exception as exc:
        out["arb_threshold"] = {"error": str(exc)[:120]}

    try:
        from backend.services.exchange_grid_bot_service import grid_status

        gs = grid_status()
        out["grid"] = {
            "live": gs.get("live"),
            "enabled": gs.get("enabled"),
            "targets_total": gs.get("targets_total"),
            "realized_pnl_usd": gs.get("realized_pnl_usd"),
        }
    except Exception as exc:
        out["grid"] = {"error": str(exc)[:120]}

    try:
        from backend.services.exchange_stuck_inventory_service import scan_stuck_assets, ops_state

        if light:
            st = ops_state()
            out["stuck"] = {
                "last_scan_at": st.get("last_scan_at"),
                "last_stuck_count": st.get("last_stuck_count"),
                "last_added": st.get("last_added") or [],
            }
        else:
            scan = scan_stuck_assets()
            out["stuck"] = {"scan": scan, "ops": ops_state()}
    except Exception as exc:
        out["stuck"] = {"error": str(exc)[:120]}

    try:
        from backend.services.exchange_spot_reuse_service import ops_state as spot_ops

        so = spot_ops()
        out["spot_reuse"] = {
            "enabled": (so.get("config") or {}).get("enabled"),
            "live_gate": (so.get("config") or {}).get("live_gate"),
            "last_tick_at": so.get("last_tick_at"),
            "last_count": so.get("last_count"),
            "profit_pct": (so.get("config") or {}).get("profit_pct"),
            "loss_cancel_pct": (so.get("config") or {}).get("loss_cancel_pct"),
        }
    except Exception as exc:
        out["spot_reuse"] = {"error": str(exc)[:120]}

    try:
        from backend.services.business_control_preflight_service import run_preflight

        pf = run_preflight(light_overview=True)
        out["preflight_ok"] = bool(pf.get("success"))
        out["preflight_failed"] = pf.get("failed") or []
    except Exception:
        out["preflight_ok"] = None

    return out


def run_profit_pipeline(
    *,
    apply_grid_from_search: bool = False,
    apply_stuck_grid: bool = False,
    cross_scan: bool = False,
    spot_reuse_tick: bool = False,
    min_cross_bps: float = 8.0,
    min_profit_score: float = 3.0,
) -> Dict[str, Any]:
    """One owner-triggered pass: refresh signals and optionally patch grid config."""
    steps: List[Dict[str, Any]] = []

    pair_search: Optional[Dict[str, Any]] = None
    try:
        from backend.services.exchange_profit_pair_search_service import run_profit_pair_search

        pair_search = run_profit_pair_search()
        steps.append({"step": "profit_pair_search", "ok": bool(pair_search.get("success")), "detail": pair_search.get("hot_symbols")})
    except Exception as exc:
        steps.append({"step": "profit_pair_search", "ok": False, "error": str(exc)[:200]})

    grid_patch: Optional[Dict[str, Any]] = None
    if apply_grid_from_search:
        try:
            from backend.services.exchange_grid_bot_service import autoselect_profit_pairs

            grid_patch = autoselect_profit_pairs(min_score=min_profit_score, include_live=True, apply=True)
            steps.append({"step": "grid_autoselect_profit", "ok": True, "added": grid_patch.get("selected")})
        except Exception as exc:
            steps.append({"step": "grid_autoselect_profit", "ok": False, "error": str(exc)[:200]})

    cross_patch: Optional[Dict[str, Any]] = None
    if cross_scan:
        try:
            from backend.services.exchange_grid_bot_service import autoselect_cross_venue_pairs

            cross_patch = autoselect_cross_venue_pairs(min_net_bps=min_cross_bps, apply=True)
            steps.append({"step": "grid_cross_scan", "ok": True, "count": cross_patch.get("count")})
        except Exception as exc:
            steps.append({"step": "grid_cross_scan", "ok": False, "error": str(exc)[:200]})

    stuck_res: Optional[Dict[str, Any]] = None
    try:
        from backend.services.exchange_stuck_inventory_service import run_stuck_strategy_tick

        stuck_res = run_stuck_strategy_tick(apply_grid=apply_stuck_grid)
        sc = stuck_res.get("scan") or {}
        steps.append({
            "step": "stuck_inventory",
            "ok": True,
            "stuck_count": sc.get("count"),
            "grid_applied": (stuck_res.get("grid_apply") or {}).get("applied"),
        })
    except Exception as exc:
        steps.append({"step": "stuck_inventory", "ok": False, "error": str(exc)[:200]})

    spot_res: Optional[Dict[str, Any]] = None
    if spot_reuse_tick:
        try:
            from backend.services.exchange_spot_reuse_service import run_spot_reuse_tick, spot_reuse_live_enabled

            dry = None if spot_reuse_live_enabled() else True
            spot_res = run_spot_reuse_tick(dry_run=dry)
            steps.append({
                "step": "spot_reuse",
                "ok": bool(spot_res.get("success")),
                "managed": spot_res.get("managed_count"),
                "placed": spot_res.get("placed"),
            })
        except Exception as exc:
            steps.append({"step": "spot_reuse", "ok": False, "error": str(exc)[:200]})

    hot: List[str] = []
    if pair_search and pair_search.get("success"):
        hot = list(pair_search.get("hot_symbols") or [])
    try:
        from backend.services.exchange_extended_profit_service import read_arb_threshold_state

        th = read_arb_threshold_state()
        for s in th.get("hot_symbols") or []:
            if s and s not in hot:
                hot.append(s)
    except Exception:
        pass

    ex._audit(
        "profit_pipeline_run",
        user_id="owner",
        steps=len(steps),
        hot=",".join(hot[:8]),
        apply_grid=apply_grid_from_search,
        apply_stuck=apply_stuck_grid,
    )

    try:
        from backend.services.monitor_5d_pulse_service import publish_unified_event

        publish_unified_event(
            "unified",
            "Profit pipeline run · hot: " + (", ".join(hot[:4]) or "none"),
            detail="Steps: " + ", ".join(s["step"] for s in steps),
        )
    except Exception:
        pass

    status = pipeline_status(light=False)
    return {
        "success": all(s.get("ok", True) for s in steps if s.get("step") != "stuck_inventory" or s.get("ok")),
        "steps": steps,
        "hot_symbols": hot,
        "pair_search": pair_search,
        "grid_patch": grid_patch,
        "cross_patch": cross_patch,
        "stuck": stuck_res,
        "spot_reuse": spot_res,
        "status": status,
    }
