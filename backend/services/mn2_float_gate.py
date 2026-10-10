"""
Hot-wallet float sufficiency gate for withdrawals and PoR claims.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional


def _load_config() -> Dict[str, Any]:
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
        "mn2_config.json",
    )
    defaults = {
        "float_gate": {
            "enabled": True,
            "min_hours_coverage": 24,
            "large_withdrawal_mn2": 50000,
            "require_external_coverage": True,
            "min_external_coverage_ratio": 1.0,
        }
    }
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f) or {}
            fg = raw.get("float_gate") if isinstance(raw.get("float_gate"), dict) else {}
            defaults["float_gate"].update({k: v for k, v in fg.items() if v is not None})
        except Exception:
            pass
    return defaults


def _p95_daily_outflow_mn2() -> float:
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
        "mn2_ledger.json",
    )
    if not os.path.isfile(path):
        return 0.0
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = data.get("entries") if isinstance(data, dict) else data
        if not isinstance(entries, list):
            return 0.0
    except Exception:
        return 0.0
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    daily: Dict[str, float] = {}
    for e in entries:
        if e.get("type") != "withdrawal":
            continue
        if (e.get("created_at") or "") < cutoff:
            continue
        day = str(e.get("created_at") or "")[:10]
        daily[day] = daily.get(day, 0) + float(e.get("amount") or 0)
    if not daily:
        return 0.0
    vals = sorted(daily.values())
    idx = min(len(vals) - 1, int(len(vals) * 0.95))
    return round(vals[idx], 8)


def _hot_wallet_balance() -> Optional[float]:
    """Direct daemon balance — never recurse into proof_of_reserves."""
    try:
        from backend.services import mn2_rpc_client as rpc
        wi = rpc.getwalletinfo(timeout_sec=4)
        res = wi.get("result") if isinstance(wi, dict) else None
        if isinstance(res, dict) and res.get("balance") is not None:
            bal = float(res.get("balance") or 0)
            imm = float(res.get("immature_balance") or 0)
            unc = float(res.get("unconfirmed_balance") or 0)
            return round(bal + imm + unc, 8)
        gb = rpc.getbalance()
        if not gb.get("error") and gb.get("result") is not None:
            return round(float(gb.get("result") or 0), 8)
    except Exception:
        return None
    return None


def _external_liabilities_total() -> Optional[float]:
    try:
        from backend.services.mn2_proof_of_reserves_service import _sum_user_liabilities
        _liq, _st, _h, ext_liq, ext_st, _eh = _sum_user_liabilities()
        return round(float(ext_liq or 0) + float(ext_st or 0), 8)
    except Exception:
        return None


def assess(amount_mn2: float = 0, *, hot_mn2: Optional[float] = None) -> Dict[str, Any]:
    cfg = _load_config().get("float_gate") or {}
    if not cfg.get("enabled", True):
        return {"success": True, "allowed": True, "skipped": True}

    hot = hot_mn2
    if hot is None:
        hot = _hot_wallet_balance()

    p95 = _p95_daily_outflow_mn2()
    hours = float(cfg.get("min_hours_coverage") or 24)
    required_float = round(p95 * (hours / 24.0), 8)
    large = float(cfg.get("large_withdrawal_mn2") or 50000)
    amount = float(amount_mn2 or 0)

    if hot is None:
        # Fail closed for large withdrawals when the oracle is down.
        if amount >= large:
            return {
                "success": True,
                "allowed": False,
                "oracle_skipped": True,
                "reason": "onchain unavailable",
                "code": "float_oracle_unavailable",
                "verdict": "red",
            }
        return {
            "success": True,
            "allowed": True,
            "oracle_skipped": True,
            "reason": "onchain unavailable",
            "verdict": "unknown",
        }

    sufficient = float(hot) >= required_float
    block_large = amount >= large and not sufficient

    external_total = _external_liabilities_total()
    external_coverage = None
    coverage_block = False
    if (
        cfg.get("require_external_coverage", True)
        and external_total is not None
        and external_total > 0
        and hot is not None
    ):
        external_coverage = round(float(hot) / float(external_total), 6)
        min_ratio = float(cfg.get("min_external_coverage_ratio") or 1.0)
        if external_coverage < min_ratio and amount >= large:
            coverage_block = True

    allowed = not block_large and not coverage_block
    code = None
    if coverage_block:
        code = "external_coverage_insufficient"
    elif block_large:
        code = "float_insufficient"

    verdict = "green" if sufficient and not coverage_block else "red"
    return {
        "success": True,
        "allowed": allowed,
        "hot_mn2": round(float(hot), 8),
        "required_float_mn2": required_float,
        "p95_daily_outflow_mn2": p95,
        "min_hours_coverage": hours,
        "external_liabilities_mn2": external_total,
        "external_coverage_ratio": external_coverage,
        "verdict": verdict,
        "code": code,
    }
