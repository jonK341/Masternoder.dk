"""
Studio Cash Rail (§4): optional org-scoped prepaid pool vs metering burn.

Env:
  MONETIZATION_ORG_POOL_ENFORCEMENT=1 — reject generation when org balance (ledger in − metering out) is below reserve.
  MONETIZATION_ORG_POOL_MIN_CREDITS_PER_JOB — override minimum reservation (generation credits); default = 1 reference job worth (1 / reference_fraction_per_credit).

Resolution order for org label (same request may set one):
  config.scr_org_label, config.org_label, config.b2b_org_label
  user profile preferences.scr_org_label or preferences.b2b_org_label
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterator, Optional, Tuple

from backend.services.cogs_metering_service import metering_jsonl_path
from backend.services.monetization_config_service import get_credit_reference_fraction
from backend.services.monetization_ledger_service import payment_ledger_file_path


def _org_pool_enforcement_enabled() -> bool:
    return (os.environ.get("MONETIZATION_ORG_POOL_ENFORCEMENT") or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _norm_org(s: str) -> str:
    return (s or "").strip()


def resolve_scr_org_label(user_id: str, config: Optional[Dict[str, Any]]) -> Optional[str]:
    cfg = config if isinstance(config, dict) else {}
    for key in ("scr_org_label", "org_label", "b2b_org_label"):
        v = cfg.get(key)
        if v is not None and str(v).strip():
            return str(v).strip()[:256]
    try:
        from backend.services.user_onboarding import user_onboarding

        prof = user_onboarding.get_user_profile(user_id) if user_onboarding else None
        if prof:
            prefs = prof.get("preferences")
            if isinstance(prefs, str):
                prefs = json.loads(prefs or "{}")
            if isinstance(prefs, dict):
                for key in ("scr_org_label", "b2b_org_label"):
                    v = prefs.get(key)
                    if v is not None and str(v).strip():
                        return str(v).strip()[:256]
    except Exception:
        pass
    return None


def _iter_jsonl(path: str, *, max_lines: int = 500_000) -> Iterator[Dict[str, Any]]:
    if not path or not os.path.isfile(path):
        return
    n = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if n >= max_lines:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    n += 1
                    yield row
    except Exception:
        return


def _ledger_path_resolved(ledger_path: Optional[str]) -> str:
    return ledger_path or payment_ledger_file_path()


def _metering_path_resolved(metering_path: Optional[str]) -> str:
    return metering_path or metering_jsonl_path()


def sum_b2b_generation_credits_in_for_org(
    org_label: str,
    *,
    ledger_path: Optional[str] = None,
) -> float:
    """Sum generation_credits_granted from b2b_scr ledger rows with matching org_label."""
    target = _norm_org(org_label)
    if not target:
        return 0.0
    total = 0.0
    for row in _iter_jsonl(_ledger_path_resolved(ledger_path)):
        if (row.get("provider") or "") != "b2b_scr":
            continue
        ol = _norm_org(str(row.get("org_label") or ""))
        if ol != target:
            continue
        try:
            total += float(row.get("generation_credits_granted") or 0)
        except (TypeError, ValueError):
            continue
    return total


def sum_b2b_amount_usd_in_for_org(
    org_label: str,
    *,
    ledger_path: Optional[str] = None,
) -> float:
    """Sum amount_usd from b2b_scr rows with matching org_label (cash attributed to the deal)."""
    target = _norm_org(org_label)
    if not target:
        return 0.0
    total = 0.0
    for row in _iter_jsonl(_ledger_path_resolved(ledger_path)):
        if (row.get("provider") or "") != "b2b_scr":
            continue
        ol = _norm_org(str(row.get("org_label") or ""))
        if ol != target:
            continue
        try:
            total += float(row.get("amount_usd") or 0)
        except (TypeError, ValueError):
            continue
    return total


def sum_metering_generation_credits_out_for_org(
    org_label: str,
    *,
    metering_path: Optional[str] = None,
) -> float:
    """
    Sum burn in generation-credit units: ratio_vs_reference_job / reference_fraction_per_credit
    for metering rows tagged with org_label.
    """
    target = _norm_org(org_label)
    if not target:
        return 0.0
    ref_f = get_credit_reference_fraction()
    if ref_f <= 0:
        ref_f = 0.25
    total = 0.0
    for row in _iter_jsonl(_metering_path_resolved(metering_path)):
        ol = _norm_org(str(row.get("org_label") or ""))
        if ol != target:
            continue
        rj = row.get("ratio_vs_reference_job")
        if rj is None:
            continue
        try:
            ratio = float(rj)
        except (TypeError, ValueError):
            continue
        total += ratio / ref_f
    return total


def get_org_pool_balance(
    org_label: str,
    *,
    ledger_path: Optional[str] = None,
    metering_path: Optional[str] = None,
) -> Dict[str, Any]:
    cin = sum_b2b_generation_credits_in_for_org(org_label, ledger_path=ledger_path)
    cout = sum_metering_generation_credits_out_for_org(org_label, metering_path=metering_path)
    bal = cin - cout
    usd_in = sum_b2b_amount_usd_in_for_org(org_label, ledger_path=ledger_path)
    return {
        "org_label": _norm_org(org_label),
        "generation_credits_in": round(cin, 6),
        "generation_credits_out": round(cout, 6),
        "generation_credits_balance": round(bal, 6),
        "amount_usd_b2b_in": round(usd_in, 6),
        "reference_fraction_per_credit": get_credit_reference_fraction(),
    }


def estimate_min_generation_credits_for_job(config: Optional[Dict[str, Any]]) -> float:
    """Minimum balance required to start one job (conservative reservation)."""
    try:
        raw = (os.environ.get("MONETIZATION_ORG_POOL_MIN_CREDITS_PER_JOB") or "").strip()
        if raw:
            m = float(raw)
            if m > 0:
                return m
    except (TypeError, ValueError):
        pass
    ref_f = get_credit_reference_fraction()
    if ref_f <= 0:
        ref_f = 0.25
    return 1.0 / ref_f


def evaluate_org_pool_for_generation(
    user_id: str,
    config: Dict[str, Any],
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Returns (allowed, error_payload). When enforcement is off or user has no org, allows.
    """
    if not _org_pool_enforcement_enabled():
        return True, None
    org = resolve_scr_org_label(user_id, config)
    if not org:
        return True, None
    bal = get_org_pool_balance(org)
    reserve = estimate_min_generation_credits_for_job(config)
    if bal["generation_credits_balance"] + 1e-9 < reserve:
        return False, {
            "code": "ORG_POOL_EXHAUSTED",
            "http_status": 402,
            "message": (
                f"Studio pool for this organization has insufficient prepaid credits "
                f"(balance {bal['generation_credits_balance']:.2f} generation credits; "
                f"need at least ~{reserve:.2f} to start this job)."
            ),
            "org_label": org,
            "balance": bal,
            "reserve_estimate": reserve,
            "upsell": {"reason": "b2b_pool", "hint": "record-payment or extend SCR deal"},
        }
    return True, None
