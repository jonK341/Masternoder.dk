"""Activate dormant supervisor fleet bots — symbol fan-out + winnable scale-out."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _supervisor_enabled(controls: Dict[str, Any], supervisor_id: str) -> bool:
    for s in controls.get("supervisors") or []:
        if s.get("id") == supervisor_id:
            return bool(s.get("enabled", True))
    return True


def _symbol_pool(
    controls: Dict[str, Any],
    *,
    hot_symbols: Optional[List[str]] = None,
    pair_search: Optional[Dict[str, Any]] = None,
) -> List[str]:
    pool: List[str] = []
    seen = set()
    for src in (hot_symbols or [], (pair_search or {}).get("hot_symbols") or []):
        for s in src:
            sym = str(s or "").upper()
            if sym and sym not in seen:
                seen.add(sym)
                pool.append(sym)
    meta = controls.setdefault("fleet_meta", {})
    off = int(meta.get("catalog_offset") or 0)
    try:
        from backend.services.exchange_binance_spot_catalog_service import catalog_batch

        batch, next_off, _n = catalog_batch(batch_size=48, offset=off, quote="USDC")
        meta["catalog_offset"] = next_off
        for sym in batch:
            s = str(sym).upper()
            if s and s not in seen:
                seen.add(s)
                pool.append(s)
    except Exception:
        pass
    return pool


def activate_fleet_for_profit(
    controls: Dict[str, Any],
    *,
    hot_symbols: Optional[List[str]] = None,
    pair_search: Optional[Dict[str, Any]] = None,
    enable_dormant: bool = True,
) -> Dict[str, Any]:
    """Mutate controls: assign symbols to PA bots, scale winnable shards, enable idle fleet rows."""
    from backend.services.exchange_supervisor_fleet_service import merge_fleet_into_controls

    merge_fleet_into_controls(controls)
    actions: List[Dict[str, Any]] = []
    mutated = False
    pool = _symbol_pool(controls, hot_symbols=hot_symbols, pair_search=pair_search)

    analytics = [b for b in (controls.get("fleet_bots") or []) if b.get("kind") == "analytics"]
    n_an = max(1, len(analytics))
    for i, bot in enumerate(analytics):
        if not _supervisor_enabled(controls, str(bot.get("supervisor") or "sup_profit")):
            continue
        chunk = [pool[j] for j in range(i, len(pool), n_an)][:10]
        if not chunk:
            continue
        cfg = bot.setdefault("config", {})
        if cfg.get("symbols") != chunk:
            cfg["symbols"] = chunk
            cfg["symbols_assigned_at"] = _iso()
            mutated = True
            actions.append({"type": "analytics_symbols", "bot_id": bot.get("id"), "symbols": chunk[:6]})

    hits = (pair_search or {}).get("hits") or []
    hit_n = int((pair_search or {}).get("hit_count") or len(hits) or 0)
    shards_live = 1
    if hit_n >= 8:
        shards_live = 4
    elif hit_n >= 4:
        shards_live = 2

    winnable = sorted(
        [b for b in (controls.get("fleet_bots") or []) if b.get("kind") == "winnable_pairs"],
        key=lambda b: int((b.get("config") or {}).get("shard") or 0),
    )
    if _supervisor_enabled(controls, "sup_winnable"):
        for bot in winnable:
            shard = int((bot.get("config") or {}).get("shard") or 0)
            bid = str(bot.get("id") or "")
            if shard >= shards_live:
                continue
            overrides = controls.setdefault("bot_overrides", {})
            cur = overrides.get(bid) if isinstance(overrides.get(bid), dict) else {}
            if cur.get("enabled") is False:
                continue
            if not isinstance(cur, dict) or cur.get("enabled") is not True:
                overrides[bid] = {**(cur if isinstance(cur, dict) else {}), "enabled": True}
                mutated = True
                actions.append({
                    "type": "winnable_scale_out",
                    "bot_id": bid,
                    "shard": shard,
                    "hit_count": hit_n,
                })

    if enable_dormant:
        for bot in controls.get("fleet_bots") or []:
            kind = bot.get("kind")
            if kind not in ("analytics", "winnable_pairs", "extended_profit"):
                continue
            sup = str(bot.get("supervisor") or "")
            if not _supervisor_enabled(controls, sup):
                continue
            if bot.get("last_run_at"):
                continue
            bid = str(bot.get("id") or "")
            overrides = controls.setdefault("bot_overrides", {})
            cur = overrides.get(bid)
            if isinstance(cur, dict) and cur.get("enabled") is False:
                continue
            overrides[bid] = {**(cur if isinstance(cur, dict) else {}), "enabled": True}
            mutated = True
            actions.append({"type": "dormant_enable", "bot_id": bid, "kind": kind})

    if mutated:
        controls["updated_at"] = _iso()
        meta = controls.setdefault("fleet_meta", {})
        meta["last_activation_at"] = _iso()
        meta["last_activation_actions"] = len(actions)
    ex._audit("fleet_activation", user_id="owner", actions=len(actions), mutated=mutated)
    return {"success": True, "mutated": mutated, "actions": actions, "pool_size": len(pool), "hit_count": hit_n}
