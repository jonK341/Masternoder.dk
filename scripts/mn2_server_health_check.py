#!/usr/bin/env python3
"""Quick server health check after /tmp cleanup — critical paths only."""
from __future__ import annotations

import sys

ROOT = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
sys.path.insert(0, ROOT)


def main() -> int:
    from deploy_ssh_env import connect_deploy_ssh

    checks = r"""
set +e
echo "== disk =="
df -h / /tmp /var/www/html | head -5
echo
echo "== critical files =="
for f in \
  /var/www/html/.env \
  /var/www/html/config/masternoder2.conf \
  /var/www/html/config/wallet.dat \
  /opt/masternoder2d/masternoder2d \
  /opt/masternoder2d/masternoder2-cli \
  /var/www/html/.venv/bin/python \
  /var/www/html/backend/services/exchange_arbitrage_service.py
do
  if [ -f "$f" ]; then echo "OK  $f ($(stat -c%s "$f" 2>/dev/null || echo ?) bytes)"
  elif [ -d "$f" ]; then echo "OK  $f/ (dir)"
  else echo "MISSING  $f"; fi
done
echo
echo "== daemon =="
systemctl is-active masternoder2d 2>/dev/null || echo inactive
/opt/masternoder2d/masternoder2-cli -datadir=/var/www/html/config getblockcount 2>/dev/null || echo rpc-fail
echo
echo "== /tmp (should not hold production data) =="
ls -la /tmp/mn2-build /tmp/masternoder2d.tar.gz 2>/dev/null || echo "(cleaned build artifacts — expected)"
echo
echo "== uwsgi =="
systemctl is-active uwsgi-vidgenerator 2>/dev/null || systemctl is-active uwsgi 2>/dev/null || echo uwsgi-unknown
"""
    ssh = connect_deploy_ssh()[0]
    try:
        _, stdout, stderr = ssh.exec_command(checks, timeout=90)
        print(stdout.read().decode("utf-8", errors="replace").rstrip())
        err = stderr.read().decode("utf-8", errors="replace").strip()
        if err:
            print(err, file=sys.stderr)
        return stdout.channel.recv_exit_status()
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
