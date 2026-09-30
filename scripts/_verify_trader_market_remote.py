#!/usr/bin/env python3
"""Remote verify: trader market tick, order book, recent trades."""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
try:
    import dotenv

    dotenv.load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass

import paramiko
from deploy_ssh_env import deploy_host, deploy_user, require_deploy_pass

WEB = "/var/www/html"


def sh(ssh, cmd: str, timeout: int = 120) -> tuple[int, str]:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    code = stdout.channel.recv_exit_status()
    text = (stdout.read() + stderr.read()).decode(errors="replace").strip()
    return code, text


def _json_ok(body: str) -> bool:
    try:
        return bool(json.loads(body).get("success"))
    except json.JSONDecodeError:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify trader market on production")
    parser.add_argument("--ask-pass", action="store_true", help="Prompt for SSH password")
    args = parser.parse_args()

    pw = require_deploy_pass(force_prompt=args.ask_pass)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(deploy_host(), username=deploy_user(), password=pw, timeout=30)

    secret_cmd = (
        f"SECRET=$(grep -E '^(MN2_OPS_SECRET|MN2_SCAN_SECRET)=' {WEB}/.env | head -1 | cut -d= -f2- | tr -d '\\r\"')"
    )
    checks: list[tuple[str, str, object]] = [
        ("p2p_market_service.py", f"test -f {WEB}/backend/services/p2p_market_service.py && echo OK || echo MISSING", lambda b: "OK" in b),
        ("p2p_market_routes.py", f"test -f {WEB}/backend/routes/p2p_market_routes.py && echo OK || echo MISSING", lambda b: "OK" in b),
        ("market_js", f"test -f {WEB}/static/js/mn2-internal-market.js && echo OK || echo MISSING", lambda b: "OK" in b),
        (
            "run_market",
            f"{secret_cmd}; curl -s -X POST -H \"X-Ops-Secret: $SECRET\" "
            f"http://127.0.0.1:5000/api/agents/trader-staking/run-market",
            _json_ok,
        ),
        ("ticker", "curl -s http://127.0.0.1:5000/api/market/ticker", _json_ok),
        ("sell_orders", "curl -s 'http://127.0.0.1:5000/api/market/orders?side=sell&limit=8'", _json_ok),
        ("recent_trades", "curl -s 'http://127.0.0.1:5000/api/market/trades?limit=5'", _json_ok),
    ]

    passed = 0
    for label, cmd, ok_fn in checks:
        print(f"\n=== {label} ===")
        code, out = sh(ssh, cmd)
        print(out[:1200])
        ok = code == 0 and ok_fn(out)
        if label == "run_market":
            try:
                data = json.loads(out)
                print(f"  -> trades={data.get('trades')} success={data.get('success')}")
            except Exception:
                pass
        print(f"{'PASS' if ok else 'FAIL'}")
        if ok:
            passed += 1

    ssh.close()
    total = len(checks)
    print(f"\nTrader market: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
