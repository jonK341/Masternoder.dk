"""Print nginx upstream + location blocks for masternoder.dk (remote)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass


def main() -> None:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print("ssh auth:", auth)
    _, stdout, _ = ssh.exec_command("sed -n '1,120p' /etc/nginx/sites-enabled/masternoder.dk", timeout=20)
    print(stdout.read().decode())
    ssh.close()


if __name__ == "__main__":
    main()
