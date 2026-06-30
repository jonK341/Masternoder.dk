#!/usr/bin/env python3
"""Ensure sporkkey is set in masternoder2.conf (local file or remote server via --apply)."""
from __future__ import annotations

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DEFAULT_CONF = os.path.join(ROOT, "config", "masternoder2.conf")
REMOTE_CONF = "/var/www/html/config/masternoder2.conf"


def patch_conf(path: str, sporkkey: str) -> None:
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    with open(path, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    kept = [ln for ln in lines if not re.match(r"^sporkkey=", ln.strip())]
    kept.append(f"sporkkey={sporkkey}")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(kept).rstrip() + "\n")


def apply_remote(sporkkey: str, *, restart: bool) -> int:
    import paramiko

    from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user

    host = deploy_host()
    user = deploy_user()
    print(f"[sporkkey] patching {REMOTE_CONF} on {user}@{host}")

    ssh = connect_deploy_ssh()[0]
    try:
        cmd = f"""set -euo pipefail
DCONF="{REMOTE_CONF}"
SPORKKEY='{sporkkey.replace("'", "'\"'\"'")}'
ts="$(date -u +%Y%m%dT%H%M%SZ)"
cp -a "$DCONF" "${{DCONF}}.bak-${{ts}}"
python3 - "$DCONF" "$SPORKKEY" <<'PY'
import re, sys
path, key = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()
kept = [ln for ln in lines if not re.match(r"^sporkkey=", ln.strip())]
kept.append(f"sporkkey={{key}}")
with open(path, "w", encoding="utf-8") as f:
    f.write("\\n".join(kept).rstrip() + "\\n")
print(f"patched {{path}}")
PY
chown root:www-data "$DCONF" 2>/dev/null || true
chmod 640 "$DCONF" 2>/dev/null || true
grep '^sporkkey=' "$DCONF" | sed 's/=.*/=<set>/'
"""
        if restart:
            cmd += """
systemctl restart masternoder2d
sleep 3
/opt/masternoder2d/masternoder2-cli -datadir=/var/www/html/config getblockcount 2>/dev/null || echo "(rpc not ready yet)"
"""
        _, stdout, stderr = ssh.exec_command(cmd, timeout=120)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        if out.strip():
            print(out.rstrip())
        if err.strip():
            print(err.rstrip(), file=sys.stderr)
        code = stdout.channel.recv_exit_status()
        if code != 0:
            print(f"[sporkkey] remote command failed (exit {code})", file=sys.stderr)
            return code
        print("[sporkkey] OK — sporkkey set on server" + (" and daemon restarted" if restart else ""))
        return 0
    finally:
        ssh.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Set sporkkey in masternoder2.conf")
    parser.add_argument(
        "sporkkey",
        nargs="?",
        default=(os.environ.get("MN2_SPORKKEY") or "").strip(),
        help="Spork private key (or set MN2_SPORKKEY env)",
    )
    parser.add_argument("--conf", default=DEFAULT_CONF, help="Local conf path")
    parser.add_argument("--apply", action="store_true", help="Patch production server via SSH")
    parser.add_argument("--no-restart", action="store_true", help="With --apply, skip masternoder2d restart")
    args = parser.parse_args()

    if not args.sporkkey:
        print("Provide sporkkey argument or MN2_SPORKKEY env", file=sys.stderr)
        return 1

    if args.apply:
        return apply_remote(args.sporkkey, restart=not args.no_restart)

    if not os.path.isfile(args.conf):
        print(f"Local conf missing: {args.conf}", file=sys.stderr)
        return 1
    patch_conf(args.conf, args.sporkkey)
    print(f"[sporkkey] patched {args.conf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
