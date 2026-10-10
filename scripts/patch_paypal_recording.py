#!/usr/bin/env python3
"""
Patch backend/routes/paypal_routes.py so real money is actually recorded.

WHY
  The PayPal API integration already works, but the capture handler drops the
  fiat facts: it never writes price_paid_usd / payment_method / payment_ref /
  purchase_status, coin-pack and MN2-pack payments create no shop_purchases row
  at all, a replayed capture can grant twice, and create-order trusts a
  client-supplied amount. This patch closes all four.

HOW
  Four anchored, indentation-aware insertions. No existing line is deleted or
  rewritten. If an anchor does not match EXACTLY ONCE the patch aborts and
  leaves the file untouched, so a drifted file can never be half-patched.

USAGE (from /var/www/html)
  .venv/bin/python scripts/patch_paypal_recording.py --dry-run   # show plan (DEFAULT)
  .venv/bin/python scripts/patch_paypal_recording.py --apply     # write (+ .bak)
"""
from __future__ import annotations

import argparse
import os
import py_compile
import shutil
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = os.path.join(REPO, "backend", "routes", "paypal_routes.py")
SERVICE = os.path.join(REPO, "backend", "services", "fiat_payment_service.py")
MARKER = "_expected_price_usd"

# Each block is written at column 0; the patcher re-indents every non-blank
# line to match the anchor's own indentation.
EDITS = [
    {
        "name": "A: server-side price helper",
        "anchor": '@paypal_bp.route("/api/paypal/create-order", methods=["POST"])',
        "where": "before",
        "blank_after": 2,
        "block": '''# Only keys that are unambiguously USD. A bare "price" may be a coin price,
# and charging 2000 USD for a 2000-coin item is worse than not overriding.
_USD_PRICE_KEYS = ("price_usd", "usd_price", "amount_usd", "usd")


def _expected_price_usd(item_id):
    """Server-side catalog price for item_id, or None if it has no USD price.

    Used instead of the client-supplied amount so a tampered request cannot
    create a cheap order for an expensive item. Returns None (caller keeps the
    client amount) whenever the catalog price cannot be resolved confidently.
    """
    if not item_id:
        return None
    try:
        from backend.routes.shop_routes import (
            get_coin_pack_map, get_mn2_pack_map, _get_paypal_shop_items,
        )
    except Exception:
        return None
    for lookup in (get_coin_pack_map, get_mn2_pack_map, _get_paypal_shop_items):
        try:
            item = (lookup() or {}).get(item_id)
        except Exception:
            item = None
        if not item:
            continue
        for key in _USD_PRICE_KEYS:
            try:
                price = float(item.get(key) or 0)
            except (TypeError, ValueError):
                price = 0.0
            if price > 0:
                return price
    return None''',
    },
    {
        "name": "B: create-order ignores client amount for catalog items",
        "anchor": "if amount <= 0:",
        "where": "before",
        "blank_after": 1,
        "block": '''# Never trust a client-supplied price for a catalog item.
expected_usd = _expected_price_usd(item_id)
if expected_usd is not None:
    amount = expected_usd''',
    },
    {
        "name": "C: capture idempotency + fiat record",
        "anchor": "fulfillment_error = None",
        "where": "after",
        "blank_before": 1,
        "block": '''capture_id = result.get("capture_id") or order_id
currency = str(result.get("currency") or "USD")
expected_usd = _expected_price_usd(item_id)
purchase_id = None

# The money is already captured at this point, so a missing or broken fiat
# service must degrade to "not recorded" -- never to a 500 that loses the grant.
fiat = None
try:
    from backend.services import fiat_payment_service as fiat
except Exception as fiat_import_err:
    print(f"[paypal] fiat_payment_service unavailable: {fiat_import_err}")

if fiat is not None:
    # A capture can arrive twice (client retry + webhook). Pay out only once.
    if fiat.already_fulfilled(capture_id):
        return jsonify({
            "success": True,
            "order_id": order_id,
            "capture_id": capture_id,
            "duplicate": True,
            "message": "payment already processed",
        }), 200

    fiat.record_fiat_payment(
        capture_id=capture_id,
        order_id=order_id,
        user_id=user_id,
        item_id=item_id,
        item_name=item_name,
        quantity=1,
        amount=amount,
        currency=currency,
        status="captured",
        price_expected=expected_usd,
        raw=result,
    )''',
    },
    {
        "name": "D: write fiat columns + purchase row after grant",
        "anchor": "# Notify admin of purchase (email + log)",
        "where": "before",
        "blank_after": 1,
        "block": '''# ---- record the fiat side (idempotent on capture_id) ----
if fiat is not None:
    try:
        granted_kind = None
        granted_amount = None
        if mn2_granted:
            granted_kind, granted_amount = "mn2", float(mn2_granted)
        elif coins_granted:
            granted_kind, granted_amount = "coins", float(coins_granted)
        elif item_granted:
            granted_kind, granted_amount = "item", 1.0
        elif amount > 0:
            granted_kind, granted_amount = "monetization_points", float(amount) * 100

        if purchase_id:
            fiat.attach_fiat_to_purchase(
                purchase_id, amount_usd=amount, capture_id=capture_id,
                order_id=order_id, status="paid",
            )
        else:
            purchase_id = fiat.record_fiat_purchase_row(
                user_id=user_id,
                item_id=item_id,
                item_name=item_name or (pack or {}).get("name") or (mn2_pack or {}).get("name") or "",
                amount_usd=amount,
                capture_id=capture_id,
                currency=currency,
            )
        fiat.update_fiat_grant(
            capture_id, granted_kind, granted_amount,
            purchase_id=purchase_id,
            status="captured" if fulfillment_error else "completed",
        )
    except Exception as fiat_err:
        # Reporting only: the grant above already happened, so do not turn a
        # bookkeeping failure into "manual_fulfillment_required".
        print(f"[paypal] fiat recording failed for {capture_id}: {fiat_err}")''',
    },
]


def indent_of(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def reindent(block: str, indent: str) -> list:
    out = []
    for ln in block.split("\n"):
        out.append(indent + ln if ln.strip() else "")
    return out


def find_anchor(lines: list, anchor: str) -> list:
    return [i for i, ln in enumerate(lines) if ln.strip() == anchor]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write the patch")
    ap.add_argument("--dry-run", action="store_true", help="show the plan only (default)")
    ap.add_argument("--file", default=TARGET, help="override target path")
    args = ap.parse_args()

    target = args.file if os.path.isabs(args.file) else os.path.abspath(args.file)
    print("=" * 70)
    print("PAYPAL RECORDING PATCH")
    print("=" * 70)
    print(f"target  : {target}")
    print(f"service : {SERVICE}")
    print(f"mode    : {'APPLY' if args.apply else 'DRY-RUN'}")
    print()

    if not os.path.exists(target):
        print(f"ERROR: target not found: {target}")
        return 2
    if not os.path.exists(SERVICE):
        print("ERROR: backend/services/fiat_payment_service.py is missing.")
        print("       Install it first (Block 17 step 1) -- the patch imports it.")
        return 2

    with open(target, "r", encoding="utf-8") as fh:
        original = fh.read()
    lines = original.split("\n")

    if MARKER in original:
        print("ALREADY PATCHED -- nothing to do.")
        print(f"  (marker '{MARKER}' present)")
        return 0

    # validate every anchor before touching anything
    problems = []
    resolved = []
    for edit in EDITS:
        hits = find_anchor(lines, edit["anchor"])
        if len(hits) != 1:
            problems.append(
                f"{edit['name']}: anchor matched {len(hits)} times (need exactly 1): "
                f"{edit['anchor']!r}"
            )
            continue
        resolved.append((edit, hits[0]))

    if problems:
        print("ANCHOR PROBLEMS -- refusing to patch (file left untouched):")
        for p in problems:
            print(f"  !! {p}")
        print()
        print("The live file has drifted from the version this patch was written")
        print("against. Send me the current paypal_routes.py and I will re-anchor.")
        return 1

    # apply from the bottom up so earlier insertions do not shift later indexes
    for edit, idx in sorted(resolved, key=lambda t: t[1], reverse=True):
        indent = indent_of(lines[idx])
        new = reindent(edit["block"], indent)
        pad_before = [""] * edit.get("blank_before", 0)
        pad_after = [""] * edit.get("blank_after", 0)
        if edit["where"] == "before":
            lines[idx:idx] = new + pad_after
        else:
            lines[idx + 1:idx + 1] = pad_before + new

    patched = "\n".join(lines)

    print(f"EDITS ({len(resolved)}):")
    for edit, idx in sorted(resolved, key=lambda t: t[1]):
        print(f"  + {edit['name']}")
        print(f"      anchor line {idx + 1}: {edit['anchor'][:60]}")
        print(f"      insert {edit['where']}, {len(edit['block'].split(chr(10)))} line(s)")
    print()
    print(f"line count: {len(original.split(chr(10)))} -> {len(patched.split(chr(10)))}")
    print()

    if not args.apply:
        print("Dry-run only. No file was written. Re-run with --apply.")
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bak = f"{target}.bak.{stamp}"
    shutil.copy2(target, bak)
    print(f"backup: {bak}")

    with open(target, "w", encoding="utf-8", newline="") as fh:
        fh.write(patched)

    try:
        py_compile.compile(target, doraise=True)
        print("COMPILE_OK")
    except Exception as e:
        print(f"COMPILE FAILED -- restoring backup: {e}")
        shutil.copy2(bak, target)
        print("restored. File is back to its original state.")
        return 1

    print()
    print("PATCHED OK")
    print("Next: restart the app so the new code loads, e.g.")
    print("  systemctl restart uwsgi   (or: systemctl restart masternoder)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
