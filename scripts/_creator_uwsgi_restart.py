#!/usr/bin/env python3
"""Hard restart uwsgi + verify creator API on server."""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""
set -e
cd /var/www/html
echo '== pycache purge =='
find backend/routes -name '*.pyc' -delete 2>/dev/null || true
find backend/routes -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
echo '== stop uwsgi =='
systemctl stop uwsgi-vidgenerator uwsgi-vidgenerator-5001 2>&1 || true
sleep 3
echo '== start uwsgi =='
systemctl start uwsgi-vidgenerator uwsgi-vidgenerator-5001 2>&1 || true
sleep 8
for port in 5000 5001; do
  echo "== curl :$port =="
  curl -sS -m 15 "http://127.0.0.1:${port}/api/creator/config" | head -c 400
  echo
done
"""

ssh, _, _ = connect_deploy_ssh()
stdin, stdout, stderr = ssh.exec_command(REMOTE, timeout=120)
print((stdout.read() + stderr.read()).decode(errors="replace"))
ssh.close()
