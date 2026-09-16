"""Grid autoselect driven by spot reuse / winnable / pair-search symbols."""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def autoselect_grid_for_symbols(
    symbols: List[str],
    *,
    min_score: float = 2.0,
    top_n: int = 3,
    apply: bool = True,
) -> Dict[str, Any]:
    if not symbols:
        return {"success": True, "skipped": True, "reason": "no_symbols"}
    symset = {str(s).upper() for s in symbols if s}
    from backend.services.exchange_grid_bot_service import load_config, rank_profit_pairs, grid_targets

    cfg = load_config()
    ranked = rank_profit_pairs(include_live=True, min_score=min_score, cfg=cfg)
    picked = [r for r in ranked if r.get("symbol") in symset][: max(1, int(top_n))]
    if not picked:
        return {"success": True, "skipped": True, "reason": "no_ranked_match", "candidates": sorted(symset)[:12]}

    existing = set(grid_targets(cfg))
    add: Dict[str, List[str]] = {}
    for r in picked:
        for v in r.get("venues") or ["binance"]:
            add.setdefault(str(v).lower(), []).append(str(r["symbol"]).upper())

    if not apply:
        return {"success": True, "applied": False, "selected": picked, "venues_add": add}

    from backend.services import crypto_exchange_service as ex
    from backend.services.exchange_grid_bot_service import _CFG_PATH, grid_targets as gt

    venues = {k: list(v) for k, v in (cfg.get("venues") or {}).items()}
    legacy_assets = {str(a).upper() for a in (cfg.get("assets") or [])}
    for v, syms in add.items():
        ex_set = {str(x).upper() for x in (venues.get(v) or [])}
        if v == "binance":
            ex_set |= legacy_assets
        venues[v] = sorted(ex_set | set(syms))
    cfg["venues"] = venues
    cfg["enabled"] = True
    ex._write_json(_CFG_PATH, cfg)
    return {
        "success": True,
        "applied": True,
        "selected": picked,
        "targets_total": len(gt(cfg)),
        "new_pairs": [r["symbol"] for r in picked],
    }


def maybe_grid_from_daemon_signals(
    *,
    spot_reuse_result: Optional[Dict[str, Any]] = None,
    pair_search: Optional[Dict[str, Any]] = None,
    enabled: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    if enabled is False:
        return None
    if enabled is None:
        try:
            from backend.services.exchange_spot_reuse_service import load_config as sr_cfg

            enabled = bool(sr_cfg().get("grid_autoselect_from_signals", True))
        except Exception:
            enabled = True
    if not enabled:
        return None

    symbols: List[str] = []
    if pair_search and pair_search.get("success"):
        symbols.extend(pair_search.get("hot_symbols") or [])
    if spot_reuse_result and not spot_reuse_result.get("skipped"):
        for row in spot_reuse_result.get("assets") or []:
            if isinstance(row, dict) and row.get("asset"):
                symbols.append(str(row["asset"]))
            elif isinstance(row, dict) and row.get("symbol"):
                symbols.append(str(row["symbol"]))
    symbols = list(dict.fromkeys(s.upper() for s in symbols if s))
    if not symbols:
        return None
    try:
        from backend.services.exchange_spot_reuse_service import load_config as sr_cfg

        top_n = int(sr_cfg().get("grid_autoselect_top_n") or 3)
    except Exception:
        top_n = 3
    return autoselect_grid_for_symbols(symbols, top_n=top_n, apply=True)
