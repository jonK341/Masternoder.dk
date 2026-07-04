#!/usr/bin/env python3
"""Ensure MN2_SPORK_OVERRIDE_JSON is in server .env for exchange live gate."""
from __future__ import annotations

import argparse
import sys

ROOT = __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

ENV = "/var/www/html/.env"
DEFAULT_JSON = '{"SPORK_112_EXCHANGE_LIVE_TRADING":1703122560}'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default=DEFAULT_JSON)
    args = parser.parse_args()

    from deploy_ssh_env import connect_deploy_ssh

    key = "MN2_SPORK_OVERRIDE_JSON"
    val = args.json.replace("'", "'\"'\"'")
    remote = """set -e
ENV="/var/www/html/.env"
KEY="MN2_SPORK_OVERRIDE_JSON"
VAL='""" + val + """'
ts="$(date -u +%Y%m%dT%H%M%SZ)"
cp -a "$ENV" "${ENV}.bak-${ts}"
python3 - "$ENV" "$KEY" "$VAL" <<'PY'
import sys
path, key, val = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path, encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()
out, found = [], False
for line in lines:
    if line.startswith(key + "="):
        out.append(key + "=" + val)
        found = True
    else:
        out.append(line)
if not found:
    out.insert(0, key + "=" + val)
with open(path, "w", encoding="utf-8") as f:
    f.write("\\n".join(out).rstrip() + "\\n")
print("set", key, "in", path)
PY
grep '^MN2_SPORK_OVERRIDE_JSON=' "$ENV"
echo
echo "Removing invalid MN2_RPC_* lines from masternoder2.conf if present..."
python3 - /var/www/html/config/masternoder2.conf <<'PY'
import re, sys
path = sys.argv[1]
with open(path, encoding="utf-8", errors="replace") as f:
    lines = f.read().splitlines()
bad = re.compile(r"^MN2_")
kept = [ln for ln in lines if not bad.match(ln.strip())]
seen = set()
dedup = []
for ln in kept:
    m = re.match(r"^(server|rpcuser|rpcpassword|rpcport|rpcbind|rpcallowip)=", ln.strip())
    if m:
        k = m.group(1)
        if k in seen:
            continue
        seen.add(k)
    dedup.append(ln)
if dedup != lines:
    with open(path, "w", encoding="utf-8") as f:
        f.write("\\n".join(dedup).rstrip() + "\\n")
    print("cleaned", path)
else:
    print("no cleanup needed for", path)
PY
grep -E '^(server|rpcuser|rpcpassword|sporkkey)=' /var/www/html/config/masternoder2.conf | sed 's/rpcpassword=.*/rpcpassword=<set>/; s/sporkkey=.*/sporkkey=<set>/'
"""
    ssh = connect_deploy_ssh()[0]
    try:
        _, stdout, stderr = ssh.exec_command(remote, timeout=120)
        print(stdout.read().decode("utf-8", errors="replace").rstrip())
        err = stderr.read().decode("utf-8", errors="replace").strip()
        if err:
            print(err, file=sys.stderr)
        return stdout.channel.recv_exit_status()
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
