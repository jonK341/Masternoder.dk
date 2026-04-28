"""
Append-only payment ledger for PayPal (and later subscriptions) — enables attribution for §0 phase C.

Writes: logs/monetization/payment_ledger.jsonl (one JSON object per capture).
No DB migration required; use for reporting gross margin vs COGS when joined with metering.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _ledger_path() -> str:
    base = os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "logs",
    )
    return os.path.join(base, "monetization", "payment_ledger.jsonl")


def payment_ledger_file_path() -> str:
    """Absolute path to append-only payment ledger (SCR + PayPal + subs)."""
    return _ledger_path()


def append_payment_event(
    *,
    provider: str,
    user_id: str,
    order_id: str,
    capture_id: Optional[str],
    amount_usd: float,
    currency: str,
    item_id: str,
    item_name: str,
    coins_granted: int = 0,
    generation_credits_granted: float = 0.0,
    subscription_id: Optional[str] = None,
    deal_kind: Optional[str] = None,
    invoice_ref: Optional[str] = None,
    org_label: Optional[str] = None,
    studio_sku_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Best-effort append; never raises.

    SCR (§4): optional deal_kind, invoice_ref, org_label, studio_sku_id for B2B / invoice / wire lines.
    """
    try:
        path = _ledger_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "provider": provider,
            "user_id": user_id,
            "paypal_order_id": order_id,
            "paypal_capture_id": capture_id,
            "subscription_id": subscription_id,
            "amount_usd": float(amount_usd or 0),
            "currency": currency or "USD",
            "item_id": item_id,
            "item_name": item_name,
            "coins_granted": int(coins_granted),
            "generation_credits_granted": float(generation_credits_granted or 0),
        }
        if deal_kind:
            row["deal_kind"] = str(deal_kind).strip()
        if invoice_ref:
            row["invoice_ref"] = str(invoice_ref).strip()[:512]
        if org_label:
            row["org_label"] = str(org_label).strip()[:256]
        if studio_sku_id:
            row["studio_sku_id"] = str(studio_sku_id).strip()[:128]
        if extra:
            row["extra"] = extra
        line = json.dumps(row, ensure_ascii=False, default=str) + "\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
