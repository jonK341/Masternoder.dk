#!/usr/bin/env python3
"""Preflight + env checklist for real PayPal auto-sweep (does not write .env).

Usage:
  python scripts/enable_live_paypal_sweep.py
  python scripts/enable_live_paypal_sweep.py --dry-run
  python scripts/enable_live_paypal_sweep.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DAEMON_QUIET", "1")
os.environ.setdefault("LITE_APP", "1")


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _mask_email(email: str) -> str:
    email = (email or "").strip()
    if "@" not in email:
        return "(not set)"
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        return f"{local[0]}*@{domain}"
    return f"{local[:2]}***@{domain}"


def _collect_preflight() -> dict:
    from scripts.daemon_env import load_dotenv

    load_dotenv()

    cid = bool((os.environ.get("PAYPAL_CLIENT_ID") or "").strip())
    secret = bool((os.environ.get("PAYPAL_CLIENT_SECRET") or "").strip())
    paypal_mode = (os.environ.get("PAYPAL_MODE") or "sandbox").strip().lower()
    payout_email = (os.environ.get("EXCHANGE_PAYOUT_PAYPAL_EMAIL") or "").strip()
    payout_live = _flag("EXCHANGE_PAYOUT_PAYPAL_LIVE")
    auto_sweep = _flag("EXCHANGE_AUTO_PAYPAL_SWEEP")
    share_pct = (os.environ.get("EXCHANGE_PAYOUT_PAYPAL_SHARE_PCT") or "50").strip()

    spork_ok = True
    spork_reason = ""
    try:
        from backend.services import mn2_spork_service as spork

        spork_ok, spork_reason = spork.payout_live_spork_ok()
    except Exception as exc:
        spork_reason = str(exc)

    min_sweep_usd = 5.0
    live_stash_usd = 0.0
    paper_stash_usd = 0.0
    sweepable_live_usd = 0.0
    ready_live = False
    plan_mode = "paper"
    plan_actionable = False
    plan_amount = 0.0
    plan_reason = ""

    try:
        from backend.services.exchange_payout_service import payout_status, plan_sweep
        from backend.services.exchange_treasury_service import treasury_status

        st = payout_status()
        tre = treasury_status()
        min_sweep_usd = float(st.get("min_sweep_usd") or 5)
        live_stash_usd = float(tre.get("live_stash_usd") or tre.get("ledger_stashed_usd_live") or 0)
        paper_stash_usd = float(tre.get("ledger_stashed_usd_paper") or 0)

        if payout_live and cid and secret and payout_email and spork_ok:
            plan = plan_sweep()
            plan_mode = plan.get("mode") or "live"
            plan_actionable = bool(plan.get("actionable"))
            plan_amount = float(plan.get("amount_usd") or 0)
            plan_reason = str(plan.get("reason") or "")
            sweepable_live_usd = float(plan.get("paypal_sweepable_usd") or plan.get("amount_usd") or 0)
            ready_live = plan_actionable and plan_mode == "live"
        else:
            net_live = max(0.0, live_stash_usd)
            try:
                share = float(share_pct)
                share_f = share / 100.0 if share > 1 else share
            except (TypeError, ValueError):
                share_f = 0.5
            sweepable_live_usd = round(net_live * share_f, 4)
            ready_live = bool(payout_email and sweepable_live_usd >= min_sweep_usd)
    except Exception as exc:
        plan_reason = str(exc)

    both_live_gates = payout_live and auto_sweep
    checks = {
        "paypal_client_id": cid,
        "paypal_client_secret": secret,
        "paypal_mode": paypal_mode,
        "payout_email": bool(payout_email),
        "payout_email_masked": _mask_email(payout_email),
        "exchange_payout_paypal_live": payout_live,
        "exchange_auto_paypal_sweep": auto_sweep,
        "both_live_gates": both_live_gates,
        "spork_payout_live": spork_ok,
        "spork_block_reason": spork_reason or None,
        "min_sweep_usd": min_sweep_usd,
        "live_stash_usd": round(live_stash_usd, 4),
        "paper_stash_usd": round(paper_stash_usd, 4),
        "live_sweepable_usd": round(sweepable_live_usd, 4),
        "ready_for_live_sweep": ready_live,
        "plan_mode": plan_mode,
        "plan_actionable": plan_actionable,
        "plan_amount_usd": round(plan_amount, 4),
        "plan_reason": plan_reason or None,
    }
    checks["all_ready"] = all([
        cid,
        secret,
        payout_email,
        both_live_gates,
        spork_ok,
    ])
    return checks


def _env_lines(checks: dict) -> list[str]:
    email_hint = "you@example.com"
    share = (os.environ.get("EXCHANGE_PAYOUT_PAYPAL_SHARE_PCT") or "50").strip()
    min_usd = checks.get("min_sweep_usd") or 100
    lines = [
        "# --- Live PayPal auto-sweep (copy into .env, then restart daemons) ---",
        f"EXCHANGE_PAYOUT_PAYPAL_EMAIL={email_hint}",
        f"EXCHANGE_PAYOUT_PAYPAL_SHARE_PCT={share}",
        "EXCHANGE_PAYOUT_PAYPAL_LIVE=1",
        "EXCHANGE_AUTO_PAYPAL_SWEEP=1",
        f"EXCHANGE_AUTO_SWEEP_MIN_USD={int(min_usd) if float(min_usd).is_integer() else min_usd}",
        "PAYPAL_MODE=live",
        "# PAYPAL_CLIENT_ID=...",
        "# PAYPAL_CLIENT_SECRET=...",
    ]
    if not checks.get("paypal_client_id"):
        lines.append("# PAYPAL_CLIENT_ID= (required — from PayPal developer dashboard)")
    if not checks.get("paypal_client_secret"):
        lines.append("# PAYPAL_CLIENT_SECRET= (required)")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight checklist for live PayPal auto-sweep")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what the next sweep would do (plan only, no payout)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    checks = _collect_preflight()
    env_lines = _env_lines(checks)

    if args.dry_run:
        try:
            from backend.services.exchange_payout_service import plan_sweep

            checks["dry_run_plan"] = plan_sweep()
        except Exception as exc:
            checks["dry_run_plan"] = {"success": False, "error": str(exc)}

    payload = {
        "checks": checks,
        "env_lines": env_lines,
        "restart": "scripts\\run_all_profit_daemons.cmd --auto-sweep",
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0 if checks.get("all_ready") else 1

    print("=== Live PayPal auto-sweep preflight ===")
    print()
    print("Checklist (no secrets shown):")
    print(f"  PayPal CLIENT_ID present:     {'yes' if checks['paypal_client_id'] else 'NO'}")
    print(f"  PayPal CLIENT_SECRET present: {'yes' if checks['paypal_client_secret'] else 'NO'}")
    print(f"  PAYPAL_MODE:                  {checks['paypal_mode']}")
    print(f"  Payout email:                 {checks['payout_email_masked']}")
    print(f"  EXCHANGE_PAYOUT_PAYPAL_LIVE:  {'1' if checks['exchange_payout_paypal_live'] else '0'}")
    print(f"  EXCHANGE_AUTO_PAYPAL_SWEEP:   {'1' if checks['exchange_auto_paypal_sweep'] else '0'}")
    print(f"  Both gates for live sweep:    {'yes' if checks['both_live_gates'] else 'no'}")
    print(f"  SPORK_114 payout live:        {'ok' if checks['spork_payout_live'] else 'blocked'}")
    if checks.get("spork_block_reason"):
        print(f"    reason: {checks['spork_block_reason']}")
    print(f"  min_sweep_usd:                ${checks['min_sweep_usd']:.2f}")
    print(f"  live_stash_usd (ledger):      ${checks['live_stash_usd']:.4f}")
    print(f"  paper_stash_usd (ignored):    ${checks['paper_stash_usd']:.2f}")
    print(f"  live sweepable (after share): ${checks['live_sweepable_usd']:.4f}")
    print(f"  ready for live sweep now:     {'yes' if checks['ready_for_live_sweep'] else 'no'}")
    if checks.get("plan_reason") and not checks.get("plan_actionable"):
        print(f"  plan note:                    {checks['plan_reason']}")

    if args.dry_run:
        plan = checks.get("dry_run_plan") or {}
        print()
        print("Dry-run (next sweep plan, no funds moved):")
        print(f"  mode:       {plan.get('mode', '?')}")
        print(f"  actionable: {plan.get('actionable')}")
        if plan.get("actionable"):
            print(f"  amount_usd: ${float(plan.get('amount_usd') or 0):.4f}")
            print(f"  receiver:   {plan.get('receiver_email', '?')}")
        else:
            print(f"  reason:     {plan.get('reason') or plan.get('error') or 'n/a'}")

    print()
    print("Add these lines to .env (edit email + PayPal creds; script does NOT write .env):")
    for line in env_lines:
        print(f"  {line}")

    print()
    print("Restart profit daemons after saving .env:")
    print(f"  {payload['restart']}")
    print()
    print("Status anytime: python scripts/payout_sweep_status.py")

    return 0 if checks.get("all_ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
