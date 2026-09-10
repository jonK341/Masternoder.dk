#!/usr/bin/env python3
"""Ensure single masternoder2d instance during reindex."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
echo '== processes before =='
pgrep -a masternoder2d || echo none
REINDEX=$(pgrep -f 'masternoder2d.*-reindex' | head -1)
if [ -n "$REINDEX" ]; then
  echo "reindex pid=$REINDEX — stopping systemd unit to avoid duplicate"
  systemctl stop masternoder2d 2>/dev/null || true
  sleep 2
fi
echo '== processes after =='
pgrep -a masternoder2d || echo none
echo '== reindex tail =='
tail -5 /var/log/mn2-reindex.log 2>/dev/null
RPC_USER=$(grep '^MN2_RPC_USER=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
RPC_PASS=$(grep '^MN2_RPC_PASSWORD=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
curl -sS -m 8 -u "$RPC_USER:$RPC_PASS" -H 'content-type: application/json' \
  -d '{"jsonrpc":"1.0","id":"t","method":"getblockcount","params":[]}' http://127.0.0.1:9332/ 2>&1
echo
free -h | head -2
ENDSCRIPT"""

ssh, auth, _ = connect_deploy_ssh()
print(f"Connected ({auth})\n")
_, o, _ = ssh.exec_command(REMOTE, timeout=60)
print(o.read().decode())
ssh.close()
