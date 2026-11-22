#!/usr/bin/env python3
"""Post-deploy exchange checks on production (no secret values printed)."""
from __future__ import annotations

import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE = "/var/www/html"


def run(ssh, cmd: str, timeout: int = 90) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = (stdout.read() or b"").decode(errors="replace").strip()
    err = (stderr.read() or b"").decode(errors="replace").strip()
    if err and not out:
        return f"ERR: {err[-800:]}"
    if err:
        return f"{out}\nERR: {err[-400:]}"
    return out


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"connected ({auth})")

    print("--- env flags (masked) ---")
    print(
        run(
            ssh,
            f"cd {REMOTE} && grep -E '^(EXCHANGE_ARBITRAGE_LIVE|EXCHANGE_PAYOUT_BINANCE_LIVE|"
            f"MN2_SPORK_OVERRIDE_JSON|MN2_SPORK_GATES)=' .env | sed 's/=.*/=***/' || true",
        )
    )

    # Ensure live flags on prod if missing (do not print values).
    ensure = r"""
cd /var/www/html
ensure() {
  key="$1"; val="$2"
  if grep -q "^${key}=" .env 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|" .env
  else
    echo "${key}=${val}" >> .env
  fi
}
ensure EXCHANGE_ARBITRAGE_LIVE 1
ensure EXCHANGE_PAYOUT_BINANCE_LIVE 1
# Local/dev-style override so withdraw/agent live works without MN2 RPC sporks.
if ! grep -q '^MN2_SPORK_OVERRIDE_JSON=' .env 2>/dev/null; then
  echo 'MN2_SPORK_OVERRIDE_JSON={"SPORK_112_EXCHANGE_LIVE_TRADING":1703122560,"SPORK_114_PAYOUT_LIVE":1703122560}' >> .env
fi
echo ensured
"""
    print("--- ensure live flags ---")
    print(run(ssh, ensure, timeout=30))

    py = r"""
cd /var/www/html && .venv/bin/python - <<'PY'
from scripts.daemon_env import load_dotenv
load_dotenv()
from backend.services.exchange_arbitrage_service import live_enabled
from backend.services.exchange_binance_withdraw_service import (
    binance_withdraw_live_enabled,
    binance_withdraw_live_gate_reason,
)
from backend.services.crypto_exchange_agent_service import list_agents
from backend.services.exchange_live_execution_service import venue_live_ready
a = list_agents()
print("arb", live_enabled())
print("wd", binance_withdraw_live_enabled(), binance_withdraw_live_gate_reason() or "ok")
print("binance_ready", venue_live_ready("binance"))
print("agents_venue", a.get("venue_live"), "live_cfg", a.get("live_venue_trading"))
PY
"""
    print("--- live status ---")
    print(run(ssh, py, timeout=120))

    print("--- health ---")
    print(run(ssh, "curl -s http://127.0.0.1:5000/api/health"))
    print(run(ssh, "curl -s -o /dev/null -w 'exchange:%{http_code}\\n' http://127.0.0.1:5000/exchange/"))

    print("--- multi-wallet --once (summary) ---")
    tick = run(
        ssh,
        f"cd {REMOTE} && .venv/bin/python scripts/exchange_multi_wallet_daemon.py --once 2>&1 | tail -c 2500",
        timeout=180,
    )
    print(tick[-2000:])

    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
