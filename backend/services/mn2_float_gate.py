"""
Hot-wallet float sufficiency gate for withdrawals and PoR claims.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List


def _load_config() -> Dict[str, Any]:
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "data",
        "mn2_config.json",
    )
    defaults = {"float_gate": {"enabled": True, "min_hours_coverage": 24, "large_withdrawal_mn2": 50000}}
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


def assess(amount_mn2: float = 0) -> Dict[str, Any]:
    cfg = _load_config().get("float_gate") or {}
    if not cfg.get("enabled", True):
        return {"success": True, "allowed": True, "skipped": True}

    hot = None
    try:
        from backend.services.mn2_proof_of_reserves_service import proof_of_reserves
        por = proof_of_reserves(force=False)
        onchain = por.get("assets", {}).get("onchain") or {}
        hot = onchain.get("total")
    except Exception:
        pass

    p95 = _p95_daily_outflow_mn2()
    hours = float(cfg.get("min_hours_coverage") or 24)
    required_float = round(p95 * (hours / 24.0), 8)
    large = float(cfg.get("large_withdrawal_mn2") or 50000)

    if hot is None:
        return {"success": True, "allowed": True, "oracle_skipped": True, "reason": "onchain unavailable"}

    sufficient = float(hot) >= required_float
    block_large = float(amount_mn2 or 0) >= large and not sufficient

    return {
        "success": True,
        "allowed": not block_large,
        "hot_mn2": round(float(hot), 8),
        "required_float_mn2": required_float,
        "p95_daily_outflow_mn2": p95,
        "min_hours_coverage": hours,
        "verdict": "green" if sufficient else "red",
        "code": None if not block_large else "float_insufficient",
    }
