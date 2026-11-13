#!/usr/bin/env python3
"""Post-merge hosting gate: fleet bootstrap progress, rental catalog, accrue dry-run (SSH → loopback)."""
from __future__ import annotations

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE = "/var/www/html"


def _ssh_json(cmd: str) -> dict:
    client, _, _ = connect_deploy_ssh(password=require_deploy_pass())
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
        out = (stdout.read() or b"").decode(errors="replace").strip()
        err = (stderr.read() or b"").decode(errors="replace").strip()
        if err and not out:
            return {"success": False, "error": err}
        try:
            return json.loads(out) if out else {"raw": out or err}
        except json.JSONDecodeError:
            return {"success": False, "error": "non_json", "raw": out[:500], "stderr": err[:200]}
    finally:
        client.close()


def main() -> int:
    shell = (
        f"set -e; cd {REMOTE}; "
        "source cron/mn2_read_ops_secret.sh 2>/dev/null || true; "
        "SECRET=$(mn2_read_ops_secret 2>/dev/null || true); "
        "PROG=$(cat data/mn2_fleet_bootstrap_progress.json 2>/dev/null || echo '{}'); "
        "echo ---PROG---; echo \"$PROG\"; "
        "echo ---CATALOG---; "
        "curl -sS -m 45 http://127.0.0.1:5000/api/mn2/masternode/rentals/catalog; "
        "echo; echo ---ACCRUE---; "
        'if [ -n "$SECRET" ]; then '
        'curl -sS -m 45 -X POST -H "X-Ops-Token: $SECRET" '
        '"http://127.0.0.1:5000/api/mn2/masternode/accrue-renter-rewards?dry_run=1&limit=20"; '
        "else echo '{\"success\":false,\"error\":\"no_ops_secret\"}'; fi"
    )
    client, _, _ = connect_deploy_ssh(password=require_deploy_pass())
    try:
        stdin, stdout, stderr = client.exec_command(shell, timeout=120)
        raw = (stdout.read() or b"").decode(errors="replace")
    finally:
        client.close()

    blocks = {"prog": {}, "catalog": {}, "accrue": {}}
    part = None
    buf: list[str] = []
    for line in raw.splitlines():
        if line.startswith("---") and line.endswith("---"):
            if part == "PROG" and buf:
                try:
                    blocks["prog"] = json.loads("\n".join(buf))
                except json.JSONDecodeError:
                    blocks["prog"] = {"parse_error": True, "raw": "\n".join(buf)[:300]}
            elif part == "CATALOG" and buf:
                try:
                    blocks["catalog"] = json.loads("\n".join(buf))
                except json.JSONDecodeError:
                    blocks["catalog"] = {"parse_error": True}
            elif part == "ACCRUE" and buf:
                try:
                    blocks["accrue"] = json.loads("\n".join(buf))
                except json.JSONDecodeError:
                    blocks["accrue"] = {"parse_error": True}
            part = line.strip("-")
            buf = []
            continue
        if part:
            buf.append(line)
    if part == "ACCRUE" and buf:
        try:
            blocks["accrue"] = json.loads("\n".join(buf))
        except json.JSONDecodeError:
            blocks["accrue"] = {"parse_error": True}

    inv = int(blocks.get("catalog", {}).get("inventory_available") or 0)
    plan_ok = blocks.get("catalog", {}).get("subscription", {}).get("subscribable") is True
    report = {
        "success": True,
        "fleet_progress": blocks.get("prog"),
        "inventory_available": inv,
        "catalog_success": bool(blocks.get("catalog", {}).get("success")),
        "accrue_dry_run": blocks.get("accrue"),
        "paypal_subscribe_live_hint": plan_ok,
        "gates": {
            "catalog_ok": bool(blocks.get("catalog", {}).get("success")),
            "accrue_ok": bool(blocks.get("accrue", {}).get("success")),
            "inventory_ready": inv > 0,
            "paypal_subscribe_live": plan_ok,
        },
    }
    print(json.dumps(report, indent=2))
    ready_public = report["gates"]["catalog_ok"] and report["gates"]["accrue_ok"]
    return 0 if ready_public else 1


if __name__ == "__main__":
    sys.exit(main())
