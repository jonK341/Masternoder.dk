#!/usr/bin/env python3
"""Stop losing Binance grid + rotation auto-buys on production; keep NonKYC grid live.

Uploads:
  - data/crypto_exchange/profit_path_protocol.json  (rotation live/auto OFF)
  - data/exchange_grid_bot_config.json             (Binance disabled; NonKYC only)
  - backend/services/exchange_grid_bot_service.py  (honors disabled_venues)

Sets remote .env:
  EXCHANGE_ROTATION_LIVE=0
  EXCHANGE_ROTATION_AUTO=0
  (does NOT force EXCHANGE_GRID_LIVE=0 — NonKYC grid stays live)

On server: pause Binance, cancel tracked Binance grid orders, restart profit daemon.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE_ROOT = "/var/www/html"
REMOTE_ENV = f"{REMOTE_ROOT}/.env"

UPLOADS = [
    ("data/crypto_exchange/profit_path_protocol.json",
     f"{REMOTE_ROOT}/data/crypto_exchange/profit_path_protocol.json"),
    ("data/exchange_grid_bot_config.json",
     f"{REMOTE_ROOT}/data/exchange_grid_bot_config.json"),
    ("backend/services/exchange_grid_bot_service.py",
     f"{REMOTE_ROOT}/backend/services/exchange_grid_bot_service.py"),
]

ENV_LOCKS = {
    "EXCHANGE_ROTATION_LIVE": "0",
    "EXCHANGE_ROTATION_AUTO": "0",
}


def upsert_remote_key(ssh, key: str, value: str) -> str:
    safe_val = value.replace("'", "'\"'\"'")
    cmd = (
        f"test -f {REMOTE_ENV} || touch {REMOTE_ENV}; "
        f"if grep -q '^{key}=' {REMOTE_ENV}; then "
        f"  sed -i 's|^{key}=.*|{key}={safe_val}|' {REMOTE_ENV}; "
        f"  echo updated; "
        f"else "
        f"  echo '{key}={safe_val}' >> {REMOTE_ENV}; "
        f"  echo appended; "
        f"fi"
    )
    _, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if err and "updated" not in out and "appended" not in out:
        return f"err:{err[-200:]}"
    return out or "ok"


def main() -> int:
    for local, _remote in UPLOADS:
        path = os.path.join(ROOT, local.replace("/", os.sep))
        if not os.path.isfile(path):
            print(f"MISSING {local}")
            return 1

    # Fail fast: interactive getpass hangs in agent shells.
    from deploy_ssh_env import _load_deploy_env_from_dotenv

    _load_deploy_env_from_dotenv()
    if not (os.environ.get("DEPLOY_PASS") or "").strip():
        print(
            "ERROR: DEPLOY_PASS is unset (commented or missing in .env). "
            "Uncomment DEPLOY_PASS=... then re-run: python scripts/lock_path_b_inventory.py"
        )
        return 2

    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"Connected ({auth})")
    try:
        sftp = ssh.open_sftp()
        for local, remote in UPLOADS:
            path = os.path.join(ROOT, local.replace("/", os.sep))
            remote_dir = os.path.dirname(remote)
            try:
                sftp.stat(remote_dir)
            except OSError:
                ssh.exec_command(f"mkdir -p {remote_dir}", timeout=30)
            sftp.put(path, remote)
            print(f"uploaded {local}")
        sftp.close()

        for key, val in ENV_LOCKS.items():
            result = upsert_remote_key(ssh, key, val)
            print(f"env {key}={val} ({result})")

        verify = (
            f"cd {REMOTE_ROOT} && "
            "export DAEMON_QUIET=1 LITE_APP=1 && "
            "python3 - <<'PY'\n"
            "from scripts.daemon_env import load_dotenv\n"
            "load_dotenv()\n"
            "from backend.services.exchange_grid_bot_service import (\n"
            "  pause_venue, reset_open_orders, grid_targets, load_config, grid_live_enabled)\n"
            "from backend.services.exchange_swap_rotation_service import (\n"
            "  rotation_live_enabled, rotation_auto_execute_enabled)\n"
            "print('pause', pause_venue('binance', reason='losing_dense_mm', manual=True))\n"
            "print('cancel', reset_open_orders('binance'))\n"
            "cfg = load_config()\n"
            "tg = grid_targets(cfg)\n"
            "print('disabled_venues=', cfg.get('disabled_venues'))\n"
            "print('targets=', sorted({v for v,_ in tg}))\n"
            "print('target_count=', len(tg))\n"
            "print('binance_targets=', sum(1 for v,_ in tg if v=='binance'))\n"
            "print('runtime.rotation_live=', rotation_live_enabled())\n"
            "print('runtime.rotation_auto=', rotation_auto_execute_enabled())\n"
            "print('runtime.grid_live=', grid_live_enabled())\n"
            "print('allow_sell_existing=', cfg.get('allow_sell_existing_inventory'))\n"
            "PY\n"
            "grep -E '^(EXCHANGE_ROTATION_LIVE|EXCHANGE_ROTATION_AUTO|EXCHANGE_GRID_LIVE)=' "
            f"{REMOTE_ENV} || true; "
            "systemctl restart masternoder-profit-daemon.service; "
            "sleep 2; "
            "systemctl is-active masternoder-profit-daemon.service"
        )
        _, stdout, stderr = ssh.exec_command(verify, timeout=180)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        if out.strip():
            print(out.strip())
        if err.strip():
            print("stderr:", err.strip()[-1200:])
        code = stdout.channel.recv_exit_status()
        return 0 if code == 0 else 1
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
