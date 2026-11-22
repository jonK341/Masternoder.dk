#!/usr/bin/env python3
"""Camgirls P2 prod: catalog db flag, sync, payouts, full uwsgi restart, status check.

Uses deploy_ssh_env (loads DEPLOY_PASS from .env when set). Does not print secrets.

A HUP/reload is not enough for CAMGIRLS_CATALOG_SOURCE — systemd EnvironmentFile
is only re-read on restart of uwsgi-vidgenerator (+ 5001).
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from deploy_ssh_env import connect_deploy_ssh  # noqa: E402


def _sh(ssh, cmd: str, timeout: int = 180) -> tuple[int, str]:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    stdout.channel.settimeout(timeout)
    stderr.channel.settimeout(timeout)
    code = stdout.channel.recv_exit_status()
    try:
        text = (stdout.read() + stderr.read()).decode("utf-8", "replace").strip()
    except Exception as exc:
        text = f"(read failed: {exc})"
    return code, text


def main() -> int:
    ssh, method, _pw = connect_deploy_ssh()
    print(f"[camgirls-p2] SSH via {method}")

    steps: list[tuple[str, str, int]] = [
        (
            "ensure catalog source db",
            r"""
cd /var/www/html || exit 1
if grep -q '^CAMGIRLS_CATALOG_SOURCE=' .env 2>/dev/null; then
  sed -i 's/^CAMGIRLS_CATALOG_SOURCE=.*/CAMGIRLS_CATALOG_SOURCE=db/' .env
else
  printf '\nCAMGIRLS_CATALOG_SOURCE=db\n' >> .env
fi
grep '^CAMGIRLS_CATALOG_SOURCE=' .env
""",
            60,
        ),
        (
            "sync catalog db",
            "cd /var/www/html && bash scripts/camgirls_py.sh scripts/camgirls_sync_catalog_db.py",
            180,
        ),
        (
            "provision payouts",
            "cd /var/www/html && bash scripts/camgirls_py.sh "
            "scripts/camgirls_provision_payout_addresses.py --check-rpc",
            300,
        ),
        (
            "restart uwsgi (reload env)",
            "systemctl restart uwsgi-vidgenerator 2>&1; "
            "systemctl restart uwsgi-vidgenerator-5001 2>&1; "
            "sleep 8; "
            "systemctl is-active uwsgi-vidgenerator uwsgi-vidgenerator-5001 2>&1; "
            "echo restart_done",
            90,
        ),
        (
            "status",
            "curl -s --max-time 45 http://127.0.0.1:5000/api/camgirls/status | "
            "python3 -c \"import sys,json; d=json.load(sys.stdin); "
            "print('catalog='+str(d.get('catalog_source'))"
            "+' performers='+str(d.get('performers_count'))"
            "+' voice='+str(d.get('voice_live')))\"",
            60,
        ),
    ]

    failed = 0
    catalog_ok = False
    for label, cmd, timeout in steps:
        print(f"\n=== {label} ===")
        code, out = _sh(ssh, cmd, timeout=timeout)
        print(out[:2500] if out else "(empty)")
        print(f"exit {code}")
        if code != 0:
            failed += 1
        if label == "status" and "catalog=db" in out and "performers=250" in out:
            catalog_ok = True
        if label == "status" and "catalog=json" in out:
            # One more restart attempt if workers still stale
            print("\n=== retry uwsgi restart (stale catalog=json) ===")
            code2, out2 = _sh(
                ssh,
                "systemctl restart uwsgi-vidgenerator uwsgi-vidgenerator-5001; sleep 10; "
                "curl -s --max-time 45 http://127.0.0.1:5000/api/camgirls/status | "
                "python3 -c \"import sys,json; d=json.load(sys.stdin); "
                "print('catalog='+str(d.get('catalog_source'))"
                "+' performers='+str(d.get('performers_count'))"
                "+' voice='+str(d.get('voice_live')))\"",
                timeout=90,
            )
            print(out2[:2500] if out2 else "(empty)")
            print(f"exit {code2}")
            if "catalog=db" in out2:
                catalog_ok = True
            elif code2 != 0 or "catalog=db" not in out2:
                failed += 1

    ssh.close()
    if not catalog_ok:
        print("\n[camgirls-p2] WARN: live status did not report catalog=db", file=sys.stderr)
        return 1
    print("\n[camgirls-p2] OK catalog=db")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
