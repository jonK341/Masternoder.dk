#!/usr/bin/env python3
"""Live test: trigger maintain-ping via ops API and watch public activetime."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("MN2_TEST_BASE", "https://masternoder.dk")


def load_secret() -> str:
    for key in ("MN2_OPS_SECRET", "MN2_SCAN_SECRET"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val
    env_path = ROOT / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            for key in ("MN2_OPS_SECRET=", "MN2_SCAN_SECRET="):
                if line.startswith(key):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def get(path: str) -> dict:
    with urllib.request.urlopen(BASE + path, timeout=45) as resp:
        return json.loads(resp.read())


def post(path: str, secret: str) -> dict:
    req = urllib.request.Request(
        BASE + path,
        method="POST",
        headers={
            "X-Ops-Secret": secret,
            "Content-Type": "application/json",
        },
        data=b"{}",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def snapshot() -> dict:
    net = get("/api/mn2/masternodes?limit=50&fresh=1")
    rows = net.get("list") or []
    enabled = [x for x in rows if str(x.get("status", "")).upper() == "ENABLED"]
    active_zero = sum(
        1
        for x in rows
        if str(x.get("status", "")).upper() == "ACTIVE" and int(x.get("activetime") or 0) == 0
    )
    # Watch highest activetime ENABLED node (primary ping target accumulates most).
    top = max(enabled, key=lambda x: int(x.get("activetime") or 0)) if enabled else (rows[0] if rows else {})
    return {
        "total": net.get("total"),
        "enabled": net.get("enabled"),
        "active_zero": active_zero,
        "top_status": top.get("status"),
        "top_act": int(top.get("activetime") or 0),
        "top_addr": str(top.get("addr") or "")[:42],
    }


def main() -> int:
    secret = load_secret()
    if not secret:
        print("No MN2_OPS_SECRET / MN2_SCAN_SECRET in env or .env", file=sys.stderr)
        return 1

    print(f"== BEFORE ({BASE}) ==")
    before = snapshot()
    print(json.dumps(before, indent=2))

    maintain_ping_stub = False
    print("\n== POST /api/mn2/masternode/maintain-ping ==")
    try:
        mp = post("/api/mn2/masternode/maintain-ping", secret)
        print(json.dumps(mp, indent=2))
        if mp.get("auto_fixed") or mp.get("message") == "Endpoint auto-created":
            maintain_ping_stub = True
            print(
                "WARN: maintain-ping is an auto-created stub on this host — "
                "deploy mn2_staking + apply_updates, then use provision-pending "
                "(cron) until the real route is live."
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(f"HTTP {exc.code}: {body[:500]}")
        if exc.code == 404:
            print("Endpoint not deployed yet — deploy mn2_staking + apply_updates first.")
    except Exception as exc:
        print(f"maintain-ping failed: {exc}")

    print("\n== POST /api/mn2/masternode/provision-pending?limit=1 ==")
    try:
        pp = post("/api/mn2/masternode/provision-pending?limit=1", secret)
        for key in ("ping_loop", "ping", "maintain_ping", "maintain_ping_loop"):
            if key in pp:
                print(f"{key}:", json.dumps(pp[key], indent=2))
        if not any(k in pp for k in ("ping_loop", "ping", "maintain_ping", "maintain_ping_loop")):
            print(json.dumps(pp, indent=2)[:3000])
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}: {exc.read().decode(errors='replace')[:500]}")
    except Exception as exc:
        print(f"provision-pending failed: {exc}")

    interval = int(os.environ.get("MN2_TEST_INTERVAL", "35"))
    samples = int(os.environ.get("MN2_TEST_SAMPLES", "3"))
    print(f"\n== WATCH activetime ({samples} samples, {interval}s apart) ==")
    prev = before["top_act"]
    increasing = False
    for i in range(samples):
        s = snapshot()
        delta = s["top_act"] - prev if i else 0
        if delta > 0:
            increasing = True
        print(
            f"sample {i + 1}: status={s['top_status']} activetime={s['top_act']} "
            f"delta={delta} addr={s['top_addr']}"
        )
        prev = s["top_act"]
        if i < samples - 1:
            time.sleep(interval)

    print("\n== RESULT ==")
    if increasing:
        print("PASS: ENABLED activetime is increasing (ping loop alive).")
        return 0
    if before["top_act"] > 0 and prev == before["top_act"]:
        print("FAIL: activetime frozen — ping loop stalled.")
        if maintain_ping_stub:
            print("  -> Deploy watchdog code first (mn2_staking + apply_updates).")
        print(
            "  -> Manual fix: SSH + startmasternode alias false platformmn2; local false."
        )
        print(
            "  -> Cron watchdog waits ping_stall_minutes (default 8) before auto-restart; "
            "re-run this script with MN2_TEST_SAMPLES=15 MN2_TEST_INTERVAL=35 for ~8 min watch."
        )
        return 2
    print("INCONCLUSIVE: no ENABLED node with rising activetime yet.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
