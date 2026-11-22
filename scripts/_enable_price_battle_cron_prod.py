#!/usr/bin/env python3
"""Install price-battle cron on production and verify open positions."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass


def sh(ssh, cmd: str, timeout: int = 60) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    stdout.channel.settimeout(timeout)
    stderr.channel.settimeout(timeout)
    try:
        out = (stdout.read() or b"").decode(errors="replace")
    except Exception as exc:
        out = f"[stdout_timeout:{exc}]"
    try:
        err = (stderr.read() or b"").decode(errors="replace")
    except Exception as exc:
        err = f"[stderr_timeout:{exc}]"
    return (out + (("\nERR:\n" + err) if err.strip() else "")).strip()


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print("auth", auth)

    # Upload cron files via write from already-deployed paths if present; else cat from heredoc.
    # Prefer using files we just deploy with sftp.
    sftp = ssh.open_sftp()
    for rel in (
        "cron/exchange_price_battle_tick.sh",
        "cron/masternoder-price-battle.cron.d",
        "backend/services/exchange_price_battle_service.py",
        "scripts/exchange_price_battle_daemon.py",
        "data/exchange_price_battle_config.json",
    ):
        local = os.path.join(ROOT, rel.replace("/", os.sep))
        remote = f"/var/www/html/{rel}"
        remote_dir = os.path.dirname(remote)
        try:
            sftp.stat(remote_dir)
        except OSError:
            ssh.exec_command(f"mkdir -p '{remote_dir}'", timeout=10)
        sftp.put(local, remote)
        print("uploaded", rel)
    sftp.close()

    print("--- install cron ---")
    print(
        sh(
            ssh,
            "chmod +x /var/www/html/cron/exchange_price_battle_tick.sh && "
            "cp /var/www/html/cron/masternoder-price-battle.cron.d /etc/cron.d/masternoder-price-battle && "
            "chmod 644 /etc/cron.d/masternoder-price-battle && "
            "mkdir -p /var/www/html/logs && "
            "echo cron_installed",
        )
    )

    print("--- run one tick now ---")
    print(sh(ssh, "bash /var/www/html/cron/exchange_price_battle_tick.sh; echo exit:$?", timeout=120))

    print("--- log ---")
    print(sh(ssh, "tail -n 40 /var/www/html/logs/price_battle_daemon.log || echo no_log"))

    print("--- positions ---")
    print(
        sh(
            ssh,
            r"""cd /var/www/html && .venv/bin/python - <<'PY'
import os
os.environ.setdefault('DAEMON_QUIET','1')
os.environ.setdefault('LITE_APP','1')
from scripts.daemon_env import load_dotenv
load_dotenv()
from backend.services.exchange_price_battle_service import status, live_enabled
s = status()
print('live', live_enabled())
print('open', s.get('open_count'), 'last', s.get('last_tick'), 'tick', s.get('tick_count'))
for p in s.get('open') or []:
    print('POS', p.get('symbol'), 'entry', p.get('entry_price'), 'qty', p.get('qty'),
          'cost', p.get('cost_usd'), 'mode', p.get('mode'), 'id', p.get('id'))
PY""",
            timeout=90,
        )
    )
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
