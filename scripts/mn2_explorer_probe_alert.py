#!/usr/bin/env python3
"""Probe explorer health and alert Discord on failure (P4 #175).

Cron-friendly. Reads DISCORD_WEBHOOK_URL from env or /var/www/html/.env.
State file avoids alert spam: data/mn2_explorer_probe_state.json

Usage:
  python scripts/mn2_explorer_probe_alert.py
  python scripts/mn2_explorer_probe_alert.py --base-url http://127.0.0.1:5000
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "data" / "mn2_explorer_probe_state.json"


def _load_env_file() -> None:
    env_path = os.environ.get("MN2_ENV_FILE", "/var/www/html/.env")
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                if key and key not in os.environ:
                    os.environ[key] = val.strip().strip('"').strip("'")
    except OSError:
        pass


def _fetch_status(base: str) -> dict:
    url = f"{base.rstrip('/')}/api/mn2/explorer/status"
    with urllib.request.urlopen(url, timeout=12) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_discord(message: str) -> bool:
    webhook = (os.environ.get("DISCORD_WEBHOOK_URL") or "").strip()
    if not webhook:
        return False
    payload = json.dumps({"content": message[:1900]}).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10):
            return True
    except urllib.error.HTTPError:
        return False


def _read_state() -> dict:
    if not STATE_PATH.is_file():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")


def main() -> int:
    _load_env_file()
    p = argparse.ArgumentParser(description="Explorer probe + Discord alert")
    p.add_argument("--base-url", default=os.environ.get("POST_DEPLOY_BASE_URL", "http://127.0.0.1:5000"))
    p.add_argument("--force-alert", action="store_true", help="Send alert even if state unchanged")
    args = p.parse_args()

    try:
        data = _fetch_status(args.base_url)
    except Exception as exc:
        data = {"status": "unreachable", "error": str(exc)}

    status = str(data.get("status") or "unknown")
    unhealthy = status not in ("healthy", "degraded")
    rpc_ok = ((data.get("checks") or {}).get("rpc") or {}).get("ok")
    if status == "degraded" and rpc_ok is False:
        unhealthy = True

    prev = _read_state()
    prev_status = prev.get("last_status")
    now = int(time.time())
    state = {"last_status": status, "last_check_ts": now, "payload": data}
    _write_state(state)

    if not unhealthy:
        if prev_status not in (None, "healthy", "degraded"):
            _post_discord(f"✅ MN2 explorer probe recovered: **{status}**")
        return 0

    if not args.force_alert and prev_status == status and (now - int(prev.get("last_alert_ts") or 0)) < 3600:
        print(f"Unhealthy ({status}) but alert suppressed (cooldown)")
        return 1

    msg = (
        f"⚠️ MN2 explorer probe **{status}**\n"
        f"kind={data.get('explorer_kind')} rpc_ok={rpc_ok}\n"
        f"rich_list={((data.get('checks') or {}).get('rich_list') or {})}"
    )
    if _post_discord(msg):
        state["last_alert_ts"] = now
        _write_state(state)
        print("Alert sent")
    else:
        print("Unhealthy but Discord webhook not configured", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
