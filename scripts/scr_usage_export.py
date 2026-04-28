#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCR usage export (§4): CSV rollups from payment_ledger.jsonl + metering.jsonl.

Produces:
  - metering_jobs.csv — one row per completed job with org_label, ratio, generation_credits_burned
  - ledger_scr.csv — b2b_scr rows (manual / invoice settlement)
  - org_pool_summary.csv — per org_label: credits in/out/balance, USD in (matches get_org_pool_balance)

Usage:
  python scripts/scr_usage_export.py
  python scripts/scr_usage_export.py --ledger path/to/payment_ledger.jsonl --metering path/to/metering.jsonl --out-dir ./exports

For a quick JSON blended margin snapshot (no CSV), see scripts/monetization_scr_export.py.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import Any, Dict, Iterator, Set

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _iter_jsonl(path: str, *, max_lines: int = 2_000_000) -> Iterator[Dict[str, Any]]:
    if not path or not os.path.isfile(path):
        return
    n = 0
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


def _collect_org_labels(ledger_path: str, metering_path: str) -> List[str]:
    found: Set[str] = set()
    for row in _iter_jsonl(ledger_path):
        if (row.get("provider") or "") != "b2b_scr":
            continue
        ol = (row.get("org_label") or "").strip()
        if ol:
            found.add(ol)
    for row in _iter_jsonl(metering_path):
        ol = (row.get("org_label") or "").strip()
        if ol:
            found.add(ol)
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser(description="Export SCR ledger + metering join to CSV")
    parser.add_argument("--ledger", help="payment_ledger.jsonl (default: from monetization_ledger_service)")
    parser.add_argument("--metering", help="metering.jsonl (default: from cogs_metering_service)")
    parser.add_argument("--out-dir", default="exports", help="Output directory (created if needed)")
    args = parser.parse_args()

    os.chdir(_ROOT)
    from backend.services.cogs_metering_service import metering_jsonl_path
    from backend.services.monetization_config_service import get_credit_reference_fraction
    from backend.services.monetization_ledger_service import payment_ledger_file_path
    from backend.services.monetization_org_pool_service import get_org_pool_balance

    ledger_path = args.ledger or payment_ledger_file_path()
    metering_path = args.metering or metering_jsonl_path()
    ref_f = get_credit_reference_fraction()
    if ref_f <= 0:
        ref_f = 0.25

    out_dir = args.out_dir
    if not os.path.isabs(out_dir):
        out_dir = os.path.join(_ROOT, out_dir)
    os.makedirs(out_dir, exist_ok=True)

    # --- metering_jobs.csv
    m_out = os.path.join(out_dir, "metering_jobs.csv")
    m_fields = [
        "ts",
        "job_kind",
        "job_id",
        "user_id",
        "org_label",
        "ratio_vs_reference_job",
        "reference_fraction_per_credit",
        "generation_credits_burned",
        "cogs_total_usd",
        "llm_tokens_for_cogs",
        "llm_tokens_source",
    ]
    m_rows = 0
    with open(m_out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=m_fields, extrasaction="ignore")
        w.writeheader()
        for row in _iter_jsonl(metering_path):
            m_rows += 1
            ratio = row.get("ratio_vs_reference_job")
            gen_burn = ""
            if ratio is not None:
                try:
                    gen_burn = round(float(ratio) / ref_f, 6)
                except (TypeError, ValueError):
                    gen_burn = ""
            cogs = row.get("cogs_usd") or {}
            w.writerow({
                "ts": row.get("ts", ""),
                "job_kind": row.get("job_kind", ""),
                "job_id": row.get("job_id", ""),
                "user_id": row.get("user_id", ""),
                "org_label": (row.get("org_label") or "").strip(),
                "ratio_vs_reference_job": ratio if ratio is not None else "",
                "reference_fraction_per_credit": ref_f,
                "generation_credits_burned": gen_burn,
                "cogs_total_usd": cogs.get("total_usd", ""),
                "llm_tokens_for_cogs": row.get("llm_tokens_for_cogs", ""),
                "llm_tokens_source": row.get("llm_tokens_source", ""),
            })

    # --- ledger_scr.csv
    l_out = os.path.join(out_dir, "ledger_scr.csv")
    l_fields = [
        "ts",
        "provider",
        "user_id",
        "org_label",
        "amount_usd",
        "currency",
        "generation_credits_granted",
        "deal_kind",
        "invoice_ref",
        "studio_sku_id",
        "paypal_order_id",
        "item_id",
        "item_name",
    ]
    l_rows = 0
    with open(l_out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=l_fields, extrasaction="ignore")
        w.writeheader()
        for row in _iter_jsonl(ledger_path):
            if (row.get("provider") or "") != "b2b_scr":
                continue
            l_rows += 1
            w.writerow({k: row.get(k, "") for k in l_fields})

    # --- org_pool_summary.csv
    orgs = _collect_org_labels(ledger_path, metering_path)
    s_out = os.path.join(out_dir, "org_pool_summary.csv")
    summary_fields = [
        "org_label",
        "generation_credits_in",
        "generation_credits_out",
        "generation_credits_balance",
        "amount_usd_b2b_in",
        "reference_fraction_per_credit",
    ]
    with open(s_out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=summary_fields)
        w.writeheader()
        for ol in orgs:
            bal = get_org_pool_balance(ol, ledger_path=ledger_path, metering_path=metering_path)
            w.writerow({
                "org_label": bal.get("org_label", ol),
                "generation_credits_in": bal.get("generation_credits_in", ""),
                "generation_credits_out": bal.get("generation_credits_out", ""),
                "generation_credits_balance": bal.get("generation_credits_balance", ""),
                "amount_usd_b2b_in": bal.get("amount_usd_b2b_in", ""),
                "reference_fraction_per_credit": bal.get("reference_fraction_per_credit", ref_f),
            })

    print("SCR usage export")
    print("  ledger:  ", ledger_path, f"({l_rows} b2b_scr rows written)")
    print("  metering:", metering_path, f"({m_rows} rows written)")
    print("  orgs:    ", len(orgs), "distinct org_label values in ledger|metering")
    print("  output:  ", out_dir)
    print("    - metering_jobs.csv")
    print("    - ledger_scr.csv")
    print("    - org_pool_summary.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
