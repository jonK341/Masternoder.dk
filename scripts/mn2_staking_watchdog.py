#!/usr/bin/env python3
"""Cron-safe: unlock MN2 wallet when staking is off after daemon restart."""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


def _rpc_call(env: dict[str, str], method: str, params: list | None = None) -> dict:
    url = env.get("MN2_RPC_URL") or "http://127.0.0.1:9332"
    user = env.get("MN2_RPC_USER", "")
    password = env.get("MN2_RPC_PASSWORD", "")
    body = json.dumps({"jsonrpc": "1.0", "id": "watchdog", "method": method, "params": params or []}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    if user:
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        req.add_header("Authorization", f"Basic {token}")
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode())


def main() -> int:
    env = _load_env()
    try:
        payload = _rpc_call(env, "getstakingstatus")
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        print(f"watchdog: getstakingstatus unavailable ({exc})")
        return 0

    result = payload.get("result") if isinstance(payload, dict) else {}
    if not isinstance(result, dict):
        print("watchdog: getstakingstatus empty result")
        return 0

    unlocked = bool(result.get("walletunlocked"))
    staking = _staking_on(result)
    if staking and unlocked:
        print("watchdog: staking OK (unlocked + active)")
        return 0

    pw = env.get("MN2_WALLET_PASSPHRASE", "")
    if not pw:
        print("watchdog: wallet locked or staking off — MN2_WALLET_PASSPHRASE missing in .env")
        return 0

    try:
        _rpc_call(env, "walletpassphrase", [pw, 0, True])
        print("watchdog: walletpassphrase OK")
    except Exception as exc:
        print(f"watchdog: walletpassphrase failed: {exc}")
        return 1

    try:
        after = _rpc_call(env, "getstakingstatus")
        after_result = after.get("result") if isinstance(after, dict) else {}
    except Exception:
        after_result = {}

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
