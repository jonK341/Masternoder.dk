#!/usr/bin/env python3
"""Process resting exchange limit orders that can never fill.

The treasury liquidity pipeline (``exchange_treasury_liquidity_service.run_liquidity_tick``)
parks MN2 *sell* limit orders quoted in COINS for the market-maker agent. The live
trade flow is swap-based and never posts COINS-quoted MN2 *buy* orders, so these sells
accumulate as a one-directional book that locks the agent's MN2 indefinitely.

This tool "processes" that book: for every ``(symbol, quote)`` pair whose open orders
are entirely one-sided (no possible counterparty), it cancels the resting orders via the
exchange engine's own ``cancel_order`` — releasing the locked balance back to each owner.

Safe by default: runs a DRY-RUN unless ``--apply`` is passed.

    python scripts/process_open_liquidity_orders.py            # preview
    python scripts/process_open_liquidity_orders.py --apply     # execute
    python scripts/process_open_liquidity_orders.py --apply --symbol MN2 --quote COINS
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services import crypto_exchange_service as ex  # noqa: E402


def _one_directional_open_orders(symbol=None, quote=None):
    """Return open orders whose (symbol, quote) book has only one active side."""
    open_orders = [o for o in ex._read_orders() if o.get("status") == "open"]
    sides_by_book = defaultdict(set)
    for o in open_orders:
        sides_by_book[(o.get("symbol"), o.get("quote"))].add(o.get("side"))

    targets = []
    for o in open_orders:
        book = (o.get("symbol"), o.get("quote"))
        if len(sides_by_book[book]) != 1:
            continue  # book has both sides -> matchable, leave it alone
        if symbol and o.get("symbol") != symbol.upper():
            continue
        if quote and o.get("quote") != quote.upper():
            continue
        targets.append(o)
    return targets


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="actually cancel (default: dry-run)")
    ap.add_argument("--symbol", help="restrict to a single symbol, e.g. MN2")
    ap.add_argument("--quote", help="restrict to a single quote currency, e.g. COINS")
    args = ap.parse_args()

    targets = _one_directional_open_orders(args.symbol, args.quote)
    if not targets:
        print("No one-directional resting orders to process.")
        return 0

    by_owner = defaultdict(lambda: [0, 0.0])
    for o in targets:
        by_owner[o.get("user_id")][0] += 1
        by_owner[o.get("user_id")][1] += float(o.get("remaining") or 0)

    total_rem = sum(float(o.get("remaining") or 0) for o in targets)
    books = sorted({(o.get("symbol"), o.get("side"), o.get("quote")) for o in targets})
    print(f"{'APPLY' if args.apply else 'DRY-RUN'}: {len(targets)} resting orders in one-directional books")
    print(f"  books: {books}")
    print(f"  total locked (base units, per symbol): {total_rem:,.6f}")
    for owner, (cnt, rem) in sorted(by_owner.items(), key=lambda kv: -kv[1][0]):
        print(f"  {owner:<34} {cnt:>4} orders   {rem:,.6f} locked")

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to cancel and release locked balances.")
        return 0

    ok, failed = 0, []
    for o in targets:
        res = ex.cancel_order(o.get("user_id"), o.get("order_id"))
        if res.get("success"):
            ok += 1
        else:
            failed.append((o.get("order_id"), res.get("error")))

    remaining_open = len([x for x in ex._read_orders() if x.get("status") == "open"])
    print(f"\nCancelled {ok}/{len(targets)} orders. Failures: {len(failed)}")
    for oid, err in failed[:20]:
        print(f"  FAIL {oid}: {err}")
    print(f"Open orders remaining in book: {remaining_open}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
