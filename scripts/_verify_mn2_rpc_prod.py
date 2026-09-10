#!/usr/bin/env python3
"""Follow-up verification of MN2 RPC auth on production."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
echo "=== FULL HEALTH (local uwsgi) ==="
curl -sS -m 60 'http://127.0.0.1:5000/api/mn2/masternode/health' | python3 -m json.tool 2>/dev/null | head -80

echo
echo "=== PROBE SUMMARY ==="
curl -sS -m 60 'http://127.0.0.1:5000/api/mn2/masternode/health' | python3 <<'PY'
import json, sys
d = json.load(sys.stdin)
p = d.get("probe") or {}
print("service_status:", d.get("status"))
print("probe_status:", p.get("status"))
print("rpc:", p.get("rpc"))
print("collateral_outputs_available:", p.get("collateral_outputs_available"))
print("network:", p.get("network"))
err = p.get("error") or d.get("error")
print("error:", (err or "none")[:200])
PY

echo
echo "=== SYSTEM HEALTH mn2_rpc ==="
curl -sS -m 20 'http://127.0.0.1:5000/api/health/system' | python3 <<'PY'
import json, sys
c = json.load(sys.stdin).get("components", {}).get("mn2_rpc", {})
print(json.dumps(c, indent=2))
PY

echo
echo "=== PUBLIC via nginx ==="
curl -sS -m 60 'https://masternoder.dk/api/mn2/masternode/health' | python3 <<'PY'
import json, sys
d = json.load(sys.stdin)
p = d.get("probe") or {}
print("status:", d.get("status"))
print("collateral_outputs_available:", p.get("collateral_outputs_available"))
print("rpc_error:", (p.get("error") or d.get("error") or "none")[:200])
PY

echo
echo "=== AUTH STRING CHECK (masked) ==="
mask() { v="$1"; [ -z "$v" ] && echo empty && return; echo "${v:0:4}…${v: -4}"; }
CU=$(grep '^rpcuser=' /var/www/html/config/masternoder2.conf | cut -d= -f2- | tr -d '\r')
CP=$(grep '^rpcpassword=' /var/www/html/config/masternoder2.conf | cut -d= -f2- | tr -d '\r')
EU=$(grep '^MN2_RPC_USER=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
EP=$(grep '^MN2_RPC_PASSWORD=' /var/www/html/.env | cut -d= -f2- | tr -d '\r"')
echo "conf_user=$(mask "$CU") env_user=$(mask "$EU") user_match=$([ "$CU" = "$EU" ] && echo yes || echo NO)"
echo "conf_pass=$(mask "$CP") env_pass=$(mask "$EP") pass_match=$([ "$CP" = "$EP" ] && echo yes || echo NO)"

echo
echo "=== MASTERNODE SERVICE (wallet RPC) ==="
curl -sS -m 45 'http://127.0.0.1:5000/api/mn2/masternode/service?fresh=1' > /tmp/mn2_svc.json
python3 <<'PY'
import json
with open("/tmp/mn2_svc.json") as f:
    d = json.load(f)
print("success:", d.get("success"))
print("collateral_outputs_available:", d.get("collateral_outputs_available"))
net = d.get("network") or {}
print("network.enabled:", net.get("enabled"))
print("network.rpc_error:", (net.get("rpc_error") or "none")[:200])
print("error:", (d.get("error") or "none")[:200])
PY

echo
echo "=== COLLATERAL OUTPUTS ==="
curl -sS -m 30 'http://127.0.0.1:5000/api/mn2/masternode/collateral-outputs' | python3 -c "import sys,json; d=json.load(sys.stdin); print('success',d.get('success'),'count',d.get('count'),'error',str(d.get('error') or 'none')[:120])"
ENDSCRIPT"""


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, stderr = ssh.exec_command(REMOTE, timeout=120)
    out = (stdout.read() or b"").decode("utf-8", errors="replace")
    err = (stderr.read() or b"").decode("utf-8", errors="replace")
    ssh.close()
    sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))
    if err.strip():
        print("\nSTDERR:", err[:500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
