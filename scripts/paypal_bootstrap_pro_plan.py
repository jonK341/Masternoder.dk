#!/usr/bin/env python3
"""Create PayPal Pro billing plan via REST API and print plan id (P-…)."""
from __future__ import annotations

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _load_dotenv() -> None:
    env_path = os.path.join(_ROOT, ".env")
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except OSError:
        return


def main() -> int:
    _load_dotenv()
    from backend.services.monetization_config_service import (
        SUBSCRIPTION_PLAN_PLACEHOLDER_PRO,
        get_subscription_plan,
        live_pro_subscription_plan_id,
    )
    from backend.services.paypal_service import ensure_pro_subscription_plan

    existing = live_pro_subscription_plan_id()
    if existing:
        print(json.dumps({"success": True, "plan_id": existing, "source": "env"}))
        return 0

    template = get_subscription_plan(SUBSCRIPTION_PLAN_PLACEHOLDER_PRO) or {}
    price = float(template.get("price_usd_monthly") or 19.99)
    label = str(template.get("label") or "Pro monthly")

    result = ensure_pro_subscription_plan(name=label, price_usd=price)
    print(json.dumps(result, indent=2))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
