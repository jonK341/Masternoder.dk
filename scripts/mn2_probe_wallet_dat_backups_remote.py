#!/usr/bin/env python3
"""
Probe wallet.dat backups on the server by briefly swapping into the live ops datadir.

Requires a short masternoder2d stop/start. Restores the live wallet.dat after each probe.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

WEB = "/var/www/html"
OPS_DD = f"{WEB}/config"
CLI = "/opt/masternoder2d/masternoder2-cli"


def sh(ssh, cmd: str, timeout: int = 600) -> str:
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    return (out + ("\n[stderr] " + err if err.strip() else "")).strip()


def build_remote(*, max_probes: int, min_bytes: int) -> str:
    return f"""
set -e
OPS_DD="{OPS_DD}"
CLI="{CLI}"
LIVE="$OPS_DD/wallet.dat"
SAFETY="$OPS_DD/wallet.dat.pre-probe-$(date +%Y%m%d%H%M%S)"
MAX={int(max_probes)}
MIN_BYTES={int(min_bytes)}

find_wallets() {{
  find /var/www/html/config /var/www/html/config/backups /root/.masternoder2 /root -maxdepth 2 -name 'wallet.dat*' -type f 2>/dev/null \\
    | while read -r f; do
        sz=$(stat -c%s "$f" 2>/dev/null || echo 0)
        if [ "$sz" -ge "$MIN_BYTES" ]; then
          echo "$sz $f"
        fi
      done | sort -rn | head -n "$MAX"
}}

probe_file() {{
  local src="$1"
  local sz="$2"
  cp -a "$LIVE" "$SAFETY"
  cp -a "$src" "$LIVE"
  systemctl start masternoder2d 2>/dev/null || true
  sleep 8
  local bal utxos txc
  bal=$($CLI -datadir="$OPS_DD" getbalance 2>&1 || echo "ERR")
  txc=$($CLI -datadir="$OPS_DD" getwalletinfo 2>&1 | head -c 400 || true)
  utxos=$($CLI -datadir="$OPS_DD" listunspent 0 9999999 2>&1 | head -c 2000 || true)
  systemctl stop masternoder2d 2>/dev/null || true
  sleep 2
  cp -a "$SAFETY" "$LIVE"
  python3 - <<PY
import json
print(json.dumps({{
  "source": {json.dumps("$src")},
  "bytes": int({json.dumps("$sz")}),
  "getbalance": {json.dumps("$bal")},
  "walletinfo_snip": {json.dumps("$txc")},
  "listunspent_snip": {json.dumps("$utxos")},
}}))
PY
}}

systemctl stop masternoder2d 2>/dev/null || true
sleep 2
results=[]
while read -r sz fp; do
  [ -z "$fp" ] && continue
  echo "PROBING $fp" >&2
  results+=("$(probe_file "$fp" "$sz")")
done < <(find_wallets)
systemctl start masternoder2d 2>/dev/null || true
sleep 5
live_bal=$($CLI -datadir="$OPS_DD" getbalance 2>&1 || echo "ERR")
python3 - <<'PY'
import json, os
results = []
PY
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-probes", type=int, default=3, help="Largest N wallet files to probe")
    parser.add_argument("--min-bytes", type=int, default=5_000_000, help="Min wallet.dat size to probe")
    parser.add_argument("--dry-run", action="store_true", help="Only list wallet files, no daemon stop")
    args = parser.parse_args()

    ssh, _, _ = connect_deploy_ssh(require_deploy_pass())
    try:
        if args.dry_run:
            cmd = (
                f"find /var/www/html/config /var/www/html/config/backups /root -name 'wallet.dat*' -type f 2>/dev/null "
                f"| xargs stat -c '%s %n' 2>/dev/null | sort -rn | head -{args.max_probes + 5}"
            )
            print(sh(ssh, cmd))
            return 0

        remote = f"""
set +e
OPS_DD="{OPS_DD}"
CLI="{CLI}"
LIVE="$OPS_DD/wallet.dat"
SAFETY="$OPS_DD/wallet.dat.pre-probe-$(date +%Y%m%d%H%M%S)"
cp -a "$LIVE" "$SAFETY"
systemctl stop masternoder2d
sleep 3
python3 <<'PY'
import glob, json, os, subprocess, time
CLI="{CLI}"
OPS="{OPS_DD}"
patterns=[
    "/var/www/html/config/wallet.dat",
    "/var/www/html/config/backups/wallet.dat.*",
    "/root/wallet.dat.bak.*",
    "/root/.masternoder2/wallet.dat",
]
seen=set()
files=[]
for pat in patterns:
    for fp in glob.glob(pat):
        if fp in seen: continue
        seen.add(fp)
        try: sz=os.path.getsize(fp)
        except OSError: continue
        if sz < {args.min_bytes} and fp != "/var/www/html/config/wallet.dat": continue
        files.append((sz, fp))
files.sort(reverse=True)
files=files[:{args.max_probes}]
print(json.dumps([{{"bytes":s,"path":p}} for s,p in files]))
PY
"""
        listed = sh(ssh, remote, timeout=120)
        start = listed.find("[")
        file_list = json.loads(listed[start:]) if start >= 0 else []

        results = []
        for item in file_list:
            probe_sh = f"""
set -e
OPS_DD="{OPS_DD}"
CLI="{CLI}"
LIVE="$OPS_DD/wallet.dat"
RESTORE="{WEB}/config/wallet.dat.restored-$(date +%s)"
cp -a "$LIVE" "$RESTORE"
cp -a "{item['path']}" "$LIVE"
systemctl start masternoder2d
sleep 10
BAL=$($CLI -datadir="$OPS_DD" getbalance 2>&1)
INFO=$($CLI -datadir="$OPS_DD" getwalletinfo 2>&1)
UTXOS=$($CLI -datadir="$OPS_DD" listunspent 0 9999999 2>&1)
COUNT=$(echo "$UTXOS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null || echo 0)
systemctl stop masternoder2d
sleep 3
cp -a "$RESTORE" "$LIVE"
systemctl start masternoder2d
sleep 6
python3 -c "import json; print(json.dumps({{'path':{json.dumps(item['path'])},'bytes':{item['bytes']},'getbalance':BAL,'utxo_count':int(COUNT or 0),'walletinfo':INFO[:800],'listunspent_head':UTXOS[:2500]}}))"
"""
            out = sh(ssh, probe_sh, timeout=300)
            jstart = out.rfind("{")
            if jstart >= 0:
                results.append(json.loads(out[jstart:]))

        live = sh(ssh, f"{CLI} -datadir={OPS_DD} getbalance && systemctl is-active masternoder2d", timeout=30)
        report = {"probed": results, "live_after_restore": live}
        print(json.dumps(report, indent=2))
        return 0
    finally:
        ssh.close()


if __name__ == "__main__":
    raise SystemExit(main())
