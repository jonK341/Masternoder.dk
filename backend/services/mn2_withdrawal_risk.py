"""
MN2 withdrawal anomaly detection (plan §20 #21/#22, Top-10 #3).

Scores each withdrawal attempt against simple, explainable signals and recommends a
step-up (re-prove password) or a hard stop. This complements the §9.2 controls
(server-resolved identity, password gate, new-address cooling-off): even when a user
has turned real-money password protection OFF, a risky withdrawal re-imposes a
verification challenge — so a hijacked session can't quietly drain an account with
a burst of, or one large, transfer.

Signals (all from the append-only ledger + current balance — no new state):
  - new payout address (never withdrawn there before)
  - large absolute amount
  - large fraction of the user's balance
  - velocity: several withdrawals inside a short window

Returns a structured assessment; the route maps it to allow / step_up / block.
Every assessment is appended to logs/mn2_withdrawal_risk.jsonl for ops review.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOG_PATH = os.path.join(_BASE_DIR, "logs", "mn2_withdrawal_risk.jsonl")

_DEFAULTS = {
    "enabled": True,
    "step_up_score": 2,
    "block_score": 5,
    "large_amount_mn2": 50000.0,
    "large_balance_fraction": 0.5,
    "velocity_window_minutes": 60,
    "velocity_count_threshold": 2,
}


def _cfg(config: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(_DEFAULTS)
    try:
        out.update({k: v for k, v in (config.get("withdrawal_risk") or {}).items() if v is not None})
    except Exception:
        pass
    return out


def _recent_withdrawals(user_id: str, window_minutes: int):
    """Return (count_in_window, prior_addresses_set) from the ledger."""
    try:
        from backend.services.mn2_ledger import get_entries_by_user
        entries = get_entries_by_user(user_id, limit=500)
    except Exception:
        return 0, set()
    since = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()
    count = 0
    addresses = set()
    for e in entries:
        if e.get("type") != "withdrawal":
            continue
        addr = (e.get("address") or "").strip()
        if addr:
            addresses.add(addr)
        ca = (e.get("created_at") or "").replace("Z", "+00:00")
        if ca >= since:
            count += 1
    return count, addresses


def assess(user_id: str, address: str, amount: float, balance: float, config: Dict[str, Any]) -> Dict[str, Any]:
    cfg = _cfg(config)
    if not cfg.get("enabled", True):
        return {"enabled": False, "score": 0, "level": "low", "reasons": [],
                "require_step_up": False, "hard_block_if_no_password": False}

    reasons = []
    score = 0
    addr = (address or "").strip()
    amount = float(amount or 0)
    balance = float(balance or 0)

    velocity_count, prior_addresses = _recent_withdrawals(user_id, int(cfg["velocity_window_minutes"]))

    if addr and addr not in prior_addresses:
        score += 1
        reasons.append("new payout address")

    if amount >= float(cfg["large_amount_mn2"]):
        score += 2
        reasons.append(f"large amount (\u2265 {cfg['large_amount_mn2']:g} MN2)")

    frac = float(cfg["large_balance_fraction"])
    if balance > 0 and frac > 0 and amount >= balance * frac:
        score += 1
        reasons.append(f"\u2265 {int(frac * 100)}% of balance")

    vthr = int(cfg["velocity_count_threshold"])
    if velocity_count >= vthr:
        score += 2
        reasons.append(f"{velocity_count} withdrawals in {cfg['velocity_window_minutes']}m")
        if velocity_count >= vthr * 2:
            score += 1
            reasons.append("rapid repeated withdrawals")

    result_extra: Dict[str, Any] = {}
    try:
        from backend.services.mn2_sybil_graph import score_user
        sybil = score_user(user_id)
        if sybil.get("elevated"):
            score += 2
            reasons.append(f"sybil cluster size {sybil.get('cluster_size')}")
        result_extra = {"sybil_score": sybil.get("sybil_score", 0), "cluster_size": sybil.get("cluster_size")}
    except Exception:
        pass

    if score >= int(cfg["block_score"]):
        level = "high"
    elif score >= int(cfg["step_up_score"]):
        level = "elevated"
    else:
        level = "low"

    result = {
        "enabled": True,
        "score": score,
        "level": level,
        "reasons": reasons,
        "velocity_count": velocity_count,
        "require_step_up": level in ("elevated", "high"),
        "hard_block_if_no_password": level == "high",
        **result_extra,
    }
    _log(user_id, addr, amount, result)
    return result


def _log(user_id: str, address: str, amount: float, result: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
        row = {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "user_id": user_id,
            "address": address,
            "amount_mn2": round(float(amount or 0), 8),
            "score": result.get("score"),
            "level": result.get("level"),
            "reasons": result.get("reasons"),
        }
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass
