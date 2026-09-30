#!/usr/bin/env python3
"""Push exchange live keys from local .env to server and import into vault."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE_ENV = "/var/www/html/.env"
REMOTE_ROOT = "/var/www/html"

UPLOAD_FILES = [
    "scripts/configure_live_trading.py",
    "scripts/configure_paypal_payout.py",
    "scripts/enable_live_daemons.py",
    "scripts/daemon_env.py",
    "scripts/remote_vault_import.py",
    "data/exchange_connectors_config.json",
    "data/exchange_sales_pool_config.json",
    "data/crypto_exchange/payout_config.json",
    "data/exchange_treasury_config.json",
    "backend/services/exchange_binance_withdraw_service.py",
    "backend/services/exchange_binance_time_service.py",
    "backend/services/exchange_live_execution_service.py",
    "backend/services/exchange_secrets_vault_service.py",
    "backend/services/exchange_arbitrage_service.py",
    "backend/services/exchange_sales_pool_service.py",
    "backend/services/exchange_payout_service.py",
    "backend/services/crypto_exchange_service.py",
    "backend/services/external_exchange_connector_service.py",
    "backend/services/exchange_venue_api_service.py",
    "backend/services/exchange_http_util.py",
    "backend/services/exchange_ai_trading_service.py",
    "backend/services/exchange_treasury_service.py",
    "backend/services/exchange_treasury_liquidity_service.py",
    "backend/routes/crypto_exchange_routes.py",
    "data/mn2_masternode_config.json",
    "backend/services/mn2_masternode_service.py",
    "dashboard/agents_control/index.html",
    "backend/services/agent_marketplace_service.py",
    "backend/services/trading_bots_control_service.py",
    "backend/services/exchange_extended_profit_service.py",
    "data/exchange_extended_profit_config.json",
    "scripts/exchange_master_daemon.py",
    "scripts/configure_live_profit_max.py",
    "scripts/all_profit_daemons.py",
    "scripts/daemon_preflight.py",
    "scripts/daemon_env.py",
    "data/exchange_venue_api_config.json",
    "cron/exchange_master_tick.sh",
    "cron/masternoder-exchange-master.cron.d",
    "scripts/configure_live_profit_max.py",
    "scripts/profit_status_report.py",
    "scripts/_server_live_check_once.py",
    "docs/LIVE_PROFIT_TRADING.md",
]

KEYS = [
    "EXCHANGE_ARBITRAGE_LIVE",
    "EXCHANGE_VAULT_KEY",
    "EXCHANGE_PAYOUT_PAYPAL_LIVE",
    "EXCHANGE_PAYOUT_PAYPAL_SHARE_PCT",
    "EXCHANGE_PAYOUT_PAYPAL_EMAIL",
    "BINANCE_API_KEY",
    "BINANCE_API_SECRET",
    "OKX_API_KEY",
    "OKX_API_SECRET",
    "BYBIT_API_KEY",
    "BYBIT_API_SECRET",
    "NONKYC_API_KEY",
    "NONKYC_API_SECRET",
    "KUCOIN_API_KEY",
    "KUCOIN_API_SECRET",
    "XEGGEX_API_KEY",
    "XEGGEX_API_SECRET",
    "EXCHANGE_PROFIT_PROFILE",
    "EXCHANGE_LIVE_PROFIT_MAX",
    "EXCHANGE_LIVE_MICRO_USD",
    "BINANCE_QUOTE",
    "EXCHANGE_AUTO_PAYPAL_SWEEP",
    "EXCHANGE_FORCE_IPV4",
]


def load_local_env() -> dict[str, str]:
    path = os.path.join(ROOT, ".env")
    out: dict[str, str] = {}
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key, val = key.strip(), val.strip().strip('"').strip("'")
            if key and val:
                out[key] = val
    return out


def upsert_remote_key(ssh, key: str, value: str) -> str:
    """Set key=value in remote .env without printing the value."""
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
        return f"error:{err[:120]}"
    return out or "ok"


def upload_files(ssh) -> None:
    sftp = ssh.open_sftp()
    try:
        for rel in UPLOAD_FILES:
            local = os.path.join(ROOT, rel.replace("/", os.sep))
            if not os.path.isfile(local):
                print(f"  skip missing local {rel}")
                continue
            remote = f"{REMOTE_ROOT}/{rel.replace(chr(92), '/')}"
            remote_dir = os.path.dirname(remote).replace(chr(92), "/")
            parts = remote_dir.replace(REMOTE_ROOT, "").strip("/").split("/")
            cur = REMOTE_ROOT
            for part in parts:
                if not part:
                    continue
                cur = f"{cur}/{part}"
                try:
                    sftp.stat(cur)
                except OSError:
                    sftp.mkdir(cur)
            sftp.put(local, remote)
            print(f"  uploaded {rel}")
    finally:
        sftp.close()


def main() -> int:
    local = load_local_env()
    to_sync = {k: local[k] for k in KEYS if local.get(k)}
    if not to_sync:
        print("No exchange keys found in local .env.")
        print("Add uncommented lines, e.g. BINANCE_API_KEY=... and BINANCE_API_SECRET=...")
        print("Then save the file and run this script again.")
        return 1

    print(f"Syncing {len(to_sync)} key(s) to {REMOTE_ENV} ...")
    for k in to_sync:
        print(f"  - {k}")

    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"Connected ({auth})")
    try:
        print("Uploading exchange live scripts/config...")
        upload_files(ssh)

        for key, val in to_sync.items():
            status = upsert_remote_key(ssh, key, val)
            print(f"  {key}: {status}")

        remote_cmd = (
            f"cd {REMOTE_ROOT} && "
            "export DAEMON_QUIET=1 LITE_APP=1 && "
            "python3 scripts/remote_vault_import.py && "
            "python3 scripts/configure_live_profit_max.py && "
            "python3 scripts/configure_paypal_payout.py 2>/dev/null || true && "
            "python3 scripts/profit_status_report.py --save 2>/dev/null | tail -40 && "
            "chmod +x cron/exchange_master_tick.sh 2>/dev/null || true && "
            "sed -i 's/\\r$//' cron/exchange_master_tick.sh 2>/dev/null || true && "
            "cp cron/masternoder-exchange-master.cron.d /etc/cron.d/masternoder-exchange-master "
            "&& chmod 644 /etc/cron.d/masternoder-exchange-master && "
            "chmod 640 .env && chown root:www-data .env && "
            "systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001 && "
            "bash cron/exchange_master_tick.sh 2>&1 | tail -5"
        )
        print("Importing keys into server vault...")
        _, stdout, stderr = ssh.exec_command(remote_cmd, timeout=180)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        code = stdout.channel.recv_exit_status()
        if out.strip():
            print(out.strip()[-3000:])
        if code != 0:
            print(f"Remote setup failed [{code}]")
            if err.strip():
                print(err.strip()[-1500:])
            return 1
        print("Done — server .env updated, vault import run, uwsgi restarted.")
        print("If exchange daemons run on the server, restart them too.")
    finally:
        ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
