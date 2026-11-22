#!/usr/bin/env python3
"""Deploy tuned price-battle rules and run one prod tick."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

FILES = [
    "backend/services/exchange_price_battle_service.py",
    "data/exchange_price_battle_config.json",
    "scripts/exchange_price_battle_daemon.py",
    "tests/unit/test_exchange_price_battle.py",
]


def sh(ssh, cmd: str, timeout: int = 120) -> str:
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
    sftp = ssh.open_sftp()
    for rel in FILES:
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

    print("--- tick ---")
    print(sh(ssh, "bash /var/www/html/cron/exchange_price_battle_tick.sh; echo EXIT:$?", timeout=180))
    print("--- status ---")
    print(
        sh(
            ssh,
            r"""cd /var/www/html && .venv/bin/python - <<'PY'
import os
os.environ.setdefault('DAEMON_QUIET','1')
os.environ.setdefault('LITE_APP','1')
from scripts.daemon_env import load_dotenv
load_dotenv()
from backend.services.exchange_price_battle_service import status, load_config
cfg=load_config()
s=status()
print('cfg', 'min_profit_bps', cfg.get('min_profit_bps'), 'fee', cfg.get('fee_buffer_bps'),
      'max_hold', cfg.get('max_hold_sec'), 'dip', cfg.get('buy_dip_only'), cfg.get('dip_bps'))
print('open', s.get('open_count'), 'tick', s.get('tick_count'), 'last', s.get('last_tick'))
for p in s.get('open') or []:
    print('POS', p.get('symbol'), 'entry', p.get('entry_price'), 'cost', p.get('cost_usd'),
          'age_hint_bought', p.get('bought_at'))
# last sell lines
path=s.get('sells_log')
try:
    lines=open(path,encoding='utf-8').read().strip().splitlines()[-5:]
    print('sells_tail', len(lines))
    for ln in lines:
        print(ln[:240])
except Exception as e:
    print('no_sells', e)
PY""",
            timeout=90,
        )
    )
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
