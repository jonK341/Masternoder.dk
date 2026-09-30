"""Compare DISCORD_PUBLIC_KEY shape on server vs local .env (no secrets printed)."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass  # noqa: E402


def _load_local_key() -> str:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DISCORD_PUBLIC_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _shape(key: str) -> dict:
    k = (key or "").strip()
    return {
        "set": bool(k),
        "len": len(k),
        "hex": bool(k) and bool(re.fullmatch(r"[0-9a-fA-F]+", k)),
        "prefix0x": k.lower().startswith("0x"),
    }


def main() -> None:
    local = _load_local_key()
    print("local:", _shape(local))

    server_pass = require_deploy_pass()
    ssh, auth, _ = connect_deploy_ssh(server_pass)
    print("ssh auth:", auth)
    cmd = (
        "python3 - <<'PY'\n"
        "import re\n"
        "val=''\n"
        "try:\n"
        "  with open('/var/www/html/.env') as f:\n"
        "    for line in f:\n"
        "      if line.strip().startswith('DISCORD_PUBLIC_KEY='):\n"
        "        val=line.split('=',1)[1].strip().strip('\"').strip(\"'\")\n"
        "        break\n"
        "except OSError:\n"
        "  pass\n"
        "k=val.strip()\n"
        "print('set', bool(k))\n"
        "print('len', len(k))\n"
        "print('hex', bool(k) and bool(re.fullmatch(r'[0-9a-fA-F]+', k)))\n"
        "print('prefix0x', k.lower().startswith('0x'))\n"
        "PY"
    )
    _, stdout, stderr = ssh.exec_command(cmd, timeout=20)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if err:
        print("remote stderr:", err[:200])
    print("server:")
    for line in out.splitlines():
        print(" ", line)
    ssh.close()

    ls, ss = _shape(local), {}
    for line in out.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            ss[parts[0]] = parts[1]
    if ls["set"] and ss.get("set") == "True":
        print("match_len:", ls["len"] == int(ss.get("len", "-1")))


if __name__ == "__main__":
    main()
