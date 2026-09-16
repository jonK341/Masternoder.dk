"""Fingerprint DISCORD_PUBLIC_KEY local vs server (no secret values printed)."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass


def _local_key() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("DISCORD_PUBLIC_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _fp(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def main() -> None:
    local = _local_key()
    print("local_key_fp:", _fp(local))
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print("ssh auth:", auth)
    py = (
        "import hashlib\n"
        "val=''\n"
        "with open('/var/www/html/.env') as f:\n"
        "  for line in f:\n"
        "    if line.strip().startswith('DISCORD_PUBLIC_KEY='):\n"
        "      val=line.split('=',1)[1].strip().strip('\"').strip(\"'\")\n"
        "      break\n"
        "print(hashlib.sha256(val.encode()).hexdigest()[:16])\n"
    )
    _, stdout, stderr = ssh.exec_command(f"python3 - <<'PY'\n{py}\nPY", timeout=20)
    server_fp = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if err:
        print("remote stderr:", err[:200])
    print("server_key_fp:", server_fp)
    print("keys_match:", _fp(local) == server_fp)
    ssh.close()


if __name__ == "__main__":
    main()
