#!/usr/bin/env python3
"""
Backfill missing p2p_sell_escrow ledger rows for open external listings (legacy drift).

Dry-run by default. Use --apply to append ledger entries (does not move balances;
escrow was already deducted when listings were created).

Run on server: cd /var/www/html && python3 scripts/mn2_reconcile_repair_p2p_escrow.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    from backend.services.mn2_proof_of_reserves_service import external_liability_user_ids
    from backend.services import mn2_ledger

    data = os.path.join(ROOT, "data", "mn2_p2p_listings.json")
    if not os.path.isfile(data):
        print("no listings file")
        return 0
    listings = json.load(open(data, encoding="utf-8")) or {}
    entries = []
    ledger_path = os.path.join(ROOT, "data", "mn2_ledger.json")
    if os.path.isfile(ledger_path):
        raw = json.load(open(ledger_path, encoding="utf-8"))
        entries = raw.get("entries", []) if isinstance(raw, dict) else raw

    escrowed = sum(float(e.get("amount") or 0) for e in entries if e.get("type") == "p2p_sell_escrow")
    returned = sum(float(e.get("amount") or 0) for e in entries if e.get("type") == "p2p_escrow_return")
    delivered = sum(float(e.get("amount") or 0) for e in entries if e.get("type") == "p2p_buy")
    expected = round(escrowed - returned - delivered, 8)

    outstanding = 0.0
    repairs = []
    for lid, listing in listings.items():
        if not isinstance(listing, dict):
            continue
        if listing.get("status") not in ("open", "sold_out"):
            continue
        sid = listing.get("seller_id") or listing.get("user_id") or ""
        if sid not in external_liability_user_ids():
            continue
        amt = round(
            float(listing.get("mn2_available", 0) or 0) + float(listing.get("mn2_reserved", 0) or 0),
            8,
        )
        if amt <= 0:
            continue
        outstanding = round(outstanding + amt, 8)
        repairs.append((lid, sid, amt))

    drift = round(outstanding - expected, 8)
    print(f"outstanding_listings={outstanding} ledger_expected={expected} drift={drift}")
    if abs(drift) <= 1e-6:
        print("no repair needed")
        return 0
    if drift < 0:
        print("WARN: ledger exceeds listings — manual review")
        return 2

    for lid, sid, amt in repairs:
        print(f"  backfill listing {lid} seller={sid} mn2={amt}")
        if args.apply:
            mn2_ledger.append_entry(
                sid,
                "p2p_sell_escrow",
                amt,
                metadata={"listing_id": lid, "repair": "mn2_reconcile_repair_p2p_escrow"},
            )
    if not args.apply:
        print("dry-run only — pass --apply to write ledger entries")
        return 1
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
