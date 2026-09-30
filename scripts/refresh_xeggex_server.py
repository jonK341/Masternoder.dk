#!/usr/bin/env python3
"""Refresh XeggeX vault keys and probe auth before enabling live_trading.

Local:  python scripts/refresh_xeggex_server.py --probe-only
Remote: python scripts/refresh_xeggex_server.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

REMOTE_ROOT = "/var/www/html"

UPLOAD = [
    "scripts/configure_live_profit_max.py",
    "scripts/remote_vault_import.py",
    "scripts/daemon_env.py",
    "scripts/all_profit_daemons.py",
    "scripts/_daemon_env.cmd",
    "data/exchange_connectors_config.json",
    "data/exchange_extended_profit_config.json",
    "data/exchange_venue_api_config.json",
    "backend/services/exchange_venue_api_service.py",
    "backend/services/exchange_ai_trading_service.py",
    "backend/services/exchange_profit_path_service.py",
    "backend/services/exchange_profit_agent_skills_service.py",
    "backend/services/crypto_exchange_agent_service.py",
    "backend/routes/crypto_exchange_routes.py",
    "data/crypto_exchange/profit_path_protocol.json",
    "docs/PROFIT_CRITICAL_TOP25.md",
    "docs/PROFIT_PATH_PROTOCOL.md",
]


def xeggex_fix_steps(code: int, reason: str) -> list[str]:
    steps = [
        "1. Confirm XEGGEX_API_KEY and XEGGEX_API_SECRET in .env (or server .env for remote).",
        "2. Run: python scripts/remote_vault_import.py  (imports keys into secrets vault).",
        "3. Whitelist server IP on XeggeX API settings if required.",
        "4. Re-run: python scripts/refresh_xeggex_server.py --probe-only",
        "5. When probe returns 200: python scripts/configure_live_profit_max.py (sets live_trading=true).",
    ]
    if code == 401 or "401" in reason:
        steps.insert(2, "2b. 401 = bad key/secret or IP blocked — regenerate API key on XeggeX dashboard.")
    if "no_credentials" in reason:
        steps = [
            "1. Set XEGGEX_API_KEY + XEGGEX_API_SECRET in .env.",
            "2. python scripts/remote_vault_import.py",
            "3. python scripts/refresh_xeggex_server.py --probe-only",
        ]
    return steps


def probe_xeggex_local() -> tuple[bool, str, int]:
    from scripts.daemon_env import load_dotenv

    load_dotenv()
    from backend.services.exchange_venue_api_service import get_account_balance, venue_has_credentials

    if not venue_has_credentials("xeggex"):
        return False, "no_credentials_in_vault", 0
    try:
        res = get_account_balance("xeggex", dry_run=False)
    except Exception as exc:
        return False, str(exc), 0
    code = int(res.get("status_code") or 0)
    if res.get("success") and code == 200:
        return True, "ok", code
    err = str(res.get("error") or res.get("body") or "probe_failed")
    return False, f"http_{code}:{err}", code


def print_probe_report(*, label: str = "local") -> bool:
    ok, reason, code = probe_xeggex_local()
    print(f"XeggeX probe ({label}): ok={ok} status={code} reason={reason}")
    if not ok:
        print("Action steps:")
        for step in xeggex_fix_steps(code, reason):
            print(f"  {step}")
    else:
        print("Probe passed — safe to run configure_live_profit_max.py (enables xeggex live_trading).")
    return ok


def main() -> int:
    if "--probe-only" in sys.argv:
        return 0 if print_probe_report(label="local") else 1

    print("Local preflight:")
    local_ok = print_probe_report(label="local")
    if not local_ok:
        print("\nSkipping remote upload until local vault has working XeggeX keys (use --force-remote to override).")
        if "--force-remote" not in sys.argv:
            return 1

    from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"Connected ({auth})")
    try:
        sftp = ssh.open_sftp()
        try:
            for rel in UPLOAD:
                local = os.path.join(ROOT, rel.replace("/", os.sep))
                if not os.path.isfile(local):
                    print(f"  skip missing {rel}")
                    continue
                remote = f"{REMOTE_ROOT}/{rel.replace(chr(92), '/')}"
                sftp.put(local, remote)
                print(f"  uploaded {rel}")
        finally:
            sftp.close()

        remote_cmd = (
            f"cd {REMOTE_ROOT} && "
            "set -a && [ -f .env ] && . ./.env && set +a && "
            "export DAEMON_QUIET=1 LITE_APP=1 EXCHANGE_ARBITRAGE_LIVE=1 && "
            "python3 scripts/remote_vault_import.py && "
            "python3 scripts/configure_live_profit_max.py && "
            "python3 -c \""
            "import os; "
            "from scripts.daemon_env import load_dotenv; load_dotenv(); "
            "from backend.services.exchange_venue_api_service import get_account_balance, venue_has_credentials, parse_spot_balances; "
            "print('xeggex_creds', venue_has_credentials('xeggex')); "
            "r=get_account_balance('xeggex', dry_run=False); "
            "print('xeggex_probe', r.get('success'), r.get('status_code')); "
            "b=parse_spot_balances('xeggex', dry_run=False); "
            "print('xeggex_balances', {k: round(v, 4) for k, v in list(b.items())[:8]});"
            "\""
        )
        print("Refreshing XeggeX vault + connector config on server...")
        _, stdout, stderr = ssh.exec_command(remote_cmd, timeout=240)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        code = stdout.channel.recv_exit_status()
        if out.strip():
            print(out.strip()[-4000:])
        if "xeggex_probe False 401" in out or "xeggex_probe False" in out:
            print("\nRemote XeggeX probe FAILED — live_trading stays false until fixed:")
            for step in xeggex_fix_steps(401, out):
                print(f"  {step}")
        elif "xeggex_probe True 200" in out:
            print("Remote XeggeX probe OK — live_trading enabled if configure_live_profit_max ran.")
        if code != 0:
            print(f"Remote refresh failed [{code}]")
            if err.strip():
                print(err.strip()[-2000:])
            return 1
        if err.strip():
            print(err.strip()[-1500:])
        print("Done — restart profit daemons if running.")
    finally:
        ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
