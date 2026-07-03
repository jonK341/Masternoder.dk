#!/usr/bin/env python3
"""Light payout sweep status — no secrets, no full Flask app.

Usage:
  python scripts/payout_sweep_status.py
  python scripts/payout_sweep_status.py --json
  python scripts/payout_sweep_status.py --plan   # include sweep plan (actionable check)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")


def _collect(*, include_plan: bool = False) -> dict:
    from scripts.daemon_env import load_dotenv

    load_dotenv()
    from backend.services.exchange_payout_service import payout_status, plan_sweep

    st = payout_status()
    out = {
        "success": st.get("success", True),
        "destination": st.get("destination"),
        "mode": st.get("mode"),
        "ready_to_sweep": bool(st.get("ready_to_sweep")),
        "auto_sweep": bool(st.get("auto_sweep")),
        "min_sweep_usd": float(st.get("min_sweep_usd") or 0),
        "net_unswept_usd": float(st.get("net_unswept_usd") or 0),
        "paypal_sweepable_usd": float(st.get("paypal_sweepable_usd") or 0),
        "realized_total_usd": float(st.get("realized_total_usd") or 0),
        "swept_total_usd": float(st.get("swept_total_usd") or 0),
        "treasury_stashed_usd": float(st.get("treasury_stashed_usd") or 0),
        "paypal_connected": bool((st.get("paypal") or {}).get("connected")),
        "paypal_live_enabled": bool((st.get("paypal") or {}).get("live_enabled")),
        "last_sweep_mode": None,
    }
    try:
        cfg_path = os.path.join(ROOT, "data", "crypto_exchange", "payout_config.json")
        if os.path.isfile(cfg_path):
            with open(cfg_path, encoding="utf-8") as fh:
                cfg = json.load(fh)
            last = cfg.get("last_sweep") or {}
            out["last_sweep_mode"] = last.get("mode")
            out["last_sweep_amount_usd"] = last.get("amount_usd")
    except Exception:
        pass

    gap = out["min_sweep_usd"] - out["paypal_sweepable_usd"]
    out["usd_to_threshold"] = round(max(0.0, gap), 4)

    out["auto_sweep_hint"] = (
        "Enable: run_all_profit_daemons.cmd --auto-sweep + EXCHANGE_AUTO_PAYPAL_SWEEP=1 "
        f"(min ${out['min_sweep_usd']:.0f} via EXCHANGE_AUTO_SWEEP_MIN_USD or payout_config)"
    )

    if include_plan:
        out["plan"] = plan_sweep()

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Payout sweep readiness (light)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--plan", action="store_true", help="Include plan_sweep actionable check")
    args = parser.parse_args()

    out = _collect(include_plan=args.plan)

    if args.json:
        print(json.dumps(out, indent=2))
        return 0

    print("Payout sweep status")
    print(f"  destination:     {out['destination']}")
    print(f"  mode:              {out['mode']} (last_sweep={out.get('last_sweep_mode')})")
    print(f"  ready_to_sweep:    {out['ready_to_sweep']}")
    print(f"  auto_sweep:        {out['auto_sweep']}")
    print(f"  min_sweep_usd:     ${out['min_sweep_usd']:.2f}")
    print(f"  net_unswept_usd:   ${out['net_unswept_usd']:.2f}")
    print(f"  paypal_sweepable:  ${out['paypal_sweepable_usd']:.2f}")
    if out["usd_to_threshold"] > 0:
        print(f"  usd_to_threshold:  ${out['usd_to_threshold']:.2f} below min")
    print(f"  hint: {out['auto_sweep_hint']}")
    if args.plan and out.get("plan"):
        plan = out["plan"]
        print(f"  plan_actionable:   {plan.get('actionable')} reason={plan.get('reason', 'ok')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
