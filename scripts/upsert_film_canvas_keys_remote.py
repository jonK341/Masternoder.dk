#!/usr/bin/env python3
"""Upsert FAL_API_KEY + DRAMACANVA_API_KEY from local .env onto the server.

Does not print secret values. Backs up the remote .env, upserts only these keys,
then restarts the uwsgi services so the monitor can see them.
"""
from __future__ import annotations

import base64
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

from dotenv import load_dotenv

from deploy_ssh_env import connect_deploy_ssh, deploy_host, require_deploy_pass

load_dotenv(".env")

KEYS = ("FAL_API_KEY", "DRAMACANVA_API_KEY")
ENV_PATH = "/var/www/html/.env"


def main() -> int:
    values = {key: (os.getenv(key) or "").strip() for key in KEYS}
    missing = [key for key, value in values.items() if not value]
    if missing:
        print(f"missing local keys: {', '.join(missing)}")
        return 1

    encoded = {
        key: base64.b64encode(value.encode("utf-8")).decode("ascii")
        for key, value in values.items()
    }

    remote_py = f"""
import base64
from pathlib import Path

path = Path({ENV_PATH!r})
text = path.read_text(encoding="utf-8", errors="replace")
updates = {{
    "FAL_API_KEY": base64.b64decode({encoded["FAL_API_KEY"]!r}).decode("utf-8"),
    "DRAMACANVA_API_KEY": base64.b64decode({encoded["DRAMACANVA_API_KEY"]!r}).decode("utf-8"),
}}
lines = text.splitlines(keepends=True)
seen = set()
out = []
for line in lines:
    raw = line.strip()
    if raw and not raw.startswith("#") and "=" in raw:
        key = raw.split("=", 1)[0].strip()
        if key in updates:
            out.append(f"{{key}}={{updates[key]}}\\n")
            seen.add(key)
            continue
    out.append(line)
missing = [key for key in updates if key not in seen]
if missing:
    if out and not str(out[-1]).endswith("\\n"):
        out.append("\\n")
    out.append("\\n# Film canvas providers\\n")
    for key in missing:
        out.append(f"{{key}}={{updates[key]}}\\n")
path.write_text("".join(out), encoding="utf-8")
print("upserted", ",".join(sorted(updates)))
for key, value in updates.items():
    masked = (value[:4] + "…" + value[-4:]) if len(value) > 10 else "***"
    print(f"OK {{key}} len={{len(value)}} mask={{masked}}")
"""

    remote_sh = f"""set -euo pipefail
test -f {ENV_PATH}
BK={ENV_PATH}.bak.filmcanvas.$(date -u +%Y%m%dT%H%M%SZ)
cp {ENV_PATH} "$BK"
echo "backup=$BK"
python3 - <<'PY'
{remote_py}
PY
chmod 640 {ENV_PATH}
chown root:www-data {ENV_PATH} 2>/dev/null || true
echo "== reload uwsgi =="
systemctl restart uwsgi-vidgenerator 2>&1 || true
systemctl restart uwsgi-vidgenerator-5001 2>&1 || true
sleep 3
systemctl is-active uwsgi-vidgenerator uwsgi-vidgenerator-5001 2>&1 || true
"""

    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"connected auth={auth} host_ok={bool(deploy_host())}")
    try:
        _, stdout, stderr = ssh.exec_command(remote_sh, timeout=120)
        out = (stdout.read() or b"").decode("utf-8", errors="replace").strip()
        err = (stderr.read() or b"").decode("utf-8", errors="replace").strip()
        code = stdout.channel.recv_exit_status()
        if out:
            print(out)
        if err:
            print("[stderr]", err[:800])
        return code
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
