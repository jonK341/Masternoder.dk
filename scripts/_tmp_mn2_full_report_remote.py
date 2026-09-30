#!/usr/bin/env python3
"""One-shot remote MN2 system snapshot for full status report."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
echo '== daemon info =='
CLI=/opt/masternoder2d/masternoder2-cli
DD=/var/www/html/config
$CLI -datadir=$DD getblockcount 2>/dev/null
echo '--- getinfo ---'
$CLI -datadir=$DD getinfo 2>/dev/null | head -c 1500
echo
echo '--- mnsync ---'
$CLI -datadir=$DD mnsync status 2>/dev/null | head -c 900
echo
echo '--- staking ---'
$CLI -datadir=$DD getstakingstatus 2>/dev/null | head -c 900
echo
echo '--- masternode count ---'
$CLI -datadir=$DD masternode count 2>/dev/null
echo
echo '--- walletinfo ---'
$CLI -datadir=$DD getwalletinfo 2>/dev/null | head -c 1200
echo
echo '== localhost APIs =='
for p in /api/health /api/mn2/health /api/mn2/price '/api/mn2/masternode/service?fresh=1' /api/mn2/services /api/mn2/network-overview /api/mn2/staking/monitor /api/mn2/staking/proof-of-reserves /api/mn2/staking/yield-report; do
  code=$(curl -sS -m 25 -o /tmp/mn2api.json -w '%{http_code}' "http://127.0.0.1:5000$p" || echo 000)
  echo "--- $p HTTP $code ---"
  head -c 1200 /tmp/mn2api.json 2>/dev/null
  echo
done
echo '== ops stats =='
TOK=$(grep -E '^MN2_SCAN_SECRET=' /var/www/html/.env 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'")
code=$(curl -sS -m 30 -o /tmp/mn2ops.json -w '%{http_code}' -H "X-Scanner-Token: $TOK" http://127.0.0.1:5000/api/mn2/ops/stats || echo 000)
echo "HTTP $code"
head -c 2500 /tmp/mn2ops.json
echo
echo '== crons =='
ls /etc/cron.d/*mn2* /etc/cron.d/masternoder* 2>/dev/null
echo '== fleet autostart =='
systemctl status mn2-fleet-autostart --no-pager -l 2>&1 | head -25
echo '== daemon version =='
$CLI -datadir=$DD getinfo 2>/dev/null | grep -E '"version"|"protocolversion"|"blocks"|"connections"' | head -20
ENDSCRIPT
"""


def main() -> int:
    ssh = connect_deploy_ssh()[0]
    try:
        _, stdout, stderr = ssh.exec_command(REMOTE, timeout=180)
        out = (stdout.read() or b"").decode("utf-8", errors="replace")
        err = (stderr.read() or b"").decode("utf-8", errors="replace")
        print(out)
        if err.strip():
            print("STDERR:", err[:2000], file=sys.stderr)
        return stdout.channel.recv_exit_status()
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
