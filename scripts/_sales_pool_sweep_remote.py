"""One-shot remote sales pool sweep on masternoder.dk."""
from __future__ import annotations

import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deploy_ssh_env import connect_deploy_ssh, deploy_host, deploy_user, _load_deploy_env_from_dotenv

REMOTE_PY = r'''
import json
from backend.services.exchange_sales_pool_service import sales_pool_status, run_sales_pool_tick

def slim(st):
    return {
        "pool_assets": st.get("pool_assets"),
        "pool_gaps": st.get("pool_gaps"),
        "last_transfer_at": st.get("last_transfer_at"),
        "transfer_count": st.get("transfer_count"),
    }

def agents(st):
    return [
        {
            "agent_id": a.get("agent_id"),
            "assets": a.get("assets"),
            "transferable": a.get("transferable"),
        }
        for a in (st.get("source_agents") or [])
    ]

before = sales_pool_status()
tick = run_sales_pool_tick(force=True)
after = sales_pool_status()
transfers = [
    {"symbol": t.get("symbol"), "amount": t.get("amount"), "from_agent": t.get("agent_id")}
    for t in (tick.get("transfers") or [])
    if t.get("success")
]
failed = [t for t in (tick.get("transfers") or []) if not t.get("success")]
bp = before.get("pool_assets") or {}
ap = after.get("pool_assets") or {}
syms = sorted(set(bp) | set(ap) | set(before.get("pool_gaps") or {}) | set(after.get("pool_gaps") or {}))
delta = {}
for s in syms:
    b = float(bp.get(s) or 0)
    a = float(ap.get(s) or 0)
    if abs(a - b) > 1e-15:
        delta[s] = {"before": b, "after": a, "delta": round(a - b, 12)}
print(json.dumps({
    "host": "masternoder.dk",
    "before": {"pool": slim(before), "agents": agents(before)},
    "tick": {k: v for k, v in tick.items() if k != "status"},
    "after": {"pool": slim(after), "agents": agents(after)},
    "transfers": transfers,
    "errors": failed,
    "comparison": {
        "pool_delta": delta,
        "gaps_before": before.get("pool_gaps"),
        "gaps_after": after.get("pool_gaps"),
    },
}, indent=2))
'''

WEB = "/var/www/html"


def main() -> int:
    _load_deploy_env_from_dotenv()
    pw = (os.environ.get("DEPLOY_PASS") or "").strip()
    if not pw:
        print("ERROR: DEPLOY_PASS not set", file=sys.stderr)
        return 2
    b64 = base64.b64encode(REMOTE_PY.encode()).decode()
    cmd = f"cd {WEB} && PYTHONPATH={WEB} python3 -c 'import base64; exec(base64.b64decode(\"{b64}\").decode())'"
    ssh, auth, _ = connect_deploy_ssh(pw)
    print(f"Connected to {deploy_user()}@{deploy_host()} via {auth}", file=sys.stderr)
    _, stdout, stderr = ssh.exec_command(cmd, timeout=120)
    out = stdout.read().decode(errors="replace")
    err = stderr.read().decode(errors="replace")
    print(out)
    if err.strip():
        print("[stderr]", err, file=sys.stderr)
    ssh.close()
    return 0 if out.strip().startswith("{") else 1


if __name__ == "__main__":
    raise SystemExit(main())
