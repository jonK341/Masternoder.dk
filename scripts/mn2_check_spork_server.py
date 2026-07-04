#!/usr/bin/env python3
"""Check MN2 spork/RPC settings on production server."""
from __future__ import annotations

import sys

ROOT = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

ENV = "/var/www/html/.env"
CLI = "/opt/masternoder2d/masternoder2-cli -datadir=/var/www/html/config"


def main() -> int:
    from deploy_ssh_env import connect_deploy_ssh

    remote = f"""set -e
echo "== server .env (MN2 / exchange live) =="
grep -E '^(MN2_SPORK|MN2_RPC|EXCHANGE_ARBITRAGE)' {ENV} 2>/dev/null | sed 's/PASSWORD=.*/PASSWORD=<set>/; s/SECRET=.*/SECRET=<set>/; s/_KEY=.*/_KEY=<set>/' || echo "(no matches)"
echo
echo "== masternoder2.conf (daemon RPC only) =="
grep -E '^(server|rpcuser|rpcpassword|sporkkey)=' /var/www/html/config/masternoder2.conf | sed 's/rpcpassword=.*/rpcpassword=<set>/; s/sporkkey=.*/sporkkey=<set>/'
echo
echo "== daemon height =="
{CLI} getblockcount
echo
echo "== spork service on server =="
test -f /var/www/html/backend/services/mn2_spork_service.py && echo mn2_spork_service.py: deployed || echo mn2_spork_service.py: MISSING
echo
echo "== Python live gate (server .env) =="
cd /var/www/html && PYTHONPATH=/var/www/html /var/www/html/.venv/bin/python -c '
from scripts.daemon_env import load_dotenv
load_dotenv()
from backend.services.exchange_arbitrage_service import live_enabled
print("live_enabled=", live_enabled())
try:
    from backend.services import mn2_spork_service as s
    s.invalidate_cache()
    print("exchange_live=", s.gate_status()["exchange_live"])
except ImportError:
    print("exchange_live=", "(spork module not deployed yet — gate is EXCHANGE_ARBITRAGE_LIVE only)")
'
"""
    ssh = connect_deploy_ssh()[0]
    try:
        _, stdout, stderr = ssh.exec_command(remote, timeout=90)
        print(stdout.read().decode("utf-8", errors="replace").rstrip())
        err = stderr.read().decode("utf-8", errors="replace").strip()
        if err:
            print(err, file=sys.stderr)
        return stdout.channel.recv_exit_status()
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
