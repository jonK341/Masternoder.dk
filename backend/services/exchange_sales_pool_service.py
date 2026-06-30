"""Sweep cross-trade agent wallet liquidity into a central sales-pool user account.

Agent bots accumulate USDC, USDT, and layer-1 assets from internal cross-trades.
This service moves excess inventory above per-agent reserves into ``sales_pool_user_id``
so customer-facing swaps can draw from a single liquidity pool.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_CFG_PATH = os.path.join(ex._BASE, "data", "exchange_sales_pool_config.json")
_STATE_PATH = os.path.join(ex._DATA_DIR, "sales_pool_state.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "sales_pool_ledger.jsonl")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CFG_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def get_sales_pool_config() -> Dict[str, Any]:
    cfg = load_config()
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "sales_pool_user_id": sales_pool_user_id(),
        "source_agent_ids": list(cfg.get("source_agent_ids") or []),
        "min_transfer_by_asset": cfg.get("min_transfer_by_asset") or {},
        "reserve_by_agent": cfg.get("reserve_by_agent") or {},
        "min_pool_by_asset": cfg.get("min_pool_by_asset") or {},
        "tick_cooldown_seconds": int(cfg.get("tick_cooldown_seconds") or 300),
    }


def sales_pool_user_id() -> str:
    return str(load_config().get("sales_pool_user_id") or "exchange_sales_pool")


def _read_state() -> Dict[str, Any]:
    return ex._read_json(_STATE_PATH, {"last_transfer_at": None, "transfer_count": 0, "gap_streak": {}})


def _write_state(state: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, state)


def _pool_gaps(cfg: Dict[str, Any]) -> Dict[str, float]:
    pool_uid = sales_pool_user_id()
    pool_assets = (ex.get_wallet(pool_uid).get("assets") or {})
    min_pool = cfg.get("min_pool_by_asset") or {}
    gaps: Dict[str, float] = {}
    if not isinstance(min_pool, dict):
        return gaps
    for sym, target in min_pool.items():
        sym_u = str(sym).upper()
        gap = round(float(target or 0) - float(pool_assets.get(sym_u) or 0), 12)
        if gap > 0:
            gaps[sym_u] = gap
    return gaps


def _auto_tune_mins(cfg: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, float]:
    """Return effective min_transfer per asset, optionally reduced when gaps persist."""
    base = cfg.get("min_transfer_by_asset") or {}
    if not isinstance(base, dict):
        return {}
    if not cfg.get("auto_tune"):
        return {str(k).upper(): float(v or 0) for k, v in base.items()}

    floors = cfg.get("auto_tune_min_transfer_floor") or {}
    streaks = state.get("auto_tune_gap_streak") or {}
    threshold = int(cfg.get("auto_tune_ticks_threshold") or 3)
    reduce_pct = float(cfg.get("auto_tune_reduce_pct") or 0.2)
    out: Dict[str, float] = {}
    for sym, raw_min in base.items():
        sym_u = str(sym).upper()
        base_min = float(raw_min or 0)
        streak = int(streaks.get(sym_u) or 0)
        if streak >= threshold and sym_u in _pool_gaps(cfg):
            floor = float(floors.get(sym_u) or floors.get(sym) or 0)
            tuned = round(base_min * (1 - reduce_pct), 12)
            out[sym_u] = max(floor, tuned) if floor > 0 else tuned
        else:
            out[sym_u] = base_min
    return out


def _update_auto_tune_state(cfg: Dict[str, Any], state: Dict[str, Any]) -> None:
    if not cfg.get("auto_tune"):
        return
    gaps = _pool_gaps(cfg)
    streaks = dict(state.get("auto_tune_gap_streak") or {})
    min_pool = cfg.get("min_pool_by_asset") or {}
    for sym in (min_pool.keys() if isinstance(min_pool, dict) else []):
        sym_u = str(sym).upper()
        if sym_u in gaps:
            streaks[sym_u] = int(streaks.get(sym_u) or 0) + 1
        else:
            streaks.pop(sym_u, None)
    state["auto_tune_gap_streak"] = streaks
    state["auto_tune_effective_mins"] = _auto_tune_mins(cfg, state)


def _agent_reserve(cfg: Dict[str, Any], agent_id: str, symbol: str) -> float:
    reserves = cfg.get("reserve_by_agent") or {}
    agent_row = reserves.get(agent_id) if isinstance(reserves.get(agent_id), dict) else {}
    default_row = reserves.get("default") if isinstance(reserves.get("default"), dict) else {}
    if symbol in agent_row:
        return float(agent_row[symbol] or 0)
    return float(default_row.get(symbol) or 0)


def _sweepable_symbols(cfg: Dict[str, Any], assets: Dict[str, Any]) -> List[str]:
    mins = cfg.get("min_transfer_by_asset") or {}
    if isinstance(mins, dict) and mins:
        return [s.upper() for s in mins.keys()]
    return [s.upper() for s, v in assets.items() if float(v or 0) > 0 and s.upper() != "MN2"]


def list_agent_wallet_balances() -> Dict[str, Any]:
    cfg = load_config()
    state = _read_state()
    effective_mins = _auto_tune_mins(cfg, state)
    agents: List[Dict[str, Any]] = []
    for agent_id in cfg.get("source_agent_ids") or []:
        aid = str(agent_id or "").strip()
        if not aid:
            continue
        wallet = ex.get_wallet(aid)
        assets = wallet.get("assets") if isinstance(wallet.get("assets"), dict) else {}
        sweepable: Dict[str, float] = {}
        for sym in _sweepable_symbols(cfg, assets):
            bal = float(assets.get(sym) or 0)
            reserve = _agent_reserve(cfg, aid, sym)
            min_xfer = float(effective_mins.get(sym) or (cfg.get("min_transfer_by_asset") or {}).get(sym) or 0)
            transferable = max(0.0, round(bal - reserve, 12))
            if transferable >= min_xfer:
                sweepable[sym] = transferable
        agents.append({
            "agent_id": aid,
            "assets": {k: round(float(v or 0), 12) for k, v in assets.items()},
            "transferable": sweepable,
        })
    return {
        "success": True,
        "agents": agents,
        "sales_pool_user_id": sales_pool_user_id(),
        "effective_min_transfer": effective_mins if cfg.get("auto_tune") else None,
    }


def _cooldown_active(cfg: Dict[str, Any], *, force: bool) -> bool:
    if force:
        return False
    cooldown = int(cfg.get("tick_cooldown_seconds") or 300)
    if cooldown <= 0:
        return False
    last = _read_state().get("last_transfer_at")
    if not last:
        return False
    try:
        last_ts = datetime.fromisoformat(str(last).replace("Z", "+00:00")).timestamp()
    except Exception:
        return False
    return (time.time() - last_ts) < cooldown


def transfer_to_sales_pool(*, force: bool = False) -> Dict[str, Any]:
    """Move sweepable assets from source agent wallets to the sales pool user."""
    cfg = load_config()
    if not cfg.get("enabled", True) and not force:
        return {"success": False, "error": "sales_pool_disabled"}

    if _cooldown_active(cfg, force=force):
        return {
            "success": True,
            "skipped": True,
            "reason": "cooldown",
            "tick_cooldown_seconds": int(cfg.get("tick_cooldown_seconds") or 300),
        }

    pool_uid = sales_pool_user_id()
    transfers: List[Dict[str, Any]] = []
    state = _read_state()
    effective_mins = _auto_tune_mins(cfg, state)

    with ex._LOCK:
        for agent_id in cfg.get("source_agent_ids") or []:
            aid = str(agent_id or "").strip()
            if not aid:
                continue
            wallet = ex.get_wallet(aid)
            assets = wallet.get("assets") if isinstance(wallet.get("assets"), dict) else {}
            for sym in _sweepable_symbols(cfg, assets):
                bal = float(assets.get(sym) or 0)
                reserve = _agent_reserve(cfg, aid, sym)
                min_xfer = float(effective_mins.get(sym) or (cfg.get("min_transfer_by_asset") or {}).get(sym) or 0)
                amount = round(max(0.0, bal - reserve), 12)
                if amount < min_xfer:
                    continue
                ref = f"sales-pool:{aid}:{sym}:{_iso()[:19]}"
                try:
                    ex._adjust_balance(aid, sym, -amount)
                    ex._adjust_balance(pool_uid, sym, amount)
                except Exception as exc:
                    transfers.append({
                        "agent_id": aid,
                        "symbol": sym,
                        "amount": amount,
                        "success": False,
                        "error": str(exc),
                    })
                    continue
                row = {
                    "ts": _iso(),
                    "agent_id": aid,
                    "sales_pool_user_id": pool_uid,
                    "symbol": sym,
                    "amount": amount,
                    "reference": ref,
                }
                ex._append_jsonl(_LEDGER_PATH, row)
                ex._audit("sales_pool_transfer", user_id=pool_uid, agent_id=aid,
                          symbol=sym, amount=amount, reference=ref)
                transfers.append({"success": True, **row})

    state = _read_state()
    if transfers:
        state["last_transfer_at"] = _iso()
        state["transfer_count"] = int(state.get("transfer_count") or 0) + len(
            [t for t in transfers if t.get("success")]
        )
    _update_auto_tune_state(cfg, state)
    _write_state(state)

    return {
        "success": True,
        "sales_pool_user_id": pool_uid,
        "transfers": transfers,
        "transfer_count": len([t for t in transfers if t.get("success")]),
        "effective_min_transfer": effective_mins if cfg.get("auto_tune") else None,
    }


def rebalance_sales_pool(*, force: bool = False) -> Dict[str, Any]:
    """Sweep from agents when the sales pool is below configured minimums per asset."""
    cfg = load_config()
    mins = cfg.get("min_pool_by_asset") or {}
    if not isinstance(mins, dict) or not mins:
        return transfer_to_sales_pool(force=force)

    pool_uid = sales_pool_user_id()
    pool_assets = (ex.get_wallet(pool_uid).get("assets") or {})
    deficits: Dict[str, float] = {}
    for sym, target in mins.items():
        sym_u = str(sym).upper()
        need = float(target or 0) - float(pool_assets.get(sym_u) or 0)
        if need > 0:
            deficits[sym_u] = round(need, 12)
    if not deficits:
        return {"success": True, "skipped": True, "reason": "pool_sufficient", "pool_assets": pool_assets}

    result = transfer_to_sales_pool(force=force)
    result["deficits_before"] = deficits
    return result


def sales_pool_status() -> Dict[str, Any]:
    cfg = load_config()
    pool_uid = sales_pool_user_id()
    pool_wallet = ex.get_wallet(pool_uid)
    pool_assets = pool_wallet.get("assets") if isinstance(pool_wallet.get("assets"), dict) else {}
    agent_balances = list_agent_wallet_balances()
    state = _read_state()
    ledger_rows = 0
    swept_total: Dict[str, float] = {}
    if os.path.isfile(_LEDGER_PATH):
        try:
            import json
            with open(_LEDGER_PATH, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    ledger_rows += 1
                    sym = str(row.get("symbol") or "").upper()
                    amt = float(row.get("amount") or 0)
                    swept_total[sym] = round(swept_total.get(sym, 0) + amt, 12)
        except Exception:
            pass

    min_pool = cfg.get("min_pool_by_asset") or {}
    pool_gaps = _pool_gaps(cfg)

    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "sales_pool_user_id": pool_uid,
        "pool_assets": {k: round(float(v or 0), 12) for k, v in pool_assets.items()},
        "pool_gaps": pool_gaps,
        "source_agents": agent_balances.get("agents") or [],
        "last_transfer_at": state.get("last_transfer_at"),
        "transfer_count": int(state.get("transfer_count") or 0),
        "ledger_rows": ledger_rows,
        "lifetime_swept": swept_total,
        "tick_cooldown_seconds": int(cfg.get("tick_cooldown_seconds") or 300),
        "auto_tune": bool(cfg.get("auto_tune")),
        "auto_tune_gap_streak": state.get("auto_tune_gap_streak") or {},
        "effective_min_transfer": state.get("auto_tune_effective_mins") or _auto_tune_mins(cfg, state),
    }


def run_sales_pool_tick(*, force: bool = False) -> Dict[str, Any]:
    """Daemon entry: rebalance (sweep when pool low) then status snapshot."""
    cfg = load_config()
    if not cfg.get("enabled", True) and not force:
        return {"success": True, "skipped": True, "reason": "disabled"}
    state = _read_state()
    _update_auto_tune_state(cfg, state)
    _write_state(state)
    result = rebalance_sales_pool(force=force)
    st = sales_pool_status()
    result["status"] = {
        "pool_assets": st.get("pool_assets"),
        "pool_gaps": st.get("pool_gaps"),
        "effective_min_transfer": st.get("effective_min_transfer"),
    }
    return result
