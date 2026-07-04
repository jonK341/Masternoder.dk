#!/usr/bin/env python3
"""Apply EXCHANGE_PAYOUT_PAYPAL_* from .env and show payout readiness."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass


def main() -> int:
    email = (os.environ.get("EXCHANGE_PAYOUT_PAYPAL_EMAIL") or "").strip()
    if not email:
        print("Set EXCHANGE_PAYOUT_PAYPAL_EMAIL in .env (your PayPal login email).")
        return 1
    share = os.environ.get("EXCHANGE_PAYOUT_PAYPAL_SHARE_PCT", "50")
    from backend.services.exchange_payout_service import configure_paypal, payout_status

    cfg = configure_paypal(email, share_pct=float(share))
    if not cfg.get("success"):
        print("Configure failed:", cfg.get("error"))
        return 1
    st = payout_status()
    print("PayPal payout configured:", email)
    print("  Share:", st["paypal"]["share_pct"], "%")
    print("  Sweepable:", st.get("paypal_sweepable_usd"), "USD")
    print("  Ready:", st.get("ready_to_sweep"))
    print("  Mode:", st.get("mode"))
    live = os.environ.get("EXCHANGE_PAYOUT_PAYPAL_LIVE", "0")
    if live not in ("1", "true", "yes"):
        print("  (Paper until EXCHANGE_PAYOUT_PAYPAL_LIVE=1 and PayPal Payouts enabled on your app)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
