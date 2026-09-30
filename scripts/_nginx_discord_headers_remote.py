"""Inspect nginx header forwarding for Discord signatures (remote)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass


def main() -> None:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print("ssh auth:", auth)
    cmd = "grep -RIn 'signature\\|uwsgi\\|proxy_pass\\|underscores' /etc/nginx/sites-enabled/ /etc/nginx/nginx.conf 2>/dev/null | head -50"
    _, stdout, stderr = ssh.exec_command(cmd, timeout=20)
    print(stdout.read().decode())
    err = stderr.read().decode().strip()
    if err:
        print("stderr:", err[:200])
    ssh.close()


if __name__ == "__main__":
    main()
