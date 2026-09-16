"""MN2 / USDT / USDC customer liquidity pool.

Customer swaps between MN2 coins and platform stables are backed by ``pool_user_id``
(``exchange_sales_pool``). The pool agent tops up inventory and rebalances stables.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.services import crypto_exchange_service as ex

_CFG_PATH = os.path.join(ex._BASE, "data", "exchange_mn2_pool_config.json")
_STATE_PATH = os.path.join(ex._DATA_DIR, "mn2_pool_state.json")
_LEDGER_PATH = os.path.join(ex._DATA_DIR, "mn2_pool_ledger.jsonl")
_RESERVE_PATH = os.path.join(ex._DATA_DIR, "mn2_pool_reserve.json")
_RESERVE_LEDGER_PATH = os.path.join(ex._DATA_DIR, "mn2_pool_reserve_ledger.jsonl")
_POOL_ASSETS = frozenset({"MN2", "USDT", "USDC"})


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CFG_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def pool_enabled() -> bool:
    return bool(load_config().get("enabled", True))


def pool_user_id() -> str:
    return str(load_config().get("pool_user_id") or "exchange_sales_pool")


def pool_agent_id() -> str:
    return str(load_config().get("agent_id") or "exchange_agent_mn2_pool")


def reserve_user_id() -> str:
    return str(load_config().get("reserve_user_id") or "exchange_mn2_pool_reserve")


def pool_swap_reserve_bps() -> int:
    if not pool_enabled():
        return 0
    return int(load_config().get("pool_swap_reserve_bps") or 200)


def compute_pool_reserve(amount: float, price_quote: float, reserve_bps: Optional[int] = None) -> float:
    bps = int(reserve_bps if reserve_bps is not None else pool_swap_reserve_bps())
    if bps <= 0:
        return 0.0
    gross = float(amount or 0) * float(price_quote or 0)
    return round(gross * bps / 10000.0, 12)


def is_pool_swap(symbol: str, quote: str) -> bool:
    sym = (symbol or "").strip().upper()
    q = (quote or "").strip().upper()
    if sym == q or sym not in _POOL_ASSETS or q not in _POOL_ASSETS:
        return False
    return "MN2" in (sym, q)


def _read_state() -> Dict[str, Any]:
    return ex._read_json(_STATE_PATH, {"last_tick_at": None, "paper_seeded": False, "tick_count": 0})


def _write_state(state: Dict[str, Any]) -> None:
    ex._write_json(_STATE_PATH, state)


def _pool_mn2_balance(uid: str) -> float:
    return float(ex._get_quote_balance(uid, "MN2") or 0)


def _pool_asset_balance(uid: str, symbol: str) -> float:
    sym = (symbol or "").strip().upper()
    if sym == "MN2":
        return _pool_mn2_balance(uid)
    return float(ex._get_balance(uid, sym) or 0)


def _credit_pool(uid: str, symbol: str, amount: float, meta: Dict[str, Any]) -> None:
    sym = (symbol or "").strip().upper()
    amt = float(amount or 0)
    if amt <= 0:
        return
    if sym == "MN2":
        ex._adjust_quote_balance(uid, "MN2", amt, "mn2_pool_receive", meta)
    else:
        ex._adjust_balance(uid, sym, amt)


def _debit_pool(uid: str, symbol: str, amount: float, meta: Dict[str, Any]) -> None:
    sym = (symbol or "").strip().upper()
    amt = float(amount or 0)
    if amt <= 0:
        return
    available = _pool_asset_balance(uid, sym)
    if available + 1e-12 < amt:
        raise ValueError("insufficient_pool_liquidity")
    if sym == "MN2":
        ex._adjust_quote_balance(uid, "MN2", -amt, "mn2_pool_pay", meta)
    else:
        ex._adjust_balance(uid, sym, -amt)


def _credit_reserve(uid: str, symbol: str, amount: float, meta: Dict[str, Any]) -> None:
    _credit_pool(uid, symbol, amount, meta)


def _read_reserve_totals() -> Dict[str, Any]:
    row = ex._read_json(_RESERVE_PATH, {"assets": {}, "swap_count": 0, "updated_at": None})
    assets = row.get("assets") if isinstance(row.get("assets"), dict) else {}
    return {
        "assets": {str(k).upper(): round(float(v or 0), 12) for k, v in assets.items()},
        "swap_count": int(row.get("swap_count") or 0),
        "updated_at": row.get("updated_at"),
    }


def reserve_balances() -> Dict[str, float]:
    uid = reserve_user_id()
    out = {sym: round(_pool_asset_balance(uid, sym), 8) for sym in sorted(_POOL_ASSETS)}
    totals = _read_reserve_totals()
    for sym, amt in (totals.get("assets") or {}).items():
        out[sym] = round(max(float(out.get(sym) or 0), float(amt or 0)), 8)
    return out


def apply_pool_reserve_to_quote(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Add the pool swap reserve (default 2%) to an existing quote payload."""
    if not payload.get("success") or not pool_enabled():
        return payload
    sym = str(payload.get("symbol") or "").upper()
    quote = str(payload.get("quote_currency") or "").upper()
    if not is_pool_swap(sym, quote):
        return payload

    reserve_bps = pool_swap_reserve_bps()
    reserve_quote = compute_pool_reserve(
        float(payload.get("amount") or 0),
        float(payload.get("price_quote") or 0),
        reserve_bps,
    )
    if reserve_quote <= 0:
        return payload

    side = str(payload.get("side") or "").lower()
    if side == "buy":
        payload["quote_cost"] = round(float(payload.get("quote_cost") or 0) + reserve_quote, 8)
    else:
        payload["quote_received"] = round(max(0.0, float(payload.get("quote_received") or 0) - reserve_quote), 8)

    payload["pool_reserve_quote"] = round(reserve_quote, 8)
    payload["pool_reserve_bps"] = reserve_bps
    payload["pool_reserve_currency"] = quote
    return payload


def stash_swap_reserve(quote_payload: Dict[str, Any], trade_ref: str) -> Dict[str, Any]:
    """Move the pool swap reserve from the liquidity pool into the reserve account."""
    reserve_quote = float(quote_payload.get("pool_reserve_quote") or 0)
    if reserve_quote <= 0 or not pool_enabled():
        return {"success": True, "skipped": True, "reason": "no_reserve"}

    reserve_asset = str(quote_payload.get("pool_reserve_currency") or quote_payload.get("quote_currency") or "MN2").upper()
    pool_uid = pool_user_id()
    reserve_uid = reserve_user_id()
    meta = {
        "reference": trade_ref,
        "quote_id": quote_payload.get("quote_id"),
        "symbol": quote_payload.get("symbol"),
        "side": quote_payload.get("side"),
        "quote": quote_payload.get("quote_currency"),
    }

    _debit_pool(pool_uid, reserve_asset, reserve_quote, meta)
    _credit_reserve(reserve_uid, reserve_asset, reserve_quote, meta)

    totals = _read_reserve_totals()
    assets = totals.get("assets") or {}
    assets[reserve_asset] = round(float(assets.get(reserve_asset) or 0) + reserve_quote, 12)
    totals_row = {
        "assets": assets,
        "swap_count": int(totals.get("swap_count") or 0) + 1,
        "updated_at": _iso(),
    }
    ex._write_json(_RESERVE_PATH, totals_row)
    ledger_row = {
        "ts": _iso(),
        "trade_ref": trade_ref,
        "reserve_user_id": reserve_uid,
        "pool_user_id": pool_uid,
        "asset": reserve_asset,
        "amount": reserve_quote,
        "reserve_bps": int(quote_payload.get("pool_reserve_bps") or pool_swap_reserve_bps()),
        "symbol": quote_payload.get("symbol"),
        "side": quote_payload.get("side"),
        "quote": quote_payload.get("quote_currency"),
    }
    ex._append_jsonl(_RESERVE_LEDGER_PATH, ledger_row)
    ex._audit("mn2_pool_reserve_stash", user_id=reserve_uid, asset=reserve_asset, amount=reserve_quote, trade_ref=trade_ref)
    return {"success": True, "stashed": ledger_row, "reserve_balances": reserve_balances()}


def pool_balances() -> Dict[str, float]:
    uid = pool_user_id()
    return {sym: round(_pool_asset_balance(uid, sym), 8) for sym in sorted(_POOL_ASSETS)}


def pool_gaps() -> Dict[str, float]:
    cfg = load_config()
    mins = cfg.get("min_pool_by_asset") or {}
    balances = pool_balances()
    gaps: Dict[str, float] = {}
    if not isinstance(mins, dict):
        return gaps
    for sym, target in mins.items():
        sym_u = str(sym).upper()
        gap = round(float(target or 0) - float(balances.get(sym_u) or 0), 12)
        if gap > 0:
            gaps[sym_u] = gap
    return gaps


def _pool_payout(symbol: str, side: str, quote: str, quote_payload: Dict[str, Any]) -> Tuple[str, float]:
    sym = (symbol or "").strip().upper()
    side = (side or "").strip().lower()
    q = (quote or "").strip().upper()
    if side == "buy":
        return sym, float(quote_payload.get("amount") or 0)
    return q, float(quote_payload.get("quote_received") or 0)


def check_pool_liquidity(symbol: str, side: str, quote: str, quote_payload: Dict[str, Any]) -> Optional[str]:
    if not pool_enabled() or not is_pool_swap(symbol, quote):
        return None
    ensure_paper_seed()
    payout_sym, payout_amt = _pool_payout(symbol, side, quote, quote_payload)
    if payout_amt <= 0:
        return "invalid_pool_amount"
    uid = pool_user_id()
    available = _pool_asset_balance(uid, payout_sym)
    if available + 1e-12 < payout_amt:
        return "insufficient_pool_liquidity"
    return None


def apply_pool_leg(symbol: str, side: str, quote: str, quote_payload: Dict[str, Any]) -> Dict[str, Any]:
    if not pool_enabled() or not is_pool_swap(symbol, quote):
        return {"success": True, "skipped": True, "reason": "not_pool_swap"}

    sym = (symbol or "").strip().upper()
    side = (side or "").strip().lower()
    q = (quote or "").strip().upper()
    uid = pool_user_id()
    amt = float(quote_payload.get("amount") or 0)
    ref = {
        "reference": f"mn2-pool:{quote_payload.get('quote_id')}",
        "symbol": sym,
        "side": side,
        "quote": q,
    }

    if side == "buy":
        cost = float(quote_payload.get("quote_cost") or 0)
        _credit_pool(uid, q, cost, ref)
        _debit_pool(uid, sym, amt, ref)
        row = {"ts": _iso(), "pool_user_id": uid, "side": side, "symbol": sym, "quote": q,
               "pool_receive": {q: cost}, "pool_pay": {sym: amt}}
    else:
        received = float(quote_payload.get("quote_received") or 0)
        _credit_pool(uid, sym, amt, ref)
        _debit_pool(uid, q, received, ref)
        row = {"ts": _iso(), "pool_user_id": uid, "side": side, "symbol": sym, "quote": q,
               "pool_receive": {sym: amt}, "pool_pay": {q: received}}

    ex._append_jsonl(_LEDGER_PATH, row)
    ex._audit("mn2_pool_leg", user_id=uid, symbol=sym, side=side, quote=q, amount=amt)
    return {"success": True, "pool_leg": row, "pool_balances": pool_balances()}


def ensure_paper_seed() -> Dict[str, Any]:
    cfg = load_config()
    if not cfg.get("paper_seed_on_empty"):
        return {"success": True, "skipped": True, "reason": "paper_seed_disabled"}
    state = _read_state()
    if state.get("paper_seeded"):
        return {"success": True, "skipped": True, "reason": "already_seeded"}

    uid = pool_user_id()
    balances = pool_balances()
    seed = cfg.get("paper_seed") or {}
    if not isinstance(seed, dict):
        return {"success": True, "skipped": True, "reason": "no_seed_config"}
    if any(float(balances.get(sym) or 0) > 0 for sym in _POOL_ASSETS):
        state["paper_seeded"] = True
        _write_state(state)
        return {"success": True, "skipped": True, "reason": "pool_not_empty"}

    seeded: Dict[str, float] = {}
    meta = {"reference": f"mn2-pool-paper-seed:{_iso()[:19]}"}
    for sym, raw_amt in seed.items():
        sym_u = str(sym).upper()
        if sym_u not in _POOL_ASSETS:
            continue
        amt = float(raw_amt or 0)
        if amt <= 0:
            continue
        _credit_pool(uid, sym_u, amt, meta)
        seeded[sym_u] = amt

    state["paper_seeded"] = True
    state["paper_seeded_at"] = _iso()
    _write_state(state)
    ex._audit("mn2_pool_paper_seed", user_id=uid, seeded=seeded)
    return {"success": True, "seeded": seeded, "pool_balances": pool_balances()}


def mn2_pool_status() -> Dict[str, Any]:
    cfg = load_config()
    state = _read_state()
    ensure_paper_seed()
    balances = pool_balances()
    gaps = pool_gaps()
    health_block: Dict[str, Any] = {}
    try:
        from backend.services.exchange_ops_service import circuit_breaker_status, pool_health_score
        health_block = {
            "health": pool_health_score(),
            "circuit_breaker": circuit_breaker_status(),
        }
    except Exception:
        health_block = {}
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "pool_user_id": pool_user_id(),
        "agent_id": pool_agent_id(),
        "pool_assets": balances,
        "pool_gaps": gaps,
        **health_block,
        "tradeable_pairs": [
            "MN2/USDT", "MN2/USDC", "USDT/MN2", "USDC/MN2",
        ],
        "swap_back_hint": "Sell USDT or USDC (quote MN2) to swap back into MN2 coins, or sell MN2 for USDT/USDC.",
        "min_pool_by_asset": cfg.get("min_pool_by_asset") or {},
        "pool_swap_reserve_bps": pool_swap_reserve_bps(),
        "reserve_user_id": reserve_user_id(),
        "reserve_assets": reserve_balances(),
        "paper_seeded": bool(state.get("paper_seeded")),
        "last_tick_at": state.get("last_tick_at"),
        "tick_count": int(state.get("tick_count") or 0),
        "cron_interval_minutes": int(cfg.get("cron_interval_minutes") or 3),
    }


def _cooldown_active(cfg: Dict[str, Any], *, force: bool) -> bool:
    if force:
        return False
    cooldown = int(cfg.get("tick_cooldown_seconds") or 120)
    if cooldown <= 0:
        return False
    last = _read_state().get("last_tick_at")
    if not last:
        return False
    try:
        last_ts = datetime.fromisoformat(str(last).replace("Z", "+00:00")).timestamp()
    except Exception:
        return False
    return (time.time() - last_ts) < cooldown


def _seed_pool_mn2(cfg: Dict[str, Any], gaps: Dict[str, float]) -> Dict[str, Any]:
    gap = float(gaps.get("MN2") or 0)
    if gap <= 0:
        return {"success": True, "skipped": True, "reason": "mn2_sufficient"}
    seed_amt = min(gap, float(cfg.get("seed_mn2_per_tick") or 250))
    uid = pool_user_id()
    from backend.services.unified_points_database import unified_points_db

    unified_points_db.add_points(
        uid,
        "mn2_balance",
        seed_amt,
        source="mn2_pool_agent_seed",
        metadata={
            "reference": f"mn2-pool-seed:{uid}:{_iso()[:19]}",
            "non_withdrawable": True,
        },
    )
    return {"success": True, "seeded_mn2": seed_amt, "pool_mn2_after": _pool_mn2_balance(uid)}


def _rebalance_stables(cfg: Dict[str, Any]) -> Dict[str, Any]:
    uid = pool_user_id()
    usdt = _pool_asset_balance(uid, "USDT")
    usdc = _pool_asset_balance(uid, "USDC")
    total = usdt + usdc
    if total <= 0:
        return {"success": True, "skipped": True, "reason": "no_stables"}

    threshold = float(cfg.get("stable_rebalance_threshold") or 0.15)
    target = total / 2.0
    actions: List[Dict[str, Any]] = []

    if usdt < target * (1 - threshold) and usdc > target * (1 + threshold):
        amount = min(usdc - target, target - usdt)
        amount = round(max(float(ex._asset_map().get("USDC", {}).get("min_trade") or 1), amount), 8)
        if amount > 0 and usdc >= amount:
            q = ex.quote_swap(uid, "USDT", "buy", amount, "USDC")
            if q.get("success"):
                res = ex.execute_swap(uid, q["quote_id"], "USDT", "buy", amount, "USDC")
                actions.append({"pair": "USDC→USDT", "amount": amount, "success": bool(res.get("success")), "error": res.get("error")})

    elif usdc < target * (1 - threshold) and usdt > target * (1 + threshold):
        amount = min(usdt - target, target - usdc)
        amount = round(max(float(ex._asset_map().get("USDT", {}).get("min_trade") or 1), amount), 8)
        if amount > 0 and usdt >= amount:
            q = ex.quote_swap(uid, "USDC", "buy", amount, "USDT")
            if q.get("success"):
                res = ex.execute_swap(uid, q["quote_id"], "USDC", "buy", amount, "USDT")
                actions.append({"pair": "USDT→USDC", "amount": amount, "success": bool(res.get("success")), "error": res.get("error")})

    if not actions:
        return {"success": True, "skipped": True, "reason": "stables_balanced"}
    return {"success": True, "actions": actions}


def run_mn2_pool_agent_tick(*, force: bool = False, light: bool = False) -> Dict[str, Any]:
    """Feature 12: light tick skips heavy agent sweep (pool seed + rebalance only)."""
    cfg = load_config()
    if not cfg.get("enabled", True) and not force:
        return {"success": True, "skipped": True, "reason": "disabled"}

    if _cooldown_active(cfg, force=force) and not light:
        return {
            "success": True,
            "skipped": True,
            "reason": "cooldown",
            "tick_cooldown_seconds": int(cfg.get("tick_cooldown_seconds") or 120),
        }

    ensure_paper_seed()
    state = _read_state()
    gaps_before = pool_gaps()

    sweep_result: Dict[str, Any] = {"skipped": True, "reason": "light_tick"}
    if not light:
        try:
            from backend.services.exchange_sales_pool_service import transfer_to_sales_pool
            sweep_result = transfer_to_sales_pool(force=force)
        except Exception as exc:
            sweep_result = {"success": False, "error": str(exc)}

    seed_result = _seed_pool_mn2(cfg, pool_gaps())
    rebalance_result = _rebalance_stables(cfg)

    state = _read_state()
    state["last_tick_at"] = _iso()
    state["tick_count"] = int(state.get("tick_count") or 0) + 1
    state["last_gaps"] = gaps_before
    _write_state(state)

    status = mn2_pool_status()
    return {
        "success": True,
        "agent_id": pool_agent_id(),
        "light": bool(light),
        "gaps_before": gaps_before,
        "sweep": sweep_result,
        "seed": seed_result,
        "rebalance": rebalance_result,
        "status": status,
    }
