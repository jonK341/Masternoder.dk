#!/usr/bin/env python3
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user

REMOTE = r"""bash -s <<'E'
D=-datadir=/var/www/html/config
CLI="/opt/masternoder2d/masternoder2-cli $D"
WEB=/var/www/html
echo "== blockcount history from debug =="
grep -E 'UpdateTip|new best' $WEB/config/debug.log 2>/dev/null | tail -5
echo "== staking =="
$CLI getstakinginfo 2>&1 | head -c 600
echo ""
echo "== wallet encrypted =="
$CLI walletpassphrase 2>&1 | head -1 || true
$CLI getwalletinfo 2>&1 | python3 -c 'import json,sys; d=json.load(sys.stdin); print("unlocked_until", d.get("unlocked_until"), "balance", d.get("balance"))' 2>/dev/null
echo "== MN2_WALLET_PASSPHRASE set =="
grep -q '^MN2_WALLET_PASSPHRASE=' $WEB/.env && echo yes || echo no
echo "== try unlock if passphrase in env =="
PW=$(grep '^MN2_WALLET_PASSPHRASE=' $WEB/.env 2>/dev/null | cut -d= -f2- | tr -d '\r"')
if [ -n "$PW" ]; then
  $CLI walletpassphrase "$PW" 600 2>&1
  $CLI getstakinginfo 2>&1 | head -c 400
  echo ""
fi
echo "== peer count =="
$CLI getconnectioncount 2>&1
echo "== generate? =="
$CLI help generate 2>&1 | head -3
E
"""

def main():
    os.environ.setdefault("DEPLOY_KEY_PATH", os.path.expanduser("~/.ssh/id_ed25519_deploy"))
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected {deploy_user()}@{deploy_host()} ({auth})\n")
    _, o, _ = ssh.exec_command(REMOTE, timeout=60)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(o.read().decode(errors="replace"))
    ssh.close()

if __name__ == "__main__":
    main()
