#!/usr/bin/env python3
"""Brief exchange capital + agent status (prod via SSH, secrets masked)."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from deploy_ssh_env import connect_deploy_ssh, require_deploy_pass

REMOTE = "/var/www/html"

REMOTE_PY = r"""
cd /var/www/html && .venv/bin/python - <<'PY'
import json
import os
os.environ.setdefault('DAEMON_QUIET','1')
os.environ.setdefault('LITE_APP','1')
from scripts.daemon_env import load_dotenv
load_dotenv()
from backend.services import exchange_venue_api_service as vapi
from backend.services import crypto_exchange_service as ex
from backend.services.exchange_arbitrage_service import live_enabled
from backend.services.exchange_binance_withdraw_service import (
    binance_withdraw_live_enabled,
    binance_withdraw_live_gate_reason,
)
from backend.services.exchange_live_execution_service import venue_live_ready
from backend.services.crypto_exchange_agent_service import list_agents
from backend.services.exchange_stable_markets_service import paper_mode_enabled
from backend.services.exchange_sales_pool_service import sales_pool_user_id

# Include Flexible Earn (LD*) — omitting them falsely looks like capital vanished.
bals = vapi.parse_spot_balances('binance', dry_run=False, force_refresh=True)
spot = {}
earn = {}
usd_total = 0.0
earn_usd = 0.0
for k, v in (bals or {}).items():
    if not v or float(v) <= 0:
        continue
    is_earn = str(k).startswith('LD') and len(str(k)) > 2
    base = str(k)[2:] if is_earn else str(k)
    px = float(ex._price_usd(base) or ex._price_usd(k) or (1.0 if base in ('USDC', 'USDT') else 0))
    if base == 'EUR':
        px = 1.08
    if base == 'DKK':
        px = 0.15
    if base == 'ETHW':
        px = float(ex._price_usd('ETH') or 0) * 0.01
    u = float(v) * px
    row = {'free': float(v), 'usd': round(u, 4), 'px': px}
    if is_earn:
        earn[k] = row
        earn_usd += u
    else:
        spot[k] = row
    usd_total += u

agents = list_agents()
recent = []
for a in agents.get('agents') or []:
    last = ((a.get('state') or {}).get('last_action') or {})
    recent.append({
        'id': a.get('id'),
        'ok': last.get('success'),
        'mode': last.get('mode'),
        'side': last.get('side'),
        'sym': last.get('symbol'),
        'usd': last.get('notional_usd'),
        'err': last.get('error'),
        'wallet_usd': round(float((a.get('wallet') or {}).get('total_usd') or 0), 2),
    })

pool = ex.get_wallet(sales_pool_user_id())
passets = {k: float(v) for k, v in (pool.get('assets') or {}).items() if float(v or 0) > 1e-8}
# Only show stables that matter for venue backing
pool_stables = {k: passets[k] for k in ('USDC', 'USDT') if k in passets}

out = {
    'gates': {
        'arb_live': live_enabled(),
        'withdraw_live': binance_withdraw_live_enabled(),
        'withdraw_reason': binance_withdraw_live_gate_reason() or 'ok',
        'binance_ready': venue_live_ready('binance'),
        'paper_mode': paper_mode_enabled(),
        'agents_venue_live': agents.get('venue_live'),
        'agent_trading_enabled': agents.get('enabled'),
    },
    'binance_total_usd': round(usd_total, 2),
    'binance_spot_usd': round(usd_total - earn_usd, 2),
    'binance_earn_usd': round(earn_usd, 2),
    'binance_spot': spot,
    'binance_earn': earn,
    'sales_pool_stables': pool_stables,
    'agents_tick': agents.get('tick_count'),
    'agents_last_tick': agents.get('last_tick'),
    'agents_last_mode': None,
    'agents': recent,
}
# last mode from state file if present
try:
    st = ex._read_json(os.path.join(ex._DATA_DIR, 'agent_state.json'), {})
    out['agents_last_mode'] = st.get('last_mode')
except Exception:
    pass
print(json.dumps(out))
PY
"""


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh(require_deploy_pass())
    print(f"prod ({auth})")
    _, stdout, stderr = ssh.exec_command(REMOTE_PY, timeout=120)
    out = (stdout.read() or b"").decode(errors="replace").strip()
    err = (stderr.read() or b"").decode(errors="replace").strip()
    # Find last JSON object line
    data = None
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                break
            except Exception:
                pass
    if not data:
        print("raw_out_tail:", out[-1500:])
        if err:
            print("err_tail:", err[-500:])
        ssh.close()
        return 1

    g = data["gates"]
    print(
        f"gates: arb={g['arb_live']} wd={g['withdraw_live']} "
        f"binance={g['binance_ready']} paper={g['paper_mode']} "
        f"agents_on={g.get('agent_trading_enabled')} "
        f"agents_venue={g['agents_venue_live']} ({g['withdraw_reason']})"
    )
    print(
        f"binance TOTAL ~${data.get('binance_total_usd', data['binance_spot_usd'])} "
        f"(spot ~${data['binance_spot_usd']} + earn ~${data.get('binance_earn_usd', 0)})"
    )
    print("spot:")
    for k, row in sorted(data["binance_spot"].items(), key=lambda kv: -kv[1]["usd"]):
        print(f"  {k}: {row['free']} (~${row['usd']})")
    if data.get("binance_earn"):
        print("flexible earn (still yours):")
        for k, row in sorted(data["binance_earn"].items(), key=lambda kv: -kv[1]["usd"]):
            if row["usd"] >= 0.05:
                print(f"  {k}: {row['free']} (~${row['usd']})")
    print(f"sales_pool stables: {data['sales_pool_stables']}")
    print(
        f"agents tick={data['agents_tick']} last={data['agents_last_tick']} "
        f"mode={data['agents_last_mode']}"
    )
    for a in data["agents"]:
        status = "ok" if a["ok"] else "fail"
        err = f" err={a['err']}" if a.get("err") else ""
        print(
            f"  {a['id']}: {status} {a.get('mode')} {a.get('side')} {a.get('sym')} "
            f"${a.get('usd')} wallet~${a['wallet_usd']}{err}"
        )
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
