#!/usr/bin/env python3
"""Verify EXCHANGE_PAYOUT_PAYPAL_LIVE on production server .env."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE_ROOT = "/var/www/html"


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"connected ({auth})")
    try:
        checks = [
            (
                "env_file",
                f"grep -E '^EXCHANGE_PAYOUT_PAYPAL_LIVE=' {REMOTE_ROOT}/.env "
                f"|| echo 'EXCHANGE_PAYOUT_PAYPAL_LIVE=NOT_SET'",
            ),
            (
                "shell_runtime",
                f"cd {REMOTE_ROOT} && set -a && [ -f .env ] && . ./.env && set +a && "
                "python3 -c \"import os; print(os.environ.get('EXCHANGE_PAYOUT_PAYPAL_LIVE','unset'))\"",
            ),
            (
                "payout_service",
                f"cd {REMOTE_ROOT} && set -a && [ -f .env ] && . ./.env && set +a && "
                "LITE_APP=1 DAEMON_QUIET=1 python3 -c "
                "\"from backend.services.exchange_payout_service import payout_status; "
                "import json; s=payout_status(); "
                "print(json.dumps({'mode': s.get('mode'), 'paypal_live_enabled': "
                "(s.get('paypal') or {}).get('live_enabled'), "
                "'auto_sweep': s.get('auto_sweep'), 'min_sweep_usd': s.get('min_sweep_usd'), "
                "'paypal_sweepable_usd': s.get('paypal_sweepable_usd'), "
                "'ready_to_sweep': s.get('ready_to_sweep')}))\"",
            ),
        ]
        results: dict = {}
        for name, cmd in checks:
            _, stdout, stderr = ssh.exec_command(cmd, timeout=90)
            out = stdout.read().decode(errors="replace").strip()
            err = stderr.read().decode(errors="replace").strip()
            results[name] = {"stdout": out, "stderr": err[-500:] if err else ""}
            print(f"\n[{name}]")
            print(out or "(empty)")
            if err:
                print(f"stderr: {err[-300:]}")

        env_line = results.get("env_file", {}).get("stdout", "")
        runtime = results.get("shell_runtime", {}).get("stdout", "").strip()
        ok_env = "EXCHANGE_PAYOUT_PAYPAL_LIVE=1" in env_line
        ok_runtime = runtime in ("1", "true", "yes", "on")

        paypal_live = False
        mode = ""
        try:
            st = json.loads(results.get("payout_service", {}).get("stdout", "") or "{}")
            paypal_live = bool(st.get("paypal_live_enabled"))
            mode = str(st.get("mode") or "")
            print(f"\n[parsed] mode={mode} paypal_live_enabled={paypal_live}")
            print(f"  auto_sweep={st.get('auto_sweep')} min_sweep_usd={st.get('min_sweep_usd')}")
            print(f"  paypal_sweepable_usd={st.get('paypal_sweepable_usd')}")
        except json.JSONDecodeError:
            print("\n[parsed] payout_status JSON parse failed")

        confirmed = ok_env and ok_runtime and paypal_live
        print(f"\nCONFIRMED={confirmed} (env_file={ok_env} runtime={ok_runtime} service={paypal_live})")
        return 0 if confirmed else 1
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
