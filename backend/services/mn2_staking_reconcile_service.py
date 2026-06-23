"""
MN2 staking reconciliation & conservation invariant (plan sec.8).

Reads the canonical stores and verifies the money actually adds up:
  - rewards ledger match: Σ reward rows == Σ `staking_reward` ledger entries
  - staked invariant:     Σ live staked == Σ `stake` − Σ `unstake` ledger entries
  - on-ramp match:        Σ funded order MN2 == Σ `onramp_purchase`; clawbacks match
  - P2P escrow conservation: outstanding listing escrow == escrowed − returned − delivered
  - no-pay-over-yield:    lifetime paid ≤ realized yield − margin (only meaningful in realized-yield mode)

Returns a structured report; `ok` is False if any hard check drifts beyond tolerance.
Surfaced at /api/mn2/staking/ops/reconcile and via scripts/mn2_reconcile.py.
"""
import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

_TOLERANCE = 1e-6


def _base_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _data_path(name: str) -> str:
    return os.path.join(_base_dir(), "data", name)


def _read_json(name: str, default: Any) -> Any:
    p = _data_path(name)
    if not os.path.exists(p):
        return default
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _read_jsonl(name: str) -> List[Dict[str, Any]]:
    p = _data_path(name)
    rows: List[Dict[str, Any]] = []
    if not os.path.exists(p):
        return rows
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
    except Exception:
        pass
    return rows


def _ledger_entries() -> List[Dict[str, Any]]:
    data = _read_json("mn2_ledger.json", {})
    if isinstance(data, dict):
        return data.get("entries", []) or []
    return data if isinstance(data, list) else []


def _sum_ledger(entries: List[Dict[str, Any]], entry_type: str) -> float:
    return round(sum(float(e.get("amount", 0) or 0) for e in entries if e.get("type") == entry_type), 8)


def _check(name: str, expected: float, actual: float, hard: bool = True, note: str = "") -> Dict[str, Any]:
    drift = round(actual - expected, 8)
    return {
        "name": name,
        "expected": round(expected, 8),
        "actual": round(actual, 8),
        "drift": drift,
        "ok": abs(drift) <= _TOLERANCE,
        "hard": hard,
        "note": note,
    }


def reconcile() -> Dict[str, Any]:
    entries = _ledger_entries()
    checks: List[Dict[str, Any]] = []

    # 1. Reward rows == staking_reward ledger
    reward_rows = _read_jsonl("mn2_staking_rewards.jsonl")
    rows_sum = round(sum(float(r.get("reward_mn2", 0) or 0) for r in reward_rows), 8)
    ledger_reward = _sum_ledger(entries, "staking_reward")
    checks.append(_check("rewards_rows_match_ledger", ledger_reward, rows_sum,
                         note="Σ reward rows vs Σ staking_reward ledger entries"))

    # 2. Live staked == Σ stake − Σ unstake
    stakes = _read_json("mn2_stakes.json", {})
    live_staked = round(sum(float((r or {}).get("staked", 0) or 0) for r in stakes.values()), 8) if isinstance(stakes, dict) else 0.0
    ledger_staked = round(_sum_ledger(entries, "stake") - _sum_ledger(entries, "unstake"), 8)
    checks.append(_check("staked_matches_ledger", ledger_staked, live_staked,
                         note="Σ live staked vs (Σ stake − Σ unstake) ledger"))

    # 3. On-ramp: funded MN2 == onramp_purchase ledger; clawbacks match
    onramp_orders = _read_json("mn2_onramp_orders.json", {})
    if isinstance(onramp_orders, dict):
        funded_mn2 = round(sum(float(o.get("mn2_amount", 0) or 0) for o in onramp_orders.values()
                               if o.get("status") in ("held", "cleared")), 8)
        clawed = round(sum(float(o.get("clawed_back_mn2", 0) or 0) for o in onramp_orders.values()
                           if o.get("status") == "charged_back"), 8)
    else:
        funded_mn2 = clawed = 0.0
    checks.append(_check("onramp_purchase_match_ledger", _sum_ledger(entries, "onramp_purchase"), funded_mn2,
                         note="Σ funded on-ramp MN2 vs onramp_purchase ledger"))
    checks.append(_check("onramp_clawback_match_ledger", _sum_ledger(entries, "onramp_clawback"), clawed,
                         note="Σ on-ramp clawed-back MN2 vs onramp_clawback ledger"))

    # 4. P2P escrow conservation
    listings = _read_json("mn2_p2p_listings.json", {})
    if isinstance(listings, dict):
        outstanding_escrow = round(sum(float(l.get("mn2_available", 0) or 0) + float(l.get("mn2_reserved", 0) or 0)
                                       for l in listings.values() if l.get("status") in ("open", "sold_out")), 8)
    else:
        outstanding_escrow = 0.0
    escrowed = _sum_ledger(entries, "p2p_sell_escrow")
    returned = _sum_ledger(entries, "p2p_escrow_return")
    delivered = _sum_ledger(entries, "p2p_buy")
    expected_escrow = round(escrowed - returned - delivered, 8)
    checks.append(_check("p2p_escrow_conservation", expected_escrow, outstanding_escrow,
                         note="outstanding listing escrow vs (escrowed − returned − delivered to buyers)"))

    # 5. No-pay-over-yield (informational unless realized-yield mode with realized data)
    reserve = _read_json("mn2_staking_reserve.json", {})
    lifetime_paid = float(reserve.get("lifetime_paid", 0) or 0) if isinstance(reserve, dict) else 0.0
    lifetime_yield = float(reserve.get("lifetime_realized_yield", 0) or 0) if isinstance(reserve, dict) else 0.0
    try:
        from backend.services.mn2_staking_service import get_config
        realized_mode = get_config().get("reward_pool_mode") == "realized_yield"
        margin = float(get_config().get("site_margin_percent", 0)) / 100.0
    except Exception:
        realized_mode, margin = False, 0.0
    pay_over_yield = realized_mode and lifetime_yield > 0 and lifetime_paid > lifetime_yield * (1.0 - margin) + _TOLERANCE
    checks.append({
        "name": "no_pay_over_realized_yield",
        "expected_max": round(lifetime_yield * (1.0 - margin), 8) if lifetime_yield > 0 else None,
        "actual": round(lifetime_paid, 8),
        "ok": not pay_over_yield,
        "hard": realized_mode and lifetime_yield > 0,
        "note": "lifetime paid must not exceed realized yield − margin (APR-fallback dev mode is exempt)",
    })

    hard_fail = [c for c in checks if c.get("hard") and not c.get("ok")]
    return {
        "success": True,
        "ok": len(hard_fail) == 0,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "tolerance": _TOLERANCE,
        "checks": checks,
        "failed_checks": [c["name"] for c in hard_fail],
        "totals": {
            "live_staked": live_staked,
            "lifetime_reward_paid": round(lifetime_paid, 8),
            "lifetime_realized_yield": round(lifetime_yield, 8),
            "reserve_mn2": round(float(reserve.get("reserve_mn2", 0) or 0), 8) if isinstance(reserve, dict) else 0.0,
            "p2p_outstanding_escrow": outstanding_escrow,
            "onramp_funded_mn2": funded_mn2,
        },
    }
