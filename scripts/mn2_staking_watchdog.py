#!/usr/bin/env python3
"""Cron-safe: unlock MN2 wallet when staking is off after daemon restart."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)


def _load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    path = os.path.join(ROOT, ".env")
    if not os.path.isfile(path):
        return out
    for raw in open(path, encoding="utf-8", errors="replace"):
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _staking_on(result: dict) -> bool:
    if not isinstance(result, dict):
        return False
    return bool(result.get("staking status") or result.get("staking_status"))


def main() -> int:
    from backend.services import mn2_rpc_client as rpc

    payload = rpc.getstakingstatus() or {}
    result = payload.get("result") if isinstance(payload, dict) else {}
    if not isinstance(result, dict):
        print("watchdog: getstakingstatus unavailable")
        return 0

    unlocked = bool(result.get("walletunlocked"))
    staking = _staking_on(result)
    if staking and unlocked:
        print("watchdog: staking OK (unlocked + active)")
        return 0

    env = _load_env()
    pw = env.get("MN2_WALLET_PASSPHRASE", "")
    if not pw:
        print("watchdog: wallet locked or staking off — MN2_WALLET_PASSPHRASE missing in .env")
        return 0

    try:
        rpc.walletpassphrase(pw, 0, True)
        print("watchdog: walletpassphrase OK")
    except Exception as exc:
        print(f"watchdog: walletpassphrase failed: {exc}")
        return 1

    after = rpc.getstakingstatus() or {}
    after_result = after.get("result") if isinstance(after, dict) else {}
    if _staking_on(after_result):
        log_dir = os.path.join(ROOT, "logs")
        os.makedirs(log_dir, exist_ok=True)
        rec = {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "type": "staking_watchdog_resumed",
            "message": "MN2 staking resumed by cron watchdog.",
        }
        with open(os.path.join(log_dir, "mn2_network_alerts.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        print("watchdog: staking active after unlock")
        return 0

    print("watchdog: unlocked but staking still off — check daemon / collateral")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
