#!/usr/bin/env python3
"""
One-time: generate a deploy SSH key and install the public key on the server.

After this, deploy scripts authenticate automatically (no DEPLOY_PASS needed).

  python scripts/setup_deploy_ssh_key.py --ask-pass

Optional:
  --key-path C:\\Users\\you\\.ssh\\id_ed25519_deploy
  --print-pub-only   Show public key for manual install
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import (
    _password_connect,
    _try_ssh_key_auth,
    deploy_host,
    deploy_user,
    require_deploy_pass,
)


def _default_deploy_key_path() -> str:
    env = (os.environ.get("DEPLOY_KEY_PATH") or "").strip()
    if env:
        return os.path.expanduser(env)
    return os.path.expanduser("~/.ssh/id_ed25519_deploy")


def _ensure_key(key_path: str) -> str:
    pub_path = key_path + ".pub"
    if os.path.isfile(key_path) and os.path.isfile(pub_path):
        return pub_path
    ssh_dir = os.path.dirname(key_path)
    os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
    print(f"Generating key: {key_path}")
    subprocess.run(
        [
            "ssh-keygen",
            "-t",
            "ed25519",
            "-f",
            key_path,
            "-N",
            "",
            "-C",
            f"masternoder-deploy@{deploy_host()}",
        ],
        check=True,
    )
    return pub_path


def _install_pubkey(ssh, pub_line: str) -> None:
    safe = pub_line.replace("'", "'\"'\"'")
    cmd = f"""bash -s <<'EOF'
set -e
mkdir -p ~/.ssh
chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
grep -qxF '{safe}' ~/.ssh/authorized_keys || echo '{safe}' >> ~/.ssh/authorized_keys
echo installed
EOF"""
    _, stdout, stderr = ssh.exec_command(cmd, timeout=60)
    out = (stdout.read() or b"").decode().strip()
    err = (stderr.read() or b"").decode().strip()
    if "installed" not in out:
        raise RuntimeError(err or out or "authorized_keys install failed")


def main() -> int:
    p = argparse.ArgumentParser(description="Install deploy SSH key on server (one-time)")
    p.add_argument("--ask-pass", action="store_true", help="Prompt for root password once")
    p.add_argument("--key-path", default="", help="Private key path (default ~/.ssh/id_ed25519_deploy)")
    p.add_argument("--print-pub-only", action="store_true")
    args = p.parse_args()

    key_path = os.path.expanduser(args.key_path or _default_deploy_key_path())
    pub_path = _ensure_key(key_path)
    pub_line = open(pub_path, encoding="utf-8").read().strip()
    print(f"Public key: {pub_path}")
    print(pub_line)
    if args.print_pub_only:
        return 0

    host, user = deploy_host(), deploy_user()
    existing = _try_ssh_key_auth(host, user, timeout=30)
    if existing:
        print(f"Already works with {existing[1]} — no install needed.")
        print(f"Add to .env:  DEPLOY_KEY_PATH={key_path}")
        existing[0].close()
        return 0

    pw = require_deploy_pass(force_prompt=args.ask_pass)
    print(f"Installing key on {user}@{host} ...")
    ssh = _password_connect(host, user, pw, timeout=30)
    try:
        _install_pubkey(ssh, pub_line)
    finally:
        ssh.close()

    os.environ["DEPLOY_KEY_PATH"] = key_path
    verify = _try_ssh_key_auth(host, user, timeout=30)
    if not verify:
        os.environ["DEPLOY_KEY_PATH"] = key_path
        verify = _try_ssh_key_auth(host, user, timeout=30)
    if not verify:
        print("Key installed but verification failed — check server sshd / permissions.", file=sys.stderr)
        return 1
    print(f"OK — key auth verified ({verify[1]})")
    verify[0].close()
    print()
    print("Add to your .env (recommended):")
    print(f"  DEPLOY_KEY_PATH={key_path}")
    print()
    print("Deploy without password:")
    print("  python scripts/deploy.py mn2_staking --upload-only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
