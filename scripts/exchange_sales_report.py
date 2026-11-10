#!/usr/bin/env python3
"""Summarize ladder fills / sales over the last N hours (default 3)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_ladder_service import load_config, load_state, state_path


def _tz():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Europe/Copenhagen")
    except Exception:
        return timezone(timedelta(hours=1))


def _fills_path() -> str:
    return os.path.join(ex._BASE, "logs", "cross_trade", "ladder_fills.jsonl")


def load_fills_since(cut_ts: float, path: str | None = None) -> List[Dict[str, Any]]:
    path = path or _fills_path()
    rows: List[Dict[str, Any]] = []
    if not os.path.isfile(path):
        return rows
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if float(row.get("ts") or 0) >= cut_ts:
                rows.append(row)
    return rows


def build_report(hours: float = 3.0) -> Dict[str, Any]:
    tz = _tz()
    now = time.time()
    cut = now - hours * 3600
    rows = load_fills_since(cut)
    by_venue: Dict[str, Any] = defaultdict(lambda: {
        "fills": 0, "notional_usd": 0.0, "realized_pnl_usd": 0.0,
        "entries": 0, "exits": 0,
        "by_symbol": defaultdict(lambda: {"fills": 0, "notional_usd": 0.0, "pnl_usd": 0.0}),
    })
    trades = []
    for r in sorted(rows, key=lambda x: float(x.get("ts") or 0)):
        venue = str(r.get("venue") or "nonkyc")
        symbol = str(r.get("symbol") or "?")
        usd = float(r.get("usd") or 0)
        pnl = float(r["pnl_usd"]) if "pnl_usd" in r else None
        kind = str(r.get("kind") or "")
        bv = by_venue[venue]
        bv["fills"] += 1
        bv["notional_usd"] += usd
        if pnl is not None:
            bv["realized_pnl_usd"] += pnl
        if kind == "entry":
            bv["entries"] += 1
        if kind == "exit":
            bv["exits"] += 1
        bs = bv["by_symbol"][symbol]
        bs["fills"] += 1
        bs["notional_usd"] += usd
        if pnl is not None:
            bs["pnl_usd"] += pnl
        trades.append({
            "when": datetime.fromtimestamp(float(r["ts"]), tz).strftime("%Y-%m-%d %H:%M:%S %Z"),
            "venue": venue,
            "symbol": symbol,
            "side": r.get("side"),
            "kind": kind,
            "level": r.get("level"),
            "qty": r.get("qty"),
            "price": r.get("price"),
            "usd": round(usd, 4),
            "pnl_usd": None if pnl is None else round(pnl, 6),
            "coid": r.get("coid"),
            "order_id": r.get("order_id"),
        })

    states = {}
    for venue in ("nonkyc", "binance"):
        st = load_state(state_path(None, venue))
        open_n = sum(1 for o in st["orders"].values() if not o.get("cancelled"))
        exits = sum(1 for o in st["orders"].values() if not o.get("cancelled") and o.get("kind") == "exit")
        states[venue] = {
            "realized_usd_lifetime": st.get("realized_usd"),
            "open_orders": open_n,
            "pending_exits": max(exits, len(st.get("pending") or [])),
            "symbols": load_config(venue).get("symbols"),
        }

    def _round_venue(data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "fills": data["fills"],
            "notional_usd": round(data["notional_usd"], 4),
            "realized_pnl_usd": round(data["realized_pnl_usd"], 6),
            "entries": data["entries"],
            "exits": data["exits"],
            "by_symbol": {
                s: {k: (round(v, 6) if isinstance(v, float) else v) for k, v in sd.items()}
                for s, sd in data["by_symbol"].items()
            },
        }

    return {
        "window": {
            "hours": hours,
            "from": datetime.fromtimestamp(cut, tz).isoformat(),
            "to": datetime.fromtimestamp(now, tz).isoformat(),
            "timezone": "Europe/Copenhagen",
        },
        "totals": {
            "fills": len(rows),
            "notional_usd": round(sum(float(r.get("usd") or 0) for r in rows), 4),
            "realized_pnl_usd": round(sum(float(r["pnl_usd"]) for r in rows if "pnl_usd" in r), 6),
        },
        "by_venue": {v: _round_venue(d) for v, d in by_venue.items()},
        "ladder_state_now": states,
        "trades": trades,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=float, default=3.0)
    parser.add_argument("--json", action="store_true", help="print full JSON")
    args = parser.parse_args()
    report = build_report(args.hours)
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    w = report["window"]
    t = report["totals"]
    print(f"Sales report — last {args.hours:g}h ({w['from']} → {w['to']})")
    print(f"Totals: {t['fills']} fills | notional ${t['notional_usd']} | realized ${t['realized_pnl_usd']}")
    for venue, data in report["by_venue"].items():
        print(f"  {venue}: {data['fills']} fills ({data['entries']} entry/{data['exits']} exit) "
              f"| ${data['notional_usd']} | pnl ${data['realized_pnl_usd']}")
        for sym, sd in data["by_symbol"].items():
            print(f"    {sym}: {sd['fills']} | ${sd['notional_usd']} | pnl ${sd['pnl_usd']}")
    print("Open now:")
    for venue, st in report["ladder_state_now"].items():
        print(f"  {venue}: open={st['open_orders']} pending_exits={st['pending_exits']} "
              f"lifetime_realized=${st['realized_usd_lifetime']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
