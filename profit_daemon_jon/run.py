#!/usr/bin/env python3
"""The Profit Daemon Jon — branded entrypoint.

Usage:
  python profit_daemon_jon/run.py --once --profile paper
  python profit_daemon_jon/run.py --install-top25
  python profit_daemon_jon/run.py --status
  python profit_daemon_jon/run.py --sales --hours 3
  python profit_daemon_jon/run.py --backlog
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

BRAND = "The Profit Daemon Jon"


def _banner(extra: str = "") -> None:
    print("=" * 72)
    print(f"{BRAND}")
    if extra:
        print(extra)
    print("=" * 72)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=BRAND)
    parser.add_argument("--install-top25", action="store_true", help="Install/mark top-25 technologies")
    parser.add_argument("--no-pip", action="store_true", help="With --install-top25, skip pip installs")
    parser.add_argument("--status", action="store_true", help="Show product + top25 install status")
    parser.add_argument("--backlog", action="store_true", help="Show finished-product improvement backlog")
    parser.add_argument("--sales", action="store_true", help="Print sales report")
    parser.add_argument("--hours", type=float, default=3.0, help="Sales window hours")
    parser.add_argument("--json", action="store_true", help="JSON output for status/sales/backlog")
    parser.add_argument("--once", action="store_true", help="Single daemon tick then exit")
    parser.add_argument("--profile", default=None, help="Profit profile (paper/standard/max/live-only)")
    parser.add_argument("--skip-preflight", action="store_true")
    args, unknown = parser.parse_known_args(argv)

    os.chdir(ROOT)
    os.environ.setdefault("DAEMON_QUIET", "1")
    os.environ.setdefault("LITE_APP", "1")
    os.environ.setdefault("PROFIT_DAEMON_JON", "1")
    os.environ.setdefault("PROFIT_DAEMON_BRAND", BRAND)

    if args.install_top25:
        from backend.services.profit_daemon_jon_product_service import install_top25
        _banner("Installing top-25 technologies…")
        out = install_top25(pip=not args.no_pip)
        print(json.dumps(out if args.json else {
            "installed": out.get("installed"), "ok": out.get("ok"),
            "version": (out.get("product") or {}).get("version"),
            "state_path": out.get("state_path"),
        }, indent=2))
        return 0 if out.get("success") else 1

    if args.status:
        from backend.services.profit_daemon_jon_product_service import status_report
        out = status_report()
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            _banner(f"v{(out.get('product') or {}).get('version')} — {out['ok']}/{out['total']} tech OK")
            for row in out.get("technologies") or []:
                mark = "OK" if row.get("ok") else ("…" if row.get("installed") else "--")
                print(f"  [{mark}] {row['id']:2} {row['title']}")
        return 0

    if args.backlog:
        from backend.services.profit_daemon_jon_product_service import product_improvement_backlog
        out = product_improvement_backlog()
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            _banner(f"Finished-product backlog — {out['done']}/{out['total']} done ({out['completion_pct']}%)")
            for row in out["items"]:
                print(f"  [{row['status']:4}] {row['area']:14} {row['title']}")
        return 0

    if args.sales:
        from scripts.exchange_sales_report import build_report
        out = build_report(args.hours)
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            t = out["totals"]
            _banner(f"Sales last {args.hours:g}h")
            print(f"Fills {t['fills']} | notional ${t['notional_usd']} | realized ${t['realized_pnl_usd']}")
            for venue, data in (out.get("by_venue") or {}).items():
                print(f"  {venue}: {data['fills']} fills | ${data['notional_usd']} | pnl ${data['realized_pnl_usd']}")
        return 0

    # Default: run the unified profit daemon
    profile = args.profile or os.environ.get("EXCHANGE_PROFIT_PROFILE") or "standard"
    if profile == "paper":
        os.environ.setdefault("EXCHANGE_ARBITRAGE_LIVE", "0")
        os.environ.setdefault("EXCHANGE_LIVE_PROFIT_MAX", "0")
        profile = "standard"
    os.environ["EXCHANGE_PROFIT_PROFILE"] = profile
    _banner(f"profile={profile} once={bool(args.once)}")

    forwarded = list(unknown)
    if args.once:
        forwarded.append("--once")
    forwarded.extend(["--profile", profile])
    if args.skip_preflight:
        forwarded.append("--skip-preflight")
    return _run_apd(forwarded)


def _run_apd(forwarded: list[str]) -> int:
    # all_profit_daemons.main() parses sys.argv — temporarily swap.
    old = sys.argv[:]
    try:
        sys.argv = ["all_profit_daemons.py", *forwarded]
        from scripts.all_profit_daemons import main as apd_main
        return int(apd_main() or 0)
    finally:
        sys.argv = old


if __name__ == "__main__":
    raise SystemExit(main())
