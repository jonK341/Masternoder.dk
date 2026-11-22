#!/usr/bin/env python3
"""Fire Path B once on production: keep Binance grid paused, resume NonKYC, run one live arb tick.

Uploads current locks (rotation off, Binance disabled in grid config), then on server:
  - pause_venue(binance)
  - resume_venue(nonkyc)
  - reset_open_orders(binance)
  - exchange_master_daemon.run_once() for spatial arb
  - print DOGE funding + tick summary
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
            print(f"env {key}={val} ({upsert_remote_key(ssh, key, val)})")

        remote = (
            f"cd {REMOTE_ROOT} && "
            "export DAEMON_QUIET=1 LITE_APP=1 EXCHANGE_ARBITRAGE_LIVE=1 "
            "EXCHANGE_LIVE_PROFIT_MAX=1 BINANCE_QUOTE=USDC EXCHANGE_FORCE_IPV4=1 "
            "EXCHANGE_ROTATION_LIVE=0 EXCHANGE_ROTATION_AUTO=0 && "
            "python3 - <<'PY'\n"
            "import json\n"
            "from scripts.daemon_env import load_dotenv\n"
            "load_dotenv()\n"
            "from backend.services.exchange_venue_api_service import parse_spot_balances, opportunity_funded\n"
            "from backend.services.exchange_arbitrage_service import scan_opportunities, live_enabled\n"
            "from backend.services.exchange_grid_bot_service import (\n"
            "  pause_venue, resume_venue, reset_open_orders, paused_venues, grid_targets, load_config)\n"
            "from scripts.exchange_master_daemon import run_once\n"
            "print('live_enabled', live_enabled())\n"
            "b = parse_spot_balances('binance', dry_run=False)\n"
            "n = parse_spot_balances('nonkyc', dry_run=False)\n"
            "print('balances', json.dumps({'binance': {'USDC': b.get('USDC'), 'DOGE': b.get('DOGE')}, "
            "'nonkyc': {'USDT': n.get('USDT'), 'DOGE': n.get('DOGE')}}, default=str))\n"
            "scan = scan_opportunities(['DOGE','XRP','LTC','BNB'], ['binance','nonkyc'], notional_usd=25)\n"
            "opps = scan.get('opportunities') or []\n"
            "print('scan profitable', scan.get('profitable_count'), 'min_margin', scan.get('min_margin_bps'))\n"
            "if opps:\n"
            "  top = opps[0]\n"
            "  print('best', top.get('symbol'), top.get('net_bps'), "
            "top.get('buy_venue'), '->', top.get('sell_venue'))\n"
            "  print('funding', opportunity_funded(top))\n"
            "print('pause_binance', pause_venue('binance', reason='losing_dense_mm', manual=True))\n"
            "print('cancel_binance', reset_open_orders('binance'))\n"
            "print('resume_nonkyc', resume_venue('nonkyc'))\n"
            "print('paused_now', paused_venues())\n"
            "print('grid_targets_venues', sorted({v for v,_ in grid_targets(load_config())}))\n"
            "tick = run_once(auto_sweep=False)\n"
            "plat = (tick.get('platform') or {}) if isinstance(tick, dict) else {}\n"
            "arb = ((plat.get('results') or {}).get('arbitrage') or {})\n"
            "print('tick_keys', sorted(tick.keys()) if isinstance(tick, dict) else type(tick))\n"
            "print('arb_executed', arb.get('executed_count'), 'actions', len(arb.get('actions') or []))\n"
            "for a in (arb.get('actions') or [])[:8]:\n"
            "  print(' action', {k:a.get(k) for k in "
            "('agent_id','symbol','success','reason','net_bps','live','realized_profit_usd','mode')})\n"
            "print('best_qualifying', arb.get('best_qualifying'))\n"
            "PY\n"
            "systemctl restart masternoder-profit-daemon.service; "
            "sleep 2; systemctl is-active masternoder-profit-daemon.service"
        )
        _, stdout, stderr = ssh.exec_command(remote, timeout=240)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        if out.strip():
            print(out.strip())
        if err.strip():
            print("stderr:", err.strip()[-1500:])
        return 0 if stdout.channel.recv_exit_status() == 0 else 1
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
