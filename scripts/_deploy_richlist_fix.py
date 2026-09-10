#!/usr/bin/env python3
"""Deploy mn2_explorer_data.py fix and restart uWSGI."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

LOCAL = ROOT / "backend/services/mn2_explorer_data.py"
REMOTE = "/var/www/html/backend/services/mn2_explorer_data.py"


def _health() -> dict:
    try:
        req = urllib.request.Request("https://masternoder.dk/api/mn2/health", headers={"User-Agent": "DeployRichFix/1.0"})
        with urllib.request.urlopen(req, timeout=45) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})")
    sftp = ssh.open_sftp()
    sftp.put(str(LOCAL), REMOTE)
    sftp.close()
    print(f"Uploaded {LOCAL.name} -> {REMOTE}")

    _, stdout, stderr = ssh.exec_command(
        "systemctl restart uwsgi-vidgenerator.service && sleep 3 && systemctl is-active uwsgi-vidgenerator.service",
        timeout=60,
    )
    out = stdout.read().decode()
    err = stderr.read().decode()
    print("uwsgi:", out.strip() or err.strip())

    _, stdout, _ = ssh.exec_command(
        "cd /var/www/html && PYTHONPATH=/var/www/html python3 -c \""
        "from backend.services import mn2_explorer_data as ed; "
        "print('synced', ed.rich_list_index_synced()); "
        "st=ed.explorer_status(); "
        "print('explorer', st.get('status')); "
        "print('rich', (st.get('checks') or {}).get('rich_list'))\"",
        timeout=30,
    )
    print(stdout.read().decode())

    ssh.close()

    h = _health()
    print("\n--- public MN2 health ---")
    print("HTTP status implied:", h.get("status"))
    print("success:", h.get("success"))
    probe = (h.get("components") or {}).get("explorer_probe") or {}
    rl = ((probe.get("detail") or {}).get("checks") or {}).get("rich_list") or {}
    print("rich_list:", rl)
    print("overall status:", h.get("status"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
