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
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "pool_user_id": pool_user_id(),
        "agent_id": pool_agent_id(),
        "pool_assets": balances,
        "pool_gaps": gaps,
        "tradeable_pairs": [
            "MN2/USDT", "MN2/USDC", "USDT/MN2", "USDC/MN2",
        ],
        "swap_back_hint": "Sell USDT or USDC (quote MN2) to swap back into MN2 coins, or sell MN2 for USDT/USDC.",
        "min_pool_by_asset": cfg.get("min_pool_by_asset") or {},
        "paper_seeded": bool(state.get("paper_seeded")),
        "last_tick_at": state.get("last_tick_at"),
        "tick_count": int(state.get("tick_count") or 0),
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


def run_mn2_pool_agent_tick(*, force: bool = False) -> Dict[str, Any]:
    cfg = load_config()
    if not cfg.get("enabled", True) and not force:
        return {"success": True, "skipped": True, "reason": "disabled"}

    if _cooldown_active(cfg, force=force):
        return {
            "success": True,
            "skipped": True,
            "reason": "cooldown",
            "tick_cooldown_seconds": int(cfg.get("tick_cooldown_seconds") or 120),
        }

    ensure_paper_seed()
    state = _read_state()
    gaps_before = pool_gaps()

    sweep_result: Dict[str, Any] = {"skipped": True}
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
        "gaps_before": gaps_before,
        "sweep": sweep_result,
        "seed": seed_result,
        "rebalance": rebalance_result,
        "status": status,
    }
